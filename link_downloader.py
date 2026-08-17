"""
link_downloader.py
Downloads the audio track from a YouTube or Instagram link so it can be
fed into the same transcription pipeline used for uploaded files. Uses
yt-dlp under the hood (supports YouTube, Instagram Reels/posts with audio,
and most other common video sites too).

YouTube regularly changes how it throttles/blocks non-browser clients, so
instead of relying on one fixed configuration, this tries a short list of
known-good client strategies in order and uses whichever one actually
produces a non-empty audio file.
"""

import os
import shutil
import tempfile

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


SUPPORTED_DOMAINS_HINT = "youtube.com, youtu.be, instagram.com"

# Each dict is merged into the base yt-dlp options and tried in order.
# "tv" and "ios" clients frequently sidestep the throttling/PO-token
# issues that hit the default "web" client.
_CLIENT_STRATEGIES = [
    {"player_client": ["android"]},
    {"player_client": ["web", "web_safari"]},
    {"player_client": ["tv"]},
    {"player_client": ["ios"]},
]

def is_probably_video_link(text: str) -> bool:
    """Quick check so the UI can validate before attempting a download."""
    text = text.strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def _build_opts(tmp_dir: str, out_template: str, notify, extractor_args: dict,
                 use_cookies: bool) -> dict:
    def _hook(d):
        if d.get("status") == "downloading":
            pct = d.get("_percent_str", "").strip()
            notify(f"Downloading audio... {pct}")
        elif d.get("status") == "finished":
            notify("Download complete, converting audio...")

    opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192",
        }],
        "progress_hooks": [_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_args": {"youtube": extractor_args},
    }
    if use_cookies:
        # Borrow cookies from a locally logged-in Chrome session. Change
        # "chrome" to "safari" / "firefox" / "edge" if that's where you're
        # logged into YouTube.
        opts["cookiesfrombrowser"] = ("chrome",)
    return opts


def download_audio_from_link(url: str, progress_callback=None) -> tuple[str, str]:
    """
    Downloads the best-available audio track for the given URL into a temp
    file. Returns (audio_path, title). Raises on failure (bad link, private
    video, no internet, etc.) — callers should catch and show a friendly
    error.
    """
    def notify(msg):
        if progress_callback:
            progress_callback(msg)

    last_error = None

    for i, strategy in enumerate(_CLIENT_STRATEGIES, start=1):
        tmp_dir = tempfile.mkdtemp(prefix="lecture_link_")
        out_template = os.path.join(tmp_dir, "%(id)s.%(ext)s")

        # Try each client both with and without cookies — some clients
        # (tv, ios) work best WITHOUT cookies attached.
        for use_cookies in (False, True):
            notify(f"Fetching link info (attempt {i}/{len(_CLIENT_STRATEGIES)})...")
            opts = _build_opts(tmp_dir, out_template, notify, strategy, use_cookies)
            try:
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Untitled lecture")
                    base_id = info.get("id")

                wav_path = os.path.join(tmp_dir, f"{base_id}.wav")
                if not os.path.exists(wav_path):
                    candidates = [f for f in os.listdir(tmp_dir) if f.endswith(".wav")]
                    wav_path = os.path.join(tmp_dir, candidates[0]) if candidates else None

                if wav_path and os.path.exists(wav_path) and os.path.getsize(wav_path) > 1024:
                    return wav_path, title

                last_error = RuntimeError("Downloaded file was empty or too small.")
            except DownloadError as e:
                last_error = e
            except Exception as e:
                last_error = e

            shutil.rmtree(tmp_dir, ignore_errors=True)
            os.makedirs(tmp_dir, exist_ok=True)

    raise RuntimeError(
        f"Couldn't download audio after trying multiple methods. Last error: {last_error}"
    )