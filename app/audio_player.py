import sounddevice as sd
import soundfile as sf

def play(path):
    audio, sr = sf.read(path)
    sd.play(audio, sr)
    sd.wait()

def stop():
    sd.stop()
