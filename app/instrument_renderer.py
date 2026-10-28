import numpy as np
import pretty_midi
import soundfile as sf

def render_midi(midi_path, wav_path, sr=22050):
    pm = pretty_midi.PrettyMIDI(midi_path)
    # simple harmonic synth
    audio = np.zeros(0)
    total = pm.get_end_time() + 0.5
    audio = np.zeros(int(total*sr))
    for inst in pm.instruments:
        for note in inst.notes:
            start = int(note.start*sr)
            end = int(note.end*sr)
            dur = end-start
            if dur <= 0: continue
            t = np.arange(dur)/sr
            freq = pretty_midi.note_number_to_hz(note.pitch)
            wave = (np.sin(2*np.pi*freq*t) + 0.5*np.sin(2*np.pi*2*freq*t) + 0.25*np.sin(2*np.pi*3*freq*t))
            # ADSR
            env = np.ones(dur)
            attack = min(int(0.01*sr), dur)
            release = min(int(0.05*sr), dur)
            env[:attack] = np.linspace(0,1,attack)
            env[-release:] = np.linspace(1,0,release)
            amp = note.velocity/127.0
            wave = wave*env*amp*0.3
            audio[start:start+dur] += wave
    # normalize
    peak = np.max(np.abs(audio))+1e-9
    audio = audio/peak*0.8
    sf.write(wav_path, audio, sr)
    return wav_path
