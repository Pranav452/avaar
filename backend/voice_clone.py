"""XTTS-v2 voice cloning wrapper.

Pinned stack: TTS==0.22.0 + transformers==4.46.3 + torch==2.6.0
This combination is confirmed working by multiple open-source dubbing repos
(ViDubb, etc). Do not upgrade transformers past 4.46.x without retesting XTTS.

The TTS model is loaded once as a module-level singleton so subsequent jobs
within the same server process reuse the loaded weights.

First run: XTTS-v2 (~1.8 GB) is downloaded to
  ~/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2/
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import torch

# torch 2.6 changed torch.load default to weights_only=True.
# Coqui XTTS checkpoints use pickle with custom TTS classes — they need weights_only=False.
_real_torch_load = torch.load


def _torch_load_compat(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _real_torch_load(*args, **kwargs)


torch.load = _torch_load_compat  # type: ignore[assignment]

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
        from TTS.api import TTS

        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
            device = "mps"
        else:
            device = "cpu"
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
    """Generate speech that mimics the speaker in reference_audio.

    Args:
        reference_audio: WAV file extracted from the original video (>=3 s).
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
