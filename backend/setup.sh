#!/bin/bash
# AI Video Dubbing System - One-time environment setup
#
# Linux (incl. WSL): bash setup.sh
# macOS: same — use Terminal or iTerm, not WSL (WSL is Windows-only).
set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> Setting up backend at $BACKEND_DIR"
cd "$BACKEND_DIR"

download_file() {
    local url="$1"
    local dest="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -q --show-progress --tries=5 --waitretry=10 "$url" -O "$dest"
    elif command -v curl >/dev/null 2>&1; then
        # Retries help large checkpoints on slow or flaky links (HF redirects to CDN).
        curl -fsSL --progress-bar \
            --connect-timeout 60 \
            --retry 5 --retry-delay 5 --retry-all-errors \
            "$url" -o "$dest"
    else
        echo "Install wget or curl to download files." >&2
        exit 1
    fi
}

# ── 1. Create venv (self-contained; no --system-site-packages — works on macOS) ──
if [ ! -d "venv" ]; then
    echo "==> Creating virtualenv..."
    python3 -m venv venv
else
    echo "==> venv already exists, skipping creation"
fi

source venv/bin/activate
pip install --upgrade pip --quiet
echo "==> Python: $(python --version)"

# ── 2. Install pinned stack (learned from working video-dubbing repos) ──
# numpy<2 must come first — sklearn/librosa/pandas break with numpy 2.x.
echo "==> Installing numpy (pinned <2.0)..."
pip install --quiet "numpy<2.0"

# PyTorch 2.6 ships MPS support for macOS Apple Silicon.
echo "==> Installing PyTorch 2.6 + torchaudio + torchcodec..."
pip install --quiet "torch==2.6.0" "torchaudio==2.6.0" "torchcodec==0.2.1"

echo "==> Torch: $(python -c "import torch; mps=torch.backends.mps.is_available() if torch.backends.mps.is_built() else False; print(torch.__version__, '| MPS:', mps)")"

# transformers 4.46.3 is the last version fully compatible with Coqui TTS 0.22.0 XTTS-v2.
# (confirmed by ViDubb and other working open-source dubbing repos)
echo "==> Installing transformers 4.46.3..."
pip install --quiet "transformers==4.46.3"

echo "==> Installing Coqui TTS 0.22.0 + coqpit..."
pip install --quiet "coqpit==0.0.17" "TTS==0.22.0"

echo "==> Installing backend API deps..."
pip install --quiet \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29" \
    "python-multipart>=0.0.9" \
    "aiofiles>=23.2.1" \
    "opencv-python>=4.8.0" \
    "face-alignment>=1.4.1" \
    "gdown>=5.1.0"

echo "==> Dependencies installed."

# ── 3. Clone Wav2Lip (directory may exist but be incomplete — only checkpoints) ──
WAV2LIP_INFERENCE="$BACKEND_DIR/Wav2Lip/inference.py"
if [ ! -f "$WAV2LIP_INFERENCE" ]; then
    if [ -d "$BACKEND_DIR/Wav2Lip" ]; then
        echo "==> Wav2Lip folder exists but repo is incomplete; repairing (keeping downloaded weights)..."
        _bk="$BACKEND_DIR/.wav2lip_weights_backup"
        rm -rf "$_bk"
        mkdir -p "$_bk/checkpoints" "$_bk/sfd"
        shopt -s nullglob
        for _f in "$BACKEND_DIR/Wav2Lip/checkpoints/"*.pth; do cp -a "$_f" "$_bk/checkpoints/"; done
        for _f in "$BACKEND_DIR/Wav2Lip/face_detection/detection/sfd/"*.pth; do cp -a "$_f" "$_bk/sfd/"; done
        shopt -u nullglob
        rm -rf "$BACKEND_DIR/Wav2Lip"
    fi
    echo "==> Cloning Wav2Lip..."
    git clone https://github.com/Rudrabha/Wav2Lip.git
    cd Wav2Lip
    git submodule update --init --recursive
    cd "$BACKEND_DIR"
    if [ -d "$BACKEND_DIR/.wav2lip_weights_backup" ]; then
        mkdir -p "$BACKEND_DIR/Wav2Lip/checkpoints" "$BACKEND_DIR/Wav2Lip/face_detection/detection/sfd"
        shopt -s nullglob
        for _f in "$BACKEND_DIR/.wav2lip_weights_backup/checkpoints/"*.pth; do cp -a "$_f" "$BACKEND_DIR/Wav2Lip/checkpoints/"; done
        for _f in "$BACKEND_DIR/.wav2lip_weights_backup/sfd/"*.pth; do cp -a "$_f" "$BACKEND_DIR/Wav2Lip/face_detection/detection/sfd/"; done
        shopt -u nullglob
        rm -rf "$BACKEND_DIR/.wav2lip_weights_backup"
    fi
else
    echo "==> Wav2Lip repo already present."
fi

# ── 4. Download Wav2Lip GAN checkpoint (~422MB) ──
WAV2LIP_CKPT="$BACKEND_DIR/Wav2Lip/checkpoints/wav2lip_gan.pth"
mkdir -p "$BACKEND_DIR/Wav2Lip/checkpoints"
if [ ! -f "$WAV2LIP_CKPT" ]; then
    echo "==> Downloading Wav2Lip GAN checkpoint (~436MB)..."
    # GitHub release asset is often 404; Rudrabha HF can return 401. Public mirror works without auth.
    _wav2lip_ok=0
    for _url in \
        "https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth" \
        "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
        "https://huggingface.co/Rudrabha/Wav2Lip/resolve/main/wav2lip_gan.pth"
    do
        echo "==> Trying: $_url"
        rm -f "$WAV2LIP_CKPT"
        if download_file "$_url" "$WAV2LIP_CKPT"; then
            _sz=$(wc -c <"$WAV2LIP_CKPT" | tr -d " ")
            if [ "${_sz:-0}" -gt 150000000 ]; then
                _wav2lip_ok=1
                break
            fi
            echo "==> Download too small (${_sz} bytes), trying next mirror..."
        fi
    done
    if [ "$_wav2lip_ok" -ne 1 ]; then
        echo "ERROR: Could not download wav2lip_gan.pth from any mirror." >&2
        exit 1
    fi
else
    echo "==> Wav2Lip checkpoint already present."
fi

# ── 5. Download s3fd face detector for Wav2Lip (~90MB) ──
FACE_DET_DIR="$BACKEND_DIR/Wav2Lip/face_detection/detection/sfd"
FACE_DET_FILE="$FACE_DET_DIR/s3fd.pth"
mkdir -p "$FACE_DET_DIR"
if [ ! -f "$FACE_DET_FILE" ]; then
    echo "==> Downloading s3fd face detection model (~90MB)..."
    download_file "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" "$FACE_DET_FILE"
else
    echo "==> Face detection model already present."
fi

# ── 6. Create runtime directories ──
mkdir -p "$BACKEND_DIR/jobs"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    echo ""
    echo "Note: ffmpeg and ffprobe are required for video/audio. On macOS install with:"
    echo "  brew install ffmpeg"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "To start the backend:"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
