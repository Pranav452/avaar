"""XTTS-v2 voice cloning wrapper.

The TTS model is loaded once as a module-level singleton so that subsequent
jobs within the same server process reuse the loaded weights instead of
reloading from disk each time.

First run: XTTS-v2 (~1.8 GB) is automatically downloaded to
  ~/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2/
Subsequent runs use the cached files.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from TTS.api import TTS as TTSType

# Supported XTTS-v2 language codes (matches frontend dropdown)
SUPPORTED_LANGUAGES = {
    "en", "es", "fr", "de", "it", "pt", "pl", "tr",
    "ru", "nl", "cs", "ar", "zh-cn", "hu", "ko", "ja", "hi",
}

_tts_model: TTSType | None = None


def get_tts_model() -> "TTSType":
    """Return the singleton XTTS-v2 model, loading it on first call."""
    global _tts_model
    if _tts_model is None:
        from TTS.api import TTS  # deferred import — slow on first load

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[voice_clone] Loading XTTS-v2 on {device} …")
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print("[voice_clone] XTTS-v2 ready.")
    return _tts_model


def clone_voice(
    reference_audio: Path,
    text: str,
    language: str,
    output_path: Path,
) -> Path:
    """
    Generate speech that mimics the speaker in reference_audio.

    Args:
        reference_audio: WAV file extracted from the original video (≥3 s).
        text:            New script to synthesise.
        language:        ISO 639-1 code — must be in SUPPORTED_LANGUAGES.
        output_path:     Destination WAV file path.

    Returns:
        output_path on success.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Language '{language}' is not supported by XTTS-v2. "
            f"Supported: {sorted(SUPPORTED_LANGUAGES)}"
        )

    model = get_tts_model()
    model.tts_to_file(
        text=text,
        speaker_wav=str(reference_audio),
        language=language,
        file_path=str(output_path),
    )
    return output_path
