"""
transcription.py
Normalizes uploaded audio/video into a clean wav file, then transcribes it
with faster-whisper (runs locally, no external API calls).
"""

import os
import tempfile
from pydub import AudioSegment
from faster_whisper import WhisperModel

# "small" gives noticeably better accuracy than "base" (fewer misheard
# words/spelling mistakes), at the cost of being slower on CPU. Bump to
# "medium" for even higher accuracy if you have the patience/hardware, or
# drop back to "base" if you need faster turnaround more than accuracy.
MODEL_SIZE = "small"

_model = None


def get_model() -> WhisperModel:
    """Lazy-load the model once per process (it's a few hundred MB)."""
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def normalize_to_wav(input_path: str) -> str:
    """
    Convert any supported upload (mp3, wav, mp4) into a 16kHz mono wav file,
    which is what the transcription model wants. Returns path to a temp wav.
    """
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)

    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio.export(tmp_wav.name, format="wav")
    return tmp_wav.name


def transcribe_file(uploaded_file_path: str, progress_callback=None) -> str:
    """
    Full pipeline: normalize -> transcribe -> return plain text transcript.
    progress_callback(str) is called with status updates if provided.
    """
    def notify(msg):
        if progress_callback:
            progress_callback(msg)

    notify("Converting audio to a standard format...")
    wav_path = normalize_to_wav(uploaded_file_path)

    try:
        notify("Loading transcription model...")
        model = get_model()

        notify("Transcribing (this can take a while for long lectures)...")
        segments, _info = model.transcribe(
            wav_path,
            beam_size=5,
            language="en",       # skip auto-detection; set to None if your
                                  # lectures aren't always in English
            vad_filter=True,     # skip silence/noise, reduces garbage output
        )

        full_text = " ".join(segment.text.strip() for segment in segments)
        return full_text.strip()
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)