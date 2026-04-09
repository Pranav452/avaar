"""Wav2Lip lip-sync wrapper.

Wav2Lip's inference.py is a standalone CLI script (uses argparse, sys.exit,
relative imports, writes temp files relative to its own directory).  Importing
it directly is fragile, so we run it as a subprocess with the venv Python.

cwd is set to the Wav2Lip directory — this is mandatory for its internal
relative imports and temp-file paths to resolve correctly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Absolute paths resolved at import time
BACKEND_DIR = Path(__file__).parent.resolve()
WAV2LIP_DIR = BACKEND_DIR / "Wav2Lip"
CHECKPOINT = WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"
INFERENCE_SCRIPT = WAV2LIP_DIR / "inference.py"


def _check_setup() -> None:
    if not CHECKPOINT.exists():
        raise RuntimeError(
            f"Wav2Lip checkpoint not found at {CHECKPOINT}. "
            "Run backend/setup.sh first."
        )
    if not INFERENCE_SCRIPT.exists():
        raise RuntimeError(
            f"Wav2Lip inference.py not found at {INFERENCE_SCRIPT}. "
            "Run backend/setup.sh first."
        )


def sync_lips(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    resize_factor: int = 1,
) -> Path:
    """
    Run Wav2Lip GAN to sync the speaker's lips in video_path with audio_path.

    Args:
        video_path:     Source video containing the face.
        audio_path:     New synthesised speech WAV.
        output_path:    Destination for the lip-synced MP4.
        resize_factor:  1 = original resolution. Use 2 if face detection fails
                        (reduces resolution, improves detection robustness).

    Returns:
        output_path on success.
    """
    _check_setup()

    cmd = [
        sys.executable,               # venv Python
        str(INFERENCE_SCRIPT),
        "--checkpoint_path", str(CHECKPOINT),
        "--face", str(video_path),
        "--audio", str(audio_path),
        "--outfile", str(output_path),
        "--pads", "0", "10", "0", "0",  # extra bottom padding for chin coverage
        "--resize_factor", str(resize_factor),
        "--nosmooth",                  # skip temporal smoothing for speed
    ]

    result = subprocess.run(
        cmd,
        cwd=str(WAV2LIP_DIR),   # mandatory — Wav2Lip uses relative imports
        capture_output=True,
        text=True,
        timeout=600,            # 10-min hard limit
    )

    if result.returncode != 0:
        # Try fallback with resize_factor=2 if face wasn't detected
        if resize_factor == 1 and "No face detected" in (result.stdout + result.stderr):
            print("[lip_sync] Face not detected at resize_factor=1, retrying with 2…")
            return sync_lips(video_path, audio_path, output_path, resize_factor=2)

        raise RuntimeError(
            f"Wav2Lip failed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout[-2000:]}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )

    return output_path
