import numpy as np
import librosa

def extract_melody(times, f0, voiced_prob, sr, hop=512):
    notes = []
    # quantize f0 to midi
    midi = librosa.hz_to_midi(np.nan_to_num(f0, nan=0.0))
    # simple grouping
    cur = None
    start = None
    for i, m in enumerate(midi):
        if voiced_prob[i] < 0.3 or m <= 0:
            if cur is not None:
                dur = times[i-1]-start if i>0 else 0.1
                notes.append({"pitch": librosa.midi_to_note(int(round(cur)), octave=True), "midi_note": int(round(cur)), "start": float(start), "duration": float(max(0.05,dur)), "confidence": float(voiced_prob[i-1] if i>0 else 0.5)})
                cur=None
            continue
        rm = int(round(m))
        if cur is None or rm != cur:
            if cur is not None:
                dur = times[i]-start
                notes.append({"pitch": librosa.midi_to_note(int(round(cur)), octave=True), "midi_note": int(round(cur)), "start": float(start), "duration": float(max(0.05,dur)), "confidence": float(voiced_prob[i-1] if i>0 else 0.5)})
            cur = rm
            start = times[i]
    if cur is not None:
        dur = times[-1]-start+0.1
        notes.append({"pitch": librosa.midi_to_note(int(round(cur)), octave=True), "midi_note": int(round(cur)), "start": float(start), "duration": float(max(0.05,dur)), "confidence": float(voiced_prob[-1])})
    # merge same consecutive
    merged=[]
    for n in notes:
        if merged and merged[-1]["midi_note"]==n["midi_note"] and n["start"]-merged[-1]["start"]-merged[-1]["duration"]<0.15:
            merged[-1]["duration"]=n["start"]+n["duration"]-merged[-1]["start"]
        else:
            merged.append(n)
    merged=[n for n in merged if n["duration"]>=0.06]
    return {"notes": merged, "tempo_bpm": None}
