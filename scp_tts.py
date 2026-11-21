"""Local WAV synthesis/cache; v4 retains its Qt signals and Telegram Opus conversion."""

import hashlib
import math
import shutil
import subprocess
import threading
import time
import wave
from array import array
from pathlib import Path

__all__ = ["TTSEngine", "TTSPlayer"]


class TTSPlayer:
    def __init__(self):
        self.channel = None
        self.levels = []
        self.start = 0

    def play(self, path):
        try:
            import pygame
        except ImportError as exc:
            raise RuntimeError("Для воспроизведения нужен pygame") from exc
        self.stop()
        pygame.mixer.init()
        self.levels = []
        with wave.open(str(path), "rb") as f:
            while data := f.readframes(max(1, f.getframerate() // 25)):
                a = array("h", data) if f.getsampwidth() == 2 else []
                self.levels.append(
                    min(1, math.sqrt(sum(x * x for x in a) / max(1, len(a))) / 5000)
                )
        self.channel = pygame.mixer.Sound(str(path)).play()
        self.start = time.monotonic()

    def rms(self):
        i = int((time.monotonic() - self.start) * 25)
        return self.levels[i] if self.busy() and i < len(self.levels) else 0

    def busy(self):
        return bool(self.channel and self.channel.get_busy())

    def stop(self):
        if self.channel:
            self.channel.stop()


class TTSEngine:
    def __init__(self, root, cfg, fallback=None):
        self.root = root / "tts_cache"
        self.root.mkdir(exist_ok=True)
        self.cfg = cfg
        self.fallback = fallback
        self.player = TTSPlayer()
        self.lock = threading.RLock()
        self.ticket = 0
        self.xtts = None

    def _xtts(self, text, target, speed):
        """Use only explicit local checkpoint, vocabulary and reference audio."""
        try:
            import psutil
        except ImportError:
            return False
        folder = Path(self.cfg.get("xtts_model_dir") or "")
        speaker = Path(self.cfg.get("xtts_speaker_wav") or "")
        if not speaker.is_file() or not all(
            (folder / name).is_file()
            for name in ("config.json", "model.pth", "vocab.json")
        ):
            return False
        if self.xtts is None:
            reserve = max(3 * 1024**3, (folder / "model.pth").stat().st_size * 2)
            if reserve > min(
                psutil.virtual_memory().available,
                10.5 * 1024**3 - psutil.Process().memory_info().rss,
            ):
                return False
            try:
                from TTS.tts.configs.xtts_config import XttsConfig
                from TTS.tts.models.xtts import Xtts
            except ImportError:
                return False
            cfg = XttsConfig()
            cfg.load_json(str(folder / "config.json"))
            model = Xtts.init_from_config(cfg)
            model.load_checkpoint(
                cfg, checkpoint_dir=str(folder), eval=True, use_deepspeed=False
            )
            self.xtts = (model.cpu(), cfg)
        model, cfg = self.xtts
        samples = model.synthesize(
            text, cfg, speaker_wav=str(speaker), language="ru", speed=1 / speed
        )["wav"]
        pcm = array("h", (round(max(-1, min(1, float(x))) * 32767) for x in samples))
        with wave.open(str(target), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(int(cfg.audio.output_sample_rate))
            f.writeframes(pcm.tobytes())
        return True

    def synthesize(self, text, mood="calm"):
        with self.lock:
            if isinstance(mood, tuple):
                mood = mood[0]
            key = repr((text, mood, self.cfg["tts_voice"], self.cfg["tts_backend"]))
            path = self.root / (hashlib.sha1(key.encode()).hexdigest() + ".wav")
            tmp = path.with_suffix(".tmp.wav")
            if path.exists():
                path.touch()
                return path
            model = Path(
                self.cfg.get("piper_model_path")
                or self.root.parent / "voices" / (self.cfg["tts_voice"] + ".onnx")
            )
            exe = shutil.which("piper")
            speed = 0.9 if mood == "joy" else 1.14 if mood == "sadness" else 1
            if self.cfg["tts_backend"] == "piper" and exe and model.is_file():
                cmd = [
                    exe,
                    "--model",
                    str(model),
                    "--output_file",
                    str(tmp),
                    "--length_scale",
                    str(speed),
                    "--noise_scale",
                    "0.72" if mood == "joy" else "0.58",
                ]
            elif self.cfg.get("tts_model_path") and self.fallback:
                cmd = None
            elif exe := shutil.which("espeak-ng") or shutil.which("espeak"):
                cmd = [
                    exe,
                    "-v",
                    "ru",
                    "-p",
                    "56" if mood == "joy" else "46",
                    "-s",
                    str(round(165 / speed)),
                    "-w",
                    str(tmp),
                    "--stdin",
                ]
            else:
                cmd = None
            try:
                if self.cfg["tts_backend"] == "xtts" and self._xtts(text, tmp, speed):
                    pass
                elif cmd:
                    subprocess.run(cmd, input=text.encode(), timeout=90, check=True)
                elif self.fallback:
                    self.fallback(text, tmp)
                else:
                    raise RuntimeError("Нет локального голоса")
                tmp.replace(path)
            finally:
                tmp.unlink(missing_ok=True)
            files = sorted(self.root.glob("*.wav"), key=lambda p: p.stat().st_mtime)
            size = sum(p.stat().st_size for p in files)
            for f in files:
                if size <= self.cfg["tts_cache_max_mb"] * 1024**2:
                    break
                if f != path:
                    size -= f.stat().st_size
                    f.unlink()
            return path

    def speak(self, text, mood="calm"):
        self.stop()
        ticket = self.ticket

        def work():
            p = self.synthesize(text, mood)
            if ticket == self.ticket:
                self.player.play(p)

        threading.Thread(target=work, daemon=True).start()

    def is_speaking(self):
        return self.player.busy()

    def stop(self):
        self.ticket += 1
        self.player.stop()
