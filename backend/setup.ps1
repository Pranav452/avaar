# AI Video Dubbing System - Windows Setup Script
# Run from PowerShell: .\setup.ps1
# Or double-click setup.bat in Explorer.
#
# What this script does:
#   1. Installs Python 3.11, Git, and FFmpeg via winget (if not present)
#   2. Creates a Python virtualenv inside backend\venv
#   3. Installs all Python dependencies inside the venv
#   4. Clones Wav2Lip and downloads model checkpoints
#   5. Starts the FastAPI backend server (uvicorn)

$ErrorActionPreference = "Stop"

$BackendDir = $PSScriptRoot
if (-not $BackendDir) {
    $BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

Write-Host "==> Setting up backend at $BackendDir"
Set-Location $BackendDir

# ── Helpers ───────────────────────────────────────────────────────────────────

function Refresh-EnvPath {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path    = "$machinePath;$userPath"
}

function Test-Cmd($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Download-File($url, $dest) {
    for ($i = 1; $i -le 5; $i++) {
        try {
            Write-Host "    Trying: $url"
            Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing `
                -MaximumRedirection 10 -TimeoutSec 300
            return $true
        } catch {
            Write-Host "    Attempt $i failed: $($_.Exception.Message)"
            if ($i -lt 5) { Start-Sleep 5 }
        }
    }
    return $false
}

# ── 1. Prerequisites via winget ───────────────────────────────────────────────

if (-not (Test-Cmd "winget")) {
    Write-Error @"
winget not found.
Install 'App Installer' from the Microsoft Store, then re-run this script.
Microsoft Store link: ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1
"@
    exit 1
}

# Python 3.11
if (-not (Test-Cmd "python")) {
    Write-Host "==> Installing Python 3.11..."
    winget install --id Python.Python.3.11 --source winget `
        --accept-package-agreements --accept-source-agreements -e --silent
    Refresh-EnvPath
    # winget may install to a user-local path; also try the common py launcher
    if (-not (Test-Cmd "python")) {
        $pyPath = "$env:LOCALAPPDATA\Programs\Python\Python311"
        if (Test-Path "$pyPath\python.exe") {
            $env:Path = "$pyPath;$pyPath\Scripts;$env:Path"
        }
    }
} else {
    Write-Host "==> Python already installed: $(python --version 2>&1)"
}

# Git
if (-not (Test-Cmd "git")) {
    Write-Host "==> Installing Git..."
    winget install --id Git.Git --source winget `
        --accept-package-agreements --accept-source-agreements -e --silent
    Refresh-EnvPath
    # Common Git install path
    $gitPath = "$env:ProgramFiles\Git\cmd"
    if (Test-Path $gitPath) { $env:Path = "$gitPath;$env:Path" }
} else {
    Write-Host "==> Git already installed: $(git --version 2>&1)"
}

# FFmpeg
if (-not (Test-Cmd "ffmpeg")) {
    Write-Host "==> Installing FFmpeg..."
    winget install --id Gyan.FFmpeg --source winget `
        --accept-package-agreements --accept-source-agreements -e --silent
    Refresh-EnvPath
} else {
    Write-Host "==> FFmpeg already installed."
}

# Final PATH refresh before Python work
Refresh-EnvPath

# ── 2. Create virtualenv ──────────────────────────────────────────────────────

$VenvDir    = Join-Path $BackendDir "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip    = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "==> Creating virtualenv..."
    python -m venv $VenvDir
} else {
    Write-Host "==> venv already exists, skipping creation."
}

# Activate (sets $env:VIRTUAL_ENV and adjusts PATH for this session)
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
& $ActivateScript

Write-Host "==> Python: $(python --version 2>&1)"
python -m pip install --upgrade pip --quiet

# ── 3. Python packages ────────────────────────────────────────────────────────

Write-Host "==> Installing numpy (pinned <2.0)..."
pip install --quiet "numpy<2.0"

# Detect NVIDIA GPU — install CUDA-enabled PyTorch when possible
$hasCuda = Test-Cmd "nvidia-smi"
if ($hasCuda) {
    Write-Host "==> NVIDIA GPU detected — installing PyTorch 2.6 with CUDA 12.1..."
    pip install --quiet "torch==2.6.0" "torchaudio==2.6.0" `
        --index-url https://download.pytorch.org/whl/cu121
} else {
    Write-Host "==> No NVIDIA GPU detected — installing PyTorch 2.6 (CPU)..."
    pip install --quiet "torch==2.6.0" "torchaudio==2.6.0"
}

Write-Host "==> Torch: $(python -c "import torch; print(torch.__version__, '| CUDA:', torch.cuda.is_available())" 2>&1)"

# torchcodec has no Windows wheel on PyPI — skip gracefully
Write-Host "==> Attempting torchcodec install (optional, no Windows wheel on PyPI)..."
pip install --quiet "torchcodec==0.2.1" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    torchcodec not available for Windows — skipping (not required for core pipeline)."
    $LASTEXITCODE = 0
}

Write-Host "==> Installing transformers 4.46.3..."
pip install --quiet "transformers==4.46.3"

Write-Host "==> Installing Coqui TTS 0.22.0 + coqpit..."
pip install --quiet "coqpit==0.0.17" "TTS==0.22.0"

Write-Host "==> Installing backend API dependencies..."
pip install --quiet `
    "fastapi>=0.110.0" `
    "uvicorn[standard]>=0.29" `
    "python-multipart>=0.0.9" `
    "aiofiles>=23.2.1" `
    "opencv-python>=4.8.0" `
    "face-alignment>=1.4.1" `
    "gdown>=5.1.0"

Write-Host "==> All Python dependencies installed."

# ── 4. Clone Wav2Lip ──────────────────────────────────────────────────────────

$Wav2LipDir       = Join-Path $BackendDir "Wav2Lip"
$Wav2LipInference = Join-Path $Wav2LipDir "inference.py"

if (-not (Test-Path $Wav2LipInference)) {
    if (Test-Path $Wav2LipDir) {
        Write-Host "==> Wav2Lip folder exists but is incomplete — repairing (keeping any downloaded weights)..."
        $Backup = Join-Path $BackendDir ".wav2lip_weights_backup"
        New-Item -ItemType Directory -Force -Path "$Backup\checkpoints", "$Backup\sfd" | Out-Null
        Get-ChildItem "$Wav2LipDir\checkpoints\*.pth" -ErrorAction SilentlyContinue |
            Copy-Item -Destination "$Backup\checkpoints\" -ErrorAction SilentlyContinue
        Get-ChildItem "$Wav2LipDir\face_detection\detection\sfd\*.pth" -ErrorAction SilentlyContinue |
            Copy-Item -Destination "$Backup\sfd\" -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force $Wav2LipDir
    }

    Write-Host "==> Cloning Wav2Lip..."
    git clone https://github.com/Rudrabha/Wav2Lip.git $Wav2LipDir
    Set-Location $Wav2LipDir
    git submodule update --init --recursive
    Set-Location $BackendDir

    $Backup = Join-Path $BackendDir ".wav2lip_weights_backup"
    if (Test-Path $Backup) {
        New-Item -ItemType Directory -Force -Path `
            "$Wav2LipDir\checkpoints", `
            "$Wav2LipDir\face_detection\detection\sfd" | Out-Null
        Get-ChildItem "$Backup\checkpoints\*.pth" -ErrorAction SilentlyContinue |
            Copy-Item -Destination "$Wav2LipDir\checkpoints\" -ErrorAction SilentlyContinue
        Get-ChildItem "$Backup\sfd\*.pth" -ErrorAction SilentlyContinue |
            Copy-Item -Destination "$Wav2LipDir\face_detection\detection\sfd\" -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force $Backup
    }
} else {
    Write-Host "==> Wav2Lip repo already present."
}

# ── 5. Download Wav2Lip GAN checkpoint (~436 MB) ──────────────────────────────

$Ckpt    = Join-Path $Wav2LipDir "checkpoints\wav2lip_gan.pth"
New-Item -ItemType Directory -Force -Path (Join-Path $Wav2LipDir "checkpoints") | Out-Null

if (-not (Test-Path $Ckpt)) {
    Write-Host "==> Downloading Wav2Lip GAN checkpoint (~436 MB)..."
    $mirrors = @(
        "https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth",
        "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth",
        "https://huggingface.co/Rudrabha/Wav2Lip/resolve/main/wav2lip_gan.pth"
    )
    $ok = $false
    foreach ($url in $mirrors) {
        if (Test-Path $Ckpt) { Remove-Item $Ckpt -Force }
        if (Download-File $url $Ckpt) {
            $sz = (Get-Item $Ckpt -ErrorAction SilentlyContinue).Length
            if ($sz -gt 150000000) { $ok = $true; break }
            Write-Host "    File too small ($sz bytes), trying next mirror..."
        }
    }
    if (-not $ok) {
        Write-Error "ERROR: Could not download wav2lip_gan.pth from any mirror."
        exit 1
    }
    Write-Host "==> Wav2Lip GAN checkpoint downloaded."
} else {
    Write-Host "==> Wav2Lip GAN checkpoint already present."
}

# ── 6. Download s3fd face detection model (~90 MB) ────────────────────────────

$FaceDetDir  = Join-Path $Wav2LipDir "face_detection\detection\sfd"
$FaceDetFile = Join-Path $FaceDetDir "s3fd.pth"
New-Item -ItemType Directory -Force -Path $FaceDetDir | Out-Null

if (-not (Test-Path $FaceDetFile)) {
    Write-Host "==> Downloading s3fd face detection model (~90 MB)..."
    $downloaded = Download-File `
        "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" `
        $FaceDetFile
    if (-not $downloaded) {
        Write-Error "ERROR: Could not download s3fd.pth."
        exit 1
    }
    Write-Host "==> s3fd model downloaded."
} else {
    Write-Host "==> Face detection model already present."
}

# ── 7. Runtime directories ────────────────────────────────────────────────────

New-Item -ItemType Directory -Force -Path (Join-Path $BackendDir "jobs") | Out-Null

# ── 8. Start the server ───────────────────────────────────────────────────────

Write-Host ""
Write-Host "Setup complete. Starting backend server..."
Write-Host "  URL : http://localhost:8000"
Write-Host "  Docs: http://localhost:8000/docs"
Write-Host "  Press Ctrl+C to stop."
Write-Host ""

Set-Location $BackendDir
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
