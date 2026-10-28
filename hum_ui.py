import ctypes
import math
import time
import threading
import tkinter as tk
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import random
from dataclasses import dataclass

import librosa
import numpy as np
import sounddevice as sd
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageTk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import audio_recorder, audio_preprocessor, pitch_detector, melody_extractor, midi_generator, instrument_renderer, audio_player

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

HERE = Path(__file__).parent
SAVE_DIR = Path.home() / "Desktop"
ORANGE, DARK, BLACK, WHITE, GREY = "#CE5719", "#A8470F", "#000000", "#FFFFFF", "#3A3A3A"
W, H = 380, 470
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ANCHOR = {"nw": "la", "ne": "ra", "center": "mm", "w": "lm", "e": "rm"}
RECORD_SECONDS = 8

@lru_cache(maxsize=None)
def load_font(px):
    for f in (HERE / "Michroma-Regular.ttf", "bahnschrift.ttf", "segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(str(f), px)
        except OSError:
            continue
    return ImageFont.load_default()

def to_midi(hz):
    return 69 + 12 * math.log2(hz / 440.0)

def midi_name(m):
    m = int(round(m))
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"

def note_stats(notes):
    if not notes:
        return {"Median": "-", "Spread": "-", "Notes": "0", "Tuning": "-"}
    m = np.array([to_midi(n.pitch_hz) for n in notes])
    cents = (m - np.round(m)) * 100
    return {"Median": midi_name(np.median(m)), "Spread": f"{m.max() - m.min():.0f} st",
            "Notes": str(len(notes)), "Tuning": f"{cents.mean():+.0f} c"}

@dataclass
class Note:
    start: float
    end: float
    pitch_hz: float

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.S = max(1.0, self.root.winfo_fpixels("1i") / 96)
        self.K = self.S * 2
        self.root.title("Hum")
        self.root.geometry(f"{int(W * self.S)}x{int(H * self.S)}+60+60")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.cv = tk.Canvas(self.root, width=int(W * self.S), height=int(H * self.S), bg=BLACK, highlightthickness=0)
        self.cv.pack()
        self.item = self.cv.create_image(0, 0, anchor="nw")
        self.cv.bind("<Button-1>", self.on_click)
        self.mic = "Microphone"
        self.state, self.mode, self.msg, self.error = "idle", "piano", "", ""
        self.chunks, self.levels, self.stream, self.t0 = [], [], None, 0.0
        self.result, self.notes, self.duration = None, [], 0.0
        self.playing, self.play_t0, self.play_len, self.saved = False, 0.0, 0.0, None
        self.hit = []
        self.audio = None
        self.sr = 22050
        self.melody = None
        self.instrument = "Piano"
        self.draw()
        self.tick()

    def run(self):
        self.root.mainloop()

    def rr(self, x1, y1, x2, y2, r=8, fill=None, outline=None, width=1):
        K = self.K
        self.d.rounded_rectangle([x1 * K, y1 * K, x2 * K, y2 * K], radius=r * K, fill=fill, outline=outline, width=max(1, int(width * K)))

    def rect(self, x1, y1, x2, y2, fill):
        K = self.K
        self.d.rectangle([x1 * K, y1 * K, x2 * K, y2 * K], fill=fill)

    def line(self, x1, y1, x2, y2, fill, width=1):
        K = self.K
        self.d.line([x1 * K, y1 * K, x2 * K, y2 * K], fill=fill, width=max(1, int(width * K)))

    def text(self, x, y, s, size, color=WHITE, anchor="nw"):
        K = self.K
        self.d.text((x * K, y * K), s, fill=color, font=load_font(int(size * 1.35 * K)), anchor=ANCHOR[anchor])

    def button(self, name, x1, y1, x2, y2, label, filled=True, size=8):
        if filled:
            self.rr(x1, y1, x2, y2, fill=ORANGE)
        else:
            self.rr(x1, y1, x2, y2, fill=BLACK, outline=ORANGE, width=2)
        self.text((x1 + x2) / 2, (y1 + y2) / 2, label, size, BLACK if filled else ORANGE, "center")
        self.hit.append((name, x1, y1, x2, y2))

    def dots(self, y):
        for x in range(40, 340, 6):
            self.rect(x, y, x + 3, y + 3, BLACK)

    def draw(self):
        self.img = Image.new("RGB", (int(W * self.K), int(H * self.K)), BLACK)
        self.d = ImageDraw.Draw(self.img)
        self.hit = []
        now = datetime.now()
        self.text(40, 40, f"{now:%A} {now.day}", 8)
        self.text(38, 58, f"{now:%H:%M}", 26)
        {"idle": self.screen_record, "recording": self.screen_record,
         "output": self.screen_output, "save": self.screen_save}[self.state]()
        out = self.img.resize((int(W * self.S), int(H * self.S)), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(out)
        self.cv.itemconfig(self.item, image=self.photo)

    def screen_record(self):
        rec = self.state == "recording"
        self.text(38, 212, "Recording" if rec else "Start recording", 8)
        self.rr(28, 240, 352, 310, fill=ORANGE)
        self.dots(272)
        if rec:
            for i, lv in enumerate(self.levels[-50:]):
                h = min(1.0, lv * 6) * 26
                self.rect(40 + i * 6, 273.5 - h, 43 + i * 6, 273.5 + h, BLACK)
        secs = time.time() - self.t0 if rec else 0.0
        remaining = max(0, RECORD_SECONDS - secs) if rec else RECORD_SECONDS
        self.text(350, 318, f"{remaining:.1f}", 8, anchor="ne")
        if self.error:
            self.text(38, 350, self.error[:46], 6, ORANGE)
        else:
            self.text(38, 350, f"Mic: {self.mic[:40]}", 6, "#8A8A8A")
        self.hit.append(("panel", 28, 240, 352, 310))

    def screen_output(self):
        self.text(38, 112, self.msg, 8)
        self.draw_roll(28, 134, 352, 288)
        self.button("play", 28, 298, 108, 330, "Stop" if self.playing else "Play", True, 8)
        # only piano
        self.instrument = "Piano"
        for i, (k, v) in enumerate(note_stats(self.notes).items()):
            x1, y1 = 28 + (i % 2) * 168, 342 + (i // 2) * 38
            self.rr(x1, y1, x1 + 156, y1 + 30, fill=BLACK, outline=GREY)
            self.text(x1 + 10, y1 + 15, k.upper(), 6, WHITE, "w")
            self.text(x1 + 146, y1 + 15, v, 9, ORANGE, "e")
        self.button("next", 28, 424, 352, 456, "Generate & Save", True, 9)

    def screen_save(self):
        self.text(38, 212, "Saved" if self.saved else "Save", 8)
        self.rr(28, 240, 352, 310, fill=ORANGE)
        if self.saved:
            self.text(46, 258, "Saved to Desktop", 10, BLACK)
            self.text(46, 284, self.saved.name, 7, BLACK)
        else:
            self.text(46, 258, "Generating...", 10, BLACK)
        self.button("new", 28, 326, 352, 372, "Start new", False, 9)
        if self.saved:
            self.text(38, 392, f"Folder: {SAVE_DIR}", 6)

    def draw_roll(self, x1, y1, x2, y2):
        self.rr(x1, y1, x2, y2, fill=ORANGE)
        ms = [to_midi(n.pitch_hz) for n in self.notes]
        lo, hi = (math.floor(min(ms)) - 1, math.ceil(max(ms)) + 1) if ms else (57, 69)
        if hi - lo < 12:
            mid = (lo + hi) / 2
            lo, hi = mid - 6, mid + 6
        left, right = x1 + 44, x2 - 10
        top, bottom = y1 + 10, y2 - 10
        ypos = lambda m: bottom - (m - lo) / (hi - lo) * (bottom - top)
        for m in range(math.ceil(lo), math.floor(hi) + 1):
            if m % 12 in (0, 7):
                self.line(left, ypos(m), right, ypos(m), DARK)
                self.text(x1 + 8, ypos(m), midi_name(m), 6, BLACK, "w")
        dur = max(self.duration, 0.5)
        for n, m in zip(self.notes, ms):
            bx1 = left + n.start / dur * (right - left)
            bx2 = max(bx1 + 5, left + n.end / dur * (right - left))
            self.rr(bx1, ypos(m) - 4, bx2, ypos(m) + 4, r=4, fill=BLACK)
        if self.playing:
            px = left + min((time.time() - self.play_t0) / dur, 1.0) * (right - left)
            self.line(px, top, px, bottom, BLACK, 2)

    def tick(self):
        if self.state == "recording":
            self.levels.append(random.random() * 0.12)
            if time.time() - self.t0 >= RECORD_SECONDS:
                self.stop_recording()
        if self.playing and time.time() - self.play_t0 > self.play_len:
            self.playing = False
        if self.state in ("idle", "recording") or (self.state == "output" and self.playing):
            self.draw()
        self.root.after(80, self.tick)

    def on_click(self, e):
        x, y = e.x / self.S, e.y / self.S
        for name, x1, y1, x2, y2 in self.hit:
            if x1 <= x <= x2 and y1 <= y <= y2:
                try:
                    self.act(name)
                except Exception as err:
                    self.error = f"Error: {err}"
                self.draw()
                return

    def act(self, name):
        if name == "panel":
            self.start_recording() if self.state == "idle" else self.stop_recording()
        elif name == "play":
            self.toggle_play()
        elif name.startswith("inst_"):
            self.instrument = name.split("_",1)[1]
        elif name == "next":
            self.stop_play()
            self.generate_and_save()
        elif name == "new":
            self.state, self.saved, self.result, self.notes, self.error = "idle", None, None, [], ""
            self.audio = None; self.melody = None

    def start_recording(self):
        self.error, self.levels = "", []
        self.t0 = time.time()
        self.state = "recording"
        def worker():
            self.audio, self.sr = audio_recorder.record(duration=RECORD_SECONDS, sr=22050)
        threading.Thread(target=worker, daemon=True).start()

    def stop_recording(self):
        if self.audio is None:
            # wait briefly
            self.root.after(200, self.stop_recording); return
        self.state = "output"
        clean = audio_preprocessor.preprocess(self.audio, self.sr)
        times, f0, prob = pitch_detector.detect_pitch(clean, self.sr)
        melody = melody_extractor.extract_melody(times, f0, prob, self.sr)
        self.notes = [Note(n["start"], n["start"]+n["duration"], 440.0*2**((n["midi_note"]-69)/12.0)) for n in melody["notes"]]
        self.duration = self.audio.shape[0]/self.sr
        self.msg = f"Pitch detected  {self.duration:.1f}s" if self.notes else "No steady notes heard"
        self.melody = melody

    def toggle_play(self):
        if self.playing:
            return self.stop_play()
        self.playing, self.play_t0, self.play_len = True, time.time(), self.duration

    def stop_play(self):
        self.playing = False

    def generate_and_save(self):
        self.state = "save"
        self.saved = None
        def worker():
            import pretty_midi
            gm = {"Piano":0,"Guitar":25,"Flute":73}[self.instrument]
            notes = self.melody["notes"] if self.melody else []
            pm = pretty_midi.PrettyMIDI()
            inst = pretty_midi.Instrument(program=gm, name=self.instrument)
            for n in notes:
                inst.notes.append(pretty_midi.Note(velocity=90, pitch=n["midi_note"], start=n["start"], end=n["start"]+n["duration"]))
            pm.instruments.append(inst)
            midi_path = SAVE_DIR / f"melody-{datetime.now():%H%M%S}.mid"
            pm.write(str(midi_path))
            out = SAVE_DIR / f"{self.instrument.lower()}_output.wav"
            instrument_renderer.render_midi(str(midi_path), str(out))
            audio_player.play(str(out))
            self.saved = out
            self.draw()
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    # helper import
    import librosa
    def librosa_hz(midi):
        return librosa.midi_to_hz(midi)
    App().run()
