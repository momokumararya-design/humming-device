import numpy as np
from swift_f0 import SwiftF0

_det = SwiftF0()

def detect_pitch(audio, sr):
    res = _det.detect(audio.astype('float32'), sr)
    times = res.timestamps
    f0 = res.pitch_hz
    prob = res.confidence
    return times, f0, prob
