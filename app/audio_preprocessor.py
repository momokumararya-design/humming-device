import numpy as np
import librosa

def preprocess(audio, sr):
    audio = audio - np.mean(audio)
    peak = np.max(np.abs(audio)) + 1e-9
    audio = audio / peak * 0.9
    return audio

def voiced_regions(audio, sr):
    intervals = librosa.effects.split(audio, top_db=40)
    return [(s/sr, e/sr) for s,e in intervals]
