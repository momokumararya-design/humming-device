import os
import numpy as np
import soundfile as sf

class ArrangementProvider:
    def __init__(self):
        self.available = False
        try:
            import transformers
            self.available = True
        except Exception:
            self.available = False

    def generate(self, guide_audio_path, prompt, out_path, sr=22050):
        if not self.available:
            # fallback: copy guide as arrangement placeholder
            audio, s = sf.read(guide_audio_path)
            sf.write(out_path, audio, s)
            return out_path, "fallback (no model)"
        try:
            from transformers import AutoProcessor, MusicgenMelodyForConditionalGeneration
            import torch
            processor = AutoProcessor.from_pretrained("facebook/musicgen-melody")
            model = MusicgenMelodyForConditionalGeneration.from_pretrained("facebook/musicgen-melody")
            import librosa
            audio, _ = librosa.load(guide_audio_path, sr=32000)
            inputs = processor(audio=audio, text=[prompt], sampling_rate=32000, return_tensors="pt")
            with torch.no_grad():
                out = model.generate(**inputs, do_sample=True, guidance_scale=3, max_new_tokens=256)
            wav = out[0].cpu().numpy()
            sf.write(out_path, wav.T if wav.ndim>1 else wav, 32000)
            return out_path, "musicgen"
        except Exception as e:
            audio, s = sf.read(guide_audio_path)
            sf.write(out_path, audio, s)
            return out_path, f"error: {e}"
