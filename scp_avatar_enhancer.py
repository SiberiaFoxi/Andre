"""Non-destructive animation for a rigged v5.3 companion canvas."""

from scp_diagnostics import measured

import math
import random
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGraphicsEffect

from AI_2D_Avatar_Studio_v5_3_integrated import CompanionAvatarWindow

__all__ = ["AvatarAnimator", "EnhancedAvatarWindow", "EMOTION_TO_EXPRESSION"]
EMOTION_TO_EXPRESSION = dict(
    joy="smile",
    sadness="sad",
    resentment="annoyed",
    bittersweet="sad_smile",
    tenderness="soft_smile",
    surprise="surprised",
)


class HeadTilt(QGraphicsEffect):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.angle = 0.0
        self.setEnabled(False)

    def draw(self, painter):
        pivot = self.canvas.rect().center()
        painter.save()
        painter.translate(pivot)
        painter.rotate(self.angle)
        painter.translate(-pivot)
        self.drawSource(painter)
        painter.restore()


class AvatarAnimator(QTimer):
    def __init__(self, w, engine, tts):
        super().__init__(w)
        self.w = w
        self.engine = engine
        self.tts = tts
        self.weight = 0.0
        self.micro = time.monotonic() + random.uniform(30, 90)
        self.tilt_until = 0
        self.canvas = w.get_canvas()
        self.tilt = HeadTilt(self.canvas)
        self.canvas.setGraphicsEffect(self.tilt)
        self.last_phase = "idle"
        self.rest = 0.0
        self.origin = self.canvas.get_display_rect
        self.canvas.get_display_rect = self.rect
        self.timeout.connect(self.frame)
        self.start(40)

    def rect(self):
        r = self.origin()
        t = time.monotonic()
        r.translate(
            math.sin(t * 0.65) * 1.4 + (1 if t < self.tilt_until else 0),
            math.sin(t * 1.8) * 1.2,
        )
        return r

    @measured('avatar_enhancer')
    def address(self, question=False):
        self.w._next_blink_ms = 0
        self.tilt_until = time.monotonic() + (0.7 if question else 0)

    def frame(self):
        name, target = self.engine.describe_short() if self.engine else ("calm", 0.2)
        self.weight += (target - self.weight) * 0.15
        self.w.set_emotion(name, self.weight)
        now = time.monotonic()
        if now > self.micro + 1:
            self.micro = now + random.uniform(30, 90)
        phase = self.w._blink_phase
        if phase == "idle" and self.last_phase != "idle":
            self.w._next_blink_ms = random.randint(3000, 7000)
        self.last_phase = phase
        target_angle = 3 if now < self.tilt_until else 0
        self.tilt.angle += (target_angle - self.tilt.angle) * 0.18
        self.tilt.setEnabled(abs(self.tilt.angle) > 0.05)
        shape = EMOTION_TO_EXPRESSION.get(name, "neutral")
        target_mouth = {
            "smile": 0.16,
            "sad_smile": 0.09,
            "soft_smile": 0.1,
            "surprised": 0.42,
        }.get(shape, 0) * self.weight
        self.rest += (target_mouth - self.rest) * 0.18
        self.canvas.talk = (
            self.tts.player.rms()
            if self.tts and self.tts.is_speaking()
            else self.rest + (0.08 if self.micro <= now else 0.0)
        )
        if phase == "idle":
            self.canvas.blink = {"sad": 0.22, "annoyed": 0.29, "sad_smile": 0.16}.get(
                shape, 0
            ) * self.weight
        self.canvas.update()


class EnhancedAvatarWindow(CompanionAvatarWindow):
    def __init__(self, emotions=None, tts=None):
        super().__init__()
        self.animator = AvatarAnimator(self, emotions, tts)
