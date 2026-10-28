import os, json, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
AUDIO_DIR = BASE_DIR / "audio"
MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output"

for d in (SESSIONS_DIR, AUDIO_DIR, MODELS_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 22050
INSTRUMENTS = ["piano", "guitar", "drums"]

def new_session_dir():
    i = 1
    while (SESSIONS_DIR / f"session_{i:03d}").exists():
        i += 1
    p = SESSIONS_DIR / f"session_{i:03d}"
    p.mkdir(parents=True, exist_ok=True)
    return p
