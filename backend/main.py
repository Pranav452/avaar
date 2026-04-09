"""FastAPI backend for the AI Video Dubbing System.

Endpoints:
  POST   /process          — upload video + text, start background pipeline
  GET    /status/{job_id}  — poll processing status
  GET    /download/{job_id}— stream finished MP4
  DELETE /job/{job_id}     — cleanup job files + state

The pipeline (run_pipeline) is a plain def so FastAPI's BackgroundTasks
dispatches it on the threadpool executor — correct for CPU/GPU-bound work.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# ── App setup ───────────────────────────────────────────────────────────────

app = FastAPI(title="AI Video Dubbing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── State ────────────────────────────────────────────────────────────────────

# In-memory job store — survives within a single uvicorn worker process.
# Keys: job_id (str)
# Values: { status, progress, message }
jobs: dict[str, dict[str, Any]] = {}

JOBS_DIR = Path(__file__).parent / "jobs"
JOBS_DIR.mkdir(exist_ok=True)


# ── Startup: pre-warm XTTS-v2 so the first user job isn't slow ──────────────

@app.on_event("startup")
def preload_tts() -> None:
    """Load XTTS-v2 into GPU memory at server start (downloads model if needed)."""
    try:
        from voice_clone import get_tts_model
        get_tts_model()
    except Exception as exc:
        # Non-fatal — model will be loaded lazily on first job instead
        print(f"[startup] TTS preload skipped: {exc}")


# ── Pipeline ─────────────────────────────────────────────────────────────────

def _update(job_id: str, status: str, progress: int, message: str) -> None:
    jobs[job_id] = {"status": status, "progress": progress, "message": message}


def run_pipeline(job_id: str, job_dir: Path, text: str, language: str) -> None:
    """Full dubbing pipeline — runs in FastAPI's threadpool (not async)."""
    try:
        from lip_sync import sync_lips
        from video_utils import check_min_audio_duration, extract_audio
        from voice_clone import clone_voice

        input_video = job_dir / "input.mp4"
        audio_wav = job_dir / "audio.wav"
        speech_wav = job_dir / "speech.wav"
        output_mp4 = job_dir / "output.mp4"

        # Step 1 — extract speaker audio
        _update(job_id, "processing", 5, "Extracting audio from video")
        extract_audio(input_video, audio_wav)
        check_min_audio_duration(audio_wav, min_seconds=3.0)

        # Step 2 — clone voice & synthesise new speech
        _update(job_id, "processing", 20, "Cloning voice with XTTS-v2 (GPU)")
        clone_voice(audio_wav, text, language, speech_wav)

        # Step 3 — lip sync
        _update(job_id, "processing", 60, "Syncing lips with Wav2Lip (GPU)")
        sync_lips(input_video, speech_wav, output_mp4)

        _update(job_id, "done", 100, "Complete — ready to download")

    except Exception as exc:
        jobs[job_id] = {"status": "error", "progress": 0, "message": str(exc)}
        print(f"[pipeline] Job {job_id} failed: {exc}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/process")
async def process_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form(default="en"),
) -> JSONResponse:
    """Accept a video upload + new script and start the dubbing pipeline."""
    if not text.strip():
        return JSONResponse({"error": "text must not be empty"}, status_code=422)

    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True)

    # Persist the uploaded video
    input_path = job_dir / "input.mp4"
    async with aiofiles.open(input_path, "wb") as f:
        content = await video.read()
        await f.write(content)

    jobs[job_id] = {"status": "queued", "progress": 0, "message": "Queued"}

    background_tasks.add_task(run_pipeline, job_id, job_dir, text.strip(), language)

    return JSONResponse({"job_id": job_id})


@app.get("/status/{job_id}")
async def get_status(job_id: str) -> JSONResponse:
    """Return current job status."""
    if job_id not in jobs:
        return JSONResponse(
            {"status": "not_found", "progress": 0, "message": "Job not found"},
            status_code=404,
        )
    return JSONResponse(jobs[job_id])


@app.get("/download/{job_id}")
async def download_result(job_id: str) -> FileResponse:
    """Stream the finished MP4. Supports HTTP range requests for video scrubbing."""
    output_path = JOBS_DIR / job_id / "output.mp4"
    if not output_path.exists():
        return JSONResponse({"error": "Output not ready"}, status_code=404)
    return FileResponse(
        str(output_path),
        media_type="video/mp4",
        filename=f"dubbed_{job_id[:8]}.mp4",
    )


@app.delete("/job/{job_id}")
async def delete_job(job_id: str) -> JSONResponse:
    """Remove job files and state."""
    job_dir = JOBS_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    jobs.pop(job_id, None)
    return JSONResponse({"deleted": job_id})


@app.get("/")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "AI Video Dubbing API"})
