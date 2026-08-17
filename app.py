"""
app.py
Flask entry point for the Lecture Summarizer & Quiz Generator.

Run with:  python app.py
Then open: http://localhost:5000
"""

import os
import secrets
import tempfile
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)

import database as db
import auth
import transcription
import summarizer
import quiz_generator
import link_downloader

app = Flask(__name__)
# Set a fixed SECRET_KEY env var in production so sessions survive restarts.
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))

db.init_db()

SUPPORTED_TYPES = {"mp3", "wav", "mp4"}


def current_user():
    return session.get("user")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/")
def login_page():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    success, message = auth.signup(username, password)
    flash(message, "success" if success else "error")
    return redirect(url_for("login_page"))


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    user, message = auth.login(username, password)
    if user:
        session["user"] = {"id": user["id"], "username": user["username"]}
        return redirect(url_for("dashboard"))
    flash(message, "error")
    return redirect(url_for("login_page"))


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = current_user()["id"]
    tab = request.args.get("tab", "summaries")
    lectures = db.get_lectures_for_user(user_id)
    quizzes = db.get_quizzes_for_user(user_id)

    selected_quiz = request.args.get("quiz", "0")
    try:
        selected_quiz = int(selected_quiz)
    except ValueError:
        selected_quiz = 0
    if quizzes:
        selected_quiz = max(0, min(selected_quiz, len(quizzes) - 1))

    return render_template(
        "dashboard.html",
        user=current_user(),
        lectures=lectures,
        quizzes=quizzes,
        tab=tab,
        selected_quiz=selected_quiz,
        supported_types=sorted(SUPPORTED_TYPES),
        supported_link_hint=link_downloader.SUPPORTED_DOMAINS_HINT,
    )


def _run_pipeline(user_id: int, title: str, audio_path: str, log: list) -> bool:
    """Runs transcribe -> summarize -> quiz -> save. Returns True on success."""
    try:
        def progress(msg):
            log.append(msg)

        transcript = transcription.transcribe_file(audio_path, progress_callback=progress)
        if not transcript:
            log.append("Couldn't extract any speech from this.")
            return False

        log.append("Generating summary...")
        bullets = summarizer.summarize_to_bullets(transcript)
        key_terms = summarizer.extract_key_terms(transcript)

        log.append("Building practice quiz...")
        questions = quiz_generator.generate_quiz(transcript, bullets, key_terms)

        db_lecture_id = db.save_lecture(user_id, title, transcript, bullets, key_terms)
        db.save_quiz(db_lecture_id, questions)

        log.append("Done!")
        return True
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    user_id = current_user()["id"]
    uploaded = request.files.get("file")

    if not uploaded or uploaded.filename == "":
        flash("Please choose a file first.", "error")
        return redirect(url_for("dashboard"))

    ext = os.path.splitext(uploaded.filename)[1].lower().lstrip(".")
    if ext not in SUPPORTED_TYPES:
        flash(f"Unsupported file type: .{ext}", "error")
        return redirect(url_for("dashboard"))

    title = request.form.get("title", "").strip() or os.path.splitext(uploaded.filename)[0]

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        uploaded.save(tmp.name)
        tmp_path = tmp.name

    log = []
    ok = _run_pipeline(user_id, title, tmp_path, log)
    flash(" \u2192 ".join(log) if log else "Something went wrong.", "success" if ok else "error")
    return redirect(url_for("dashboard"))


@app.route("/link", methods=["POST"])
@login_required
def process_link():
    user_id = current_user()["id"]
    url = request.form.get("url", "").strip()
    title_override = request.form.get("title", "").strip()

    if not link_downloader.is_probably_video_link(url):
        flash("That doesn't look like a valid link.", "error")
        return redirect(url_for("dashboard"))

    log = []
    try:
        def progress(msg):
            log.append(msg)
        audio_path, fetched_title = link_downloader.download_audio_from_link(
            url, progress_callback=progress
        )
    except Exception as e:
        flash(f"Couldn't process that link: {e}", "error")
        return redirect(url_for("dashboard"))

    title = title_override or fetched_title
    ok = _run_pipeline(user_id, title, audio_path, log)
    flash(" \u2192 ".join(log) if log else "Something went wrong.", "success" if ok else "error")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", debug=debug_mode, port=port)