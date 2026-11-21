"""Затухание и композиция эмоций."""

from scp_diagnostics import measured

import math
import time
from collections import deque
from functools import wraps
from threading import RLock

from scp_emotion_taxonomy import EMOTION_DELTAS, TAXONOMY
from scp_storage import read, save

__all__ = ["EmotionEngine", "EMOTION_DELTAS"]
PAIRS = dict(
    bittersweet=("joy", "sadness"),
    jealousy_composite=("attachment", "insecurity"),
    wounded_pride_composite=("shame", "anger"),
    wounded_pride=("shame", "anger"),
    guilty_pleasure=("joy", "guilt"),
    nervous_excitement=("fear", "joy"),
    homesickness=("longing", "nostalgia"),
    tough_love=("affection", "frustration"),
)


EMOTION_DELTAS.update(
    {
        "return_0": dict(joy=0.10, missing_you=-0.15, tenderness=0.05),
        "return_1": dict(
            joy=0.15, bittersweet=0.10, resentment=-0.05, missing_you=-0.20
        ),
        "return_2": dict(
            joy=0.18, bittersweet=0.20, resentment=-0.10, missing_you=-0.25
        ),
        "return_3": EMOTION_DELTAS["user_returned"],
        "time_of_day_night": dict(calm=0.05, tenderness=0.03),
        "time_of_day_morning": dict(hope=0.04, curiosity=0.03),
    }
)


def synchronized(fn):
    @wraps(fn)
    def call(self, *a, **kw):
        with self.lock:
            return fn(self, *a, **kw)

    return call


class EmotionEngine:
    def __init__(self, root, bus=None):
        self.lock = RLock()
        self.path = root / "emotions_v2.json"
        state = read(self.path, {})
        self.baselines = {k: v.baseline for k, v in TAXONOMY.items()}
        self.values = self.baselines | {
            k: min(1, max(0, float(v)))
            for k, v in state.get("values", {}).items()
            if k in TAXONOMY and isinstance(v, (float, int))
        }
        self.boost = state.get("boost", {})
        self.last_cool = state.get("last_cool", time.time())
        self.history = deque(maxlen=500)
        self.cool()
        if bus:
            bus.subscribe("*", self.apply_event)

    def compose(self):
        for k, (a, b) in PAIRS.items():
            self.values[k] = min(
                1, math.sqrt(self.values[a] * self.values[b]) + self.boost.get(k, 0)
            )

    @synchronized
    def persist(self):
        self.compose()
        save(
            self.path,
            dict(values=self.values, boost=self.boost, last_cool=self.last_cool),
        )

    @synchronized
    @measured('emotion_engine')
    def cool(self, elapsed=None):
        now = time.time()
        h = max(0, elapsed if elapsed is not None else now - self.last_cool) / 3600
        for k, e in TAXONOMY.items():
            f = math.exp(-h * e.decay_per_hour)
            self.values[k] = e.baseline + (self.values[k] - e.baseline) * f
            if k in self.boost:
                self.boost[k] *= f
        self.last_cool = now
        self.persist()

    @synchronized
    @measured('emotion_engine')
    def apply_event(self, event_type, payload=None, **kwargs):
        p = (payload or {}) | kwargs
        if event_type == "user_returned":
            event_type = "return_" + str(min(3, max(0, int(p.get("after_days", 0)))))
        if event_type == "legacy_update":
            for k in self.values:
                if k in p["trigger"]:
                    self.values[k] = min(1, max(0, self.values[k] + p["delta"]))
        if event_type == "absence_threshold_crossed":
            event_type = f"absence_{p['hours']}"
        for k, v in EMOTION_DELTAS.get(event_type, {}).items():
            target = self.boost if k in PAIRS else self.values
            target[k] = min(1, max(0, target.get(k, 0) + v))
        self.history.append((time.time(), event_type))
        self.persist()

    @synchronized
    def describe_short(self):
        return max(self.values.items(), key=lambda p: p[1])

    @synchronized
    def describe_for_prompt(self):
        top = sorted(self.values, key=self.values.get, reverse=True)[:4]
        return "Сейчас ты чувствуешь: " + ", ".join(
            f"{k} {self.values[k]:.2f} ({TAXONOMY[k].prompt_phrase})" for k in top
        )

    def apply_to_prompt(self, prompt):
        from scp_safety import GUIDANCE

        return "\n".join([prompt, self.describe_for_prompt(), GUIDANCE])
