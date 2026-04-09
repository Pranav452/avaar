#!/bin/bash
# AI Video Dubbing System - One-time environment setup
# Run this in WSL: bash setup.sh
set -e

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> Setting up backend at $BACKEND_DIR"
cd "$BACKEND_DIR"

# ── 1. Create venv (inherits global torch, librosa, fastapi, transformers) ──
if [ ! -d "venv" ]; then
    echo "==> Creating virtualenv with --system-site-packages..."
    python3 -m venv venv --system-site-packages
else
    echo "==> venv already exists, skipping creation"
fi

source venv/bin/activate
echo "==> Python: $(python --version)"
echo "==> Checking CUDA: $(python -c 'import torch; print("torch", torch.__version__, "| CUDA:", torch.cuda.is_available())')"

# ── 2. Install only what isn't already present ──
echo "==> Installing Python dependencies..."
pip install --upgrade --quiet \
    "TTS>=0.22.0" \
    "opencv-python>=4.8.0" \
    "face-alignment>=1.4.1" \
    "gdown>=5.1.0" \
    "uvicorn[standard]>=0.29" \
    "python-multipart>=0.0.9" \
    "aiofiles>=23.2.1"

echo "==> Dependencies installed."

# ── 3. Clone Wav2Lip ──
if [ ! -d "Wav2Lip" ]; then
    echo "==> Cloning Wav2Lip..."
    git clone https://github.com/Rudrabha/Wav2Lip.git
    cd Wav2Lip
    # face_detection is a git submodule — must init separately
    git submodule update --init --recursive
    cd "$BACKEND_DIR"
else
    echo "==> Wav2Lip already cloned."
fi

# ── 4. Download Wav2Lip GAN checkpoint (~422MB) ──
WAV2LIP_CKPT="$BACKEND_DIR/Wav2Lip/checkpoints/wav2lip_gan.pth"
mkdir -p "$BACKEND_DIR/Wav2Lip/checkpoints"
if [ ! -f "$WAV2LIP_CKPT" ]; then
    echo "==> Downloading Wav2Lip GAN checkpoint (~422MB)..."
    # Try direct mirror URL first (faster, more reliable)
    wget -q --show-progress \
        "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth" \
        -O "$WAV2LIP_CKPT" 2>&1 || {
        echo "==> GitHub mirror failed, trying HuggingFace..."
        wget -q --show-progress \
            "https://huggingface.co/Rudrabha/Wav2Lip/resolve/main/wav2lip_gan.pth" \
            -O "$WAV2LIP_CKPT"
    }
else
    echo "==> Wav2Lip checkpoint already present."
fi

# ── 5. Download s3fd face detector for Wav2Lip (~90MB) ──
FACE_DET_DIR="$BACKEND_DIR/Wav2Lip/face_detection/detection/sfd"
FACE_DET_FILE="$FACE_DET_DIR/s3fd.pth"
mkdir -p "$FACE_DET_DIR"
if [ ! -f "$FACE_DET_FILE" ]; then
    echo "==> Downloading s3fd face detection model (~90MB)..."
    wget -q --show-progress \
        "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" \
        -O "$FACE_DET_FILE"
else
    echo "==> Face detection model already present."
fi

# ── 6. Create runtime directories ──
mkdir -p "$BACKEND_DIR/jobs"

echo ""
echo "✓ Setup complete!"
echo ""
echo "To start the backend:"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
