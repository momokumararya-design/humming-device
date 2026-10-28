import numpy as np
import sounddevice as sd
import soundfile as sf

def record(duration=10, sr=22050):
    rec = sd.rec(int(duration*sr), samplerate=sr, channels=1, dtype='float32')
    sd.wait()
    audio = rec.flatten()
    return audio, sr

def save(path, audio, sr):
    sf.write(path, audio, sr)

def load(path):
    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, sr

def playback(audio, sr):
    sd.play(audio, sr)
    sd.wait()
