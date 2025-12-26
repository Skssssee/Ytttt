import subprocess
import random
import time
from fastapi import FastAPI, Query, HTTPException

app = FastAPI()

COOKIES_FILE = "cookies.txt"
PROXY_FILE = "proxy.txt"
TIMEOUT = 90


# -------------------------------
# Load SOCKS5 proxies only
# -------------------------------
def load_socks5_proxies():
    try:
        with open(PROXY_FILE, "r") as f:
            return [
                p.strip()
                for p in f.readlines()
                if p.strip().startswith("socks5://")
            ]
    except FileNotFoundError:
        return []


# -------------------------------
# yt-dlp runner with auto rotate
# -------------------------------
def fetch_audio_url(video_url: str):
    proxies = load_socks5_proxies()
    random.shuffle(proxies)

    last_error = None

    # Try with proxy first
    for proxy in proxies:
        try:
            print(f"[TRYING PROXY] {proxy}")

            cmd = [
                "yt-dlp",
                "--cookies", COOKIES_FILE,
                "--remote-components", "ejs:github",
                "--force-ipv4",
                "--proxy", proxy,
                "-f", "bestaudio",
                "-g",
                video_url,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT
            )

            if result.returncode == 0 and result.stdout.strip():
                print("[SUCCESS WITH PROXY]")
                return result.stdout.strip()

            last_error = result.stderr

        except Exception as e:
            last_error = str(e)

    # -------------------------------
    # Fallback: WITHOUT PROXY
    # -------------------------------
    try:
        print("[FALLBACK] Trying without proxy")

        cmd = [
            "yt-dlp",
            "--cookies", COOKIES_FILE,
            "--remote-components", "ejs:github",
            "--force-ipv4",
            "-f", "bestaudio",
            "-g",
            video_url,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )

        if result.returncode == 0 and result.stdout.strip():
            print("[SUCCESS WITHOUT PROXY]")
            return result.stdout.strip()

        last_error = result.stderr

    except Exception as e:
        last_error = str(e)

    raise Exception(last_error or "yt-dlp failed")


# -------------------------------
# API Endpoint
# -------------------------------
@app.get("/audio")
def get_audio(url: str = Query(...)):
    try:
        audio_url = fetch_audio_url(url)
        return {
            "status": "success",
            "audio": audio_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
            )
