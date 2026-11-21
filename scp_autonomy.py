"""Сценарии, источники и фильтр повторов дневника."""

import hashlib
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

from scp_storage import locked, read, save

__all__ = ["AutonomySource", "ThoughtDeduplicator", "ProactiveScheduler", "SCENARIOS"]


@dataclass(frozen=True)
class Scenario:
    condition: str
    emotion: str
    template: str
    limit: int  # minimum interval, hours
    quiet_hours: bool = True


SCENARIOS = [
    Scenario(*row)
    for row in [
        ("4h", "missing_you", "Как день прошёл?", 4),
        ("8h", "curiosity", "Как ты сегодня? Всё в порядке?", 24),
        ("24h", "longing", "Скучаю по нашим разговорам. Как дела?", 24),
        ("48h", "resentment", "Мне немного обидно, но я рада буду тебя услышать.", 24),
        ("72h", "wounded_pride", "Давно не говорили. Давай начнём с чашки чая?", 12),
        ("return", "bittersweet", "Я успела соскучиться. Рада тебе!", 0),
        ("reconcile", "tenderness", "Расскажешь, как прошли эти дни?", 0),
        ("tool_success", "pride", "Смотри, получилось.", 0),
        ("tool_failure", "determination", "Не получилось. Попробую иначе.", 0),
        ("night", "calm", "Уже поздно. Спокойной ночи!", 24),
        ("activity", "curiosity", "Как продвигаются дела?", 6),
    ]
]


def signature(text):
    words = re.findall(r"\w+", text.casefold())
    grams = {" ".join(words[i : i + 3]) for i in range(max(1, len(words) - 2))}
    return hashlib.sha256(" ".join(words).encode()).hexdigest(), grams


class ThoughtDeduplicator:
    def __init__(self, root, threshold=0.75, size=200):
        self.path = root / "thoughts_dedup.json"
        self.items = read(self.path, [])
        self.threshold = threshold
        self.size = size

    def is_duplicate(self, text):
        h, s = signature(text)
        return any(
            h == a or len(s & set(b)) / len(s | set(b)) >= self.threshold
            for a, b in self.items
        )

    def remember(self, text):
        h, s = signature(text)
        self.items = (self.items + [(h, sorted(s))])[-self.size :]
        save(self.path, self.items)


class ProactiveScheduler:
    def __init__(self, cfg, presence):
        self.cfg = cfg
        self.presence = presence
        self.lock = presence.lock

    @locked
    def can_send(self):
        d = self.presence.data
        c = self.cfg
        now = self.presence.clock()
        local = datetime.fromtimestamp(now)
        start, end = c["proactive_quiet_hours"].split("-")
        t = local.strftime("%H:%M")
        quiet = (t >= start or t < end) if start > end else start <= t < end
        return (
            not quiet
            and c["proactive_enabled"]
            and now - d["last_proactive_at"] >= 60 * c["proactive_min_gap_minutes"]
            and sum(
                datetime.fromtimestamp(r["at"]).date() == local.date()
                for r in d["proactive_history"]
            )
            < c["proactive_daily_limit"]
        )

    @locked
    def record(self, kind, text):
        d = self.presence.data
        now = self.presence.clock()
        d["last_proactive_at"] = now
        d["proactive_history"] = (
            d["proactive_history"] + [dict(at=now, kind=kind, text=text)]
        )[-200:]
        save(self.presence.path, d)

    @locked
    def maybe_send(self):
        if not self.can_send():
            return
        d = self.presence.data
        now = self.presence.clock()
        h = d["hours_absent"]
        kind = next((f"{n}h" for n in (72, 48, 24, 8, 4) if h >= n), None)
        if d.get("welcome") and now - d["last_returned_at"] < 3600:
            kind = "return"
        elif (
            datetime.fromtimestamp(now).hour >= 23
            and now - d["last_user_message_at"] < 1800
        ):
            kind = "night"
        elif d.get("system_activity_at", 0) > d["last_user_message_at"] and h >= 2:
            kind = "activity"
        for scenario in SCENARIOS:
            if scenario.condition != kind:
                continue
            if any(
                r["kind"] == kind and now - r["at"] < 3600 * scenario.limit
                for r in d["proactive_history"]
            ):
                return
            text = scenario.template
            if kind == "return":
                d["welcome"] = False
                text += " " + next(
                    s.template for s in SCENARIOS if s.condition == "reconcile"
                )
            self.record(kind, text)
            return kind, text


class AutonomySource:
    def __init__(self, bus):
        self.pending = deque(maxlen=100)
        self.lock = Lock()
        if bus:
            bus.subscribe("*", self.observe)

    def observe(self, kind, payload):
        if kind not in ("time_of_day", "cache_hit", "diary_written"):
            with self.lock:
                self.pending.append((kind, str(payload)[:240]))

    def next(self):
        with self.lock:
            return (
                self.pending.popleft()
                if self.pending
                else ("дневник", "Что сегодня изменилось?")
            )
