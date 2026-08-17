# Lecture Study Assistant

Upload a lecture recording (MP3 / WAV / MP4) and get:
- A transcript (via local speech-to-text — no cloud API, no per-minute cost)
- A bullet-point summary
- An auto-generated practice quiz (fill-in-the-blank + short-answer)

Everything is saved per-user in a local SQLite database so students can log
back in and study anytime.

## 1. Install system dependency: ffmpeg

Audio/video decoding needs ffmpeg on your PATH.

- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: download from https://ffmpeg.org/download.html and add it to PATH

## 2. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The first time you run a transcription, `faster-whisper` will download its
model (~150MB for the "base" model) — that step needs internet access once.
After that it runs fully offline.

## 3. Run the app

```bash
streamlit run app.py
```

This opens the app in your browser (usually http://localhost:8501).

## How it works

| Step | File | What it does |
|---|---|---|
| Upload & UI | `app.py` | Streamlit UI: login, upload zone, two dashboard tabs |
| Auth | `auth.py` | Signup/login, bcrypt-hashed passwords |
| Storage | `database.py` | SQLite: users, lectures, quizzes |
| Audio → text | `transcription.py` | Converts upload to 16kHz mono wav (pydub), transcribes with faster-whisper |
| Text → bullets | `summarizer.py` | TextRank extractive summarization (sumy) + keyword extraction |
| Bullets → quiz | `quiz_generator.py` | Builds fill-in-the-blank (from key terms) and short-answer (from bullets) questions |

## Notes / things you may want to tweak

- **Transcription speed vs. accuracy**: `transcription.py` uses the `"base"`
  Whisper model on CPU. For longer/harder lectures, try `"small"` or
  `"medium"` in `MODEL_SIZE` — slower but more accurate. If you have a GPU,
  change `device="cpu"` to `device="cuda"`.
- **Summary length**: `summarizer.summarize_to_bullets(transcript, num_bullets=8)`
  — tune the default in `app.py`'s call if you want longer/shorter summaries.
- **Quiz size/mix**: `quiz_generator.generate_quiz(..., num_questions=10)`
  controls total question count; the mix of fill-in-blank vs short-answer
  questions comes naturally from how many key terms vs. summary bullets exist.
- **Multi-user**: accounts are fully separate — each user only sees their
  own lectures and quizzes.
