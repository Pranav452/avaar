"""FFmpeg utilities for audio extraction and video info."""

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """
    Extract audio track from video as 22050 Hz mono WAV.
    XTTS-v2 uses 22050 Hz for its speaker reference; providing it directly
    avoids an extra librosa resample step.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                   # no video stream
        "-acodec", "pcm_s16le", # uncompressed PCM
        "-ar", "22050",
        "-ac", "1",              # mono
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed:\n{result.stderr}")
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"ffprobe failed on {audio_path}: {result.stderr}")
    return float(result.stdout.strip())


def check_min_audio_duration(audio_path: Path, min_seconds: float = 3.0) -> None:
    """Raise ValueError if reference audio is too short for XTTS-v2 voice cloning."""
    duration = get_audio_duration(audio_path)
    if duration < min_seconds:
        raise ValueError(
            f"Reference audio is only {duration:.1f}s — XTTS-v2 needs at least "
            f"{min_seconds}s of clear speech for voice cloning. "
            "Please upload a longer video."
        )
