"""
summarizer.py
Turns a raw transcript into bullet-point summary sentences and a list of
key terms, using classic extractive summarization (TextRank via sumy) —
no external API calls, works entirely offline once nltk data is present.
"""

import re
from collections import Counter

import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

LANGUAGE = "english"

_STOPWORDS = None


def _ensure_nltk_data():
    """Download the small nltk tokenizer models the first time they're needed."""
    for pkg in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{pkg}")
        except LookupError:
            nltk.download(pkg, quiet=True)


def summarize_to_bullets(transcript: str, num_bullets: int = 8) -> list:
    """
    Returns a list of `num_bullets` sentences that best represent the
    transcript, ranked by TextRank.
    """
    _ensure_nltk_data()

    parser = PlaintextParser.from_string(transcript, Tokenizer(LANGUAGE))
    stemmer = Stemmer(LANGUAGE)
    summarizer = TextRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(LANGUAGE)

    sentence_count = min(num_bullets, max(3, len(parser.document.sentences) // 4))
    sentences = summarizer(parser.document, sentence_count)

    bullets = [str(s).strip() for s in sentences]
    return bullets if bullets else _fallback_first_sentences(transcript, num_bullets)


def _fallback_first_sentences(transcript: str, n: int) -> list:
    """If TextRank produces nothing (e.g. very short transcript), just take
    the first few sentences instead of returning an empty summary."""
    sentences = re.split(r"(?<=[.!?])\s+", transcript.strip())
    return [s for s in sentences[:n] if s]


def extract_key_terms(transcript: str, num_terms: int = 12) -> list:
    """
    Lightweight keyword extraction: picks the most frequent capitalized-or-
    repeated multi-letter words, filtering common stopwords. Good enough to
    drive fill-in-the-blank quiz questions without a heavy NLP model.
    """
    _ensure_nltk_data()
    stop_words = get_stop_words(LANGUAGE)

    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", transcript)
    words_lower = [w.lower() for w in words]

    freq = Counter(w for w in words_lower if w not in stop_words)
    most_common = [word for word, _count in freq.most_common(num_terms)]
    return most_common
