import time
import psutil
import subprocess
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="YT Stream API")

START_TIME = time.time()
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
MAX_VIDEO_QUALITY = "360p"


# ==========================
# UTILS
# ==========================
def uptime():
    s = int(time.time() - START_TIME)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}h {m}m {s}s"


def load_level(cpu):
    if cpu < 40:
        return "LOW"
    elif cpu < 70:
        return "MEDIUM"
    return "HIGH"


# ==========================
# ROOT / PING
# ==========================
@app.get("/")
def root():
    return {
        "status": "running",
        "uptime": uptime(),
        "endpoints": ["/audio", "/video", "/status", "/ping"]
    }


@app.get("/ping")
def ping():
    return {"ping": "pong", "uptime": uptime()}


# ==========================
# STATUS
# ==========================
@app.get("/status")
def status():
    cpu = psutil.cpu_percent(interval=0.4)
    ram = psutil.virtual_memory()

    return {
        "cpu": {
            "usage_percent": cpu,
            "load": load_level(cpu)
        },
        "ram": {
            "total_mb": ram.total // 1024 // 1024,
            "used_mb": ram.used // 1024 // 1024,
            "usage_percent": ram.percent
        },
        "video_policy": {
            "max_quality": MAX_VIDEO_QUALITY,
            "allowed": cpu < 80
        }
    }


# ==========================
# AUDIO STREAM (WORKING)
# ==========================
@app.get("/audio")
def audio(url: str = Query(...)):
    cmd = [
        YTDLP,
        "--cookies", COOKIES,
        "--force-ipv4",
        "-f", "ba/b",
        "-o", "-",
        url
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        raise HTTPException(500, "yt-dlp failed")

    return StreamingResponse(
        proc.stdout,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"}
    )


# ==========================
# VIDEO STREAM (360p) ✔ /vplay
# ==========================
@app.get("/video")
def video(url: str = Query(...)):
    cpu = psutil.cpu_percent(interval=0.3)

    if cpu > 80:
        return JSONResponse(
            {"status": "blocked", "reason": "high_cpu"},
            status_code=503
        )

    cmd = [
        YTDLP,
        "--cookies", COOKIES,
        "--force-ipv4",
        "-f", "bv*[height<=360]+ba/b",
        "--merge-output-format", "mp4",
        "-o", "-",
        url
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        raise HTTPException(500, "yt-dlp failed")

    return StreamingResponse(
        proc.stdout,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }
    )
