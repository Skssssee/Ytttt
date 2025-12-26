# api.py
import random
import subprocess
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException

# ================= CONFIG =================

COOKIE_FILE = Path("cookies.txt")
PROXY_FILE = Path("proxy.txt")

# ==========================================

app = FastAPI(title="YouTube Audio API", version="1.0")


# ---------- Proxy Handler ----------
def get_proxy():
    if not PROXY_FILE.exists():
        return None

    proxies = [
        p.strip()
        for p in PROXY_FILE.read_text().splitlines()
        if p.strip()
    ]
    return random.choice(proxies) if proxies else None


# ---------- Core yt-dlp Logic ----------
def extract_audio_url(youtube_url: str) -> str:
    if not COOKIE_FILE.exists():
        raise RuntimeError("cookies.txt not found")

    proxy = get_proxy()

    cmd = [
        "yt-dlp",
        "--cookies", str(COOKIE_FILE),
        "--remote-components", "ejs:github",
        "--extractor-args", "youtube:player_client=web",
        "-f", "bestaudio",
        "-g",
        youtube_url,
    ]

    if proxy:
        cmd.insert(1, "--proxy")
        cmd.insert(2, proxy)

    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
        )
        return output.strip()

    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.output)


# ================= API ROUTES =================

@app.get("/")
def root():
    return {
        "status": "running",
        "proxy_enabled": PROXY_FILE.exists(),
        "cookies_loaded": COOKIE_FILE.exists(),
    }


@app.get("/audio")
def get_audio(
    url: str = Query(..., description="YouTube video URL"),
):
    try:
        audio_url = extract_audio_url(url)
        return {
            "status": "success",
            "audio_url": audio_url,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )
