"""
quiz_generator.py
Builds a practice quiz (fill-in-the-blank + short-answer questions) from
the transcript, its summary bullets, and extracted key terms. Pure
rule-based logic — no external API calls.
"""

import re
import random


def _find_sentence_for_term(term: str, sentences: list) -> str:
    """Return the first sentence that contains the given term, if any."""
    for s in sentences:
        if re.search(rf"\b{re.escape(term)}\b", s, flags=re.IGNORECASE):
            return s
    return None


def generate_quiz(transcript: str, summary_bullets: list, key_terms: list,
                   num_questions: int = 10) -> list:
    """
    Returns a list of dicts: {"type": ..., "question": ..., "answer": ...}
    Mixes fill-in-the-blank questions (built from key terms + the sentence
    they appear in) with short-answer questions (built from summary bullets).
    """
    sentences = re.split(r"(?<=[.!?])\s+", transcript.strip())
    questions = []

    # --- Fill-in-the-blank questions from key terms ---
    for term in key_terms:
        sentence = _find_sentence_for_term(term, sentences)
        if not sentence:
            continue
        blanked = re.sub(
            rf"\b{re.escape(term)}\b", "_____", sentence, count=1, flags=re.IGNORECASE
        )
        if blanked == sentence:
            continue
        questions.append({
            "type": "fill_in_blank",
            "question": blanked,
            "answer": term,
        })

    # --- Short-answer questions from summary bullets ---
    for bullet in summary_bullets:
        questions.append({
            "type": "short_answer",
            "question": f"Explain the following point from the lecture: \"{bullet}\"",
            "answer": bullet,
        })

    random.shuffle(questions)
    return questions[:num_questions]
