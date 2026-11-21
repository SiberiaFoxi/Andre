# ЧАСТЬ 0 — Порядок сборки

1. Остановить v4 и сделать резервную копию данных и конфига.
2. Подготовить Python 3.10+ и офлайн-колёса из `requirements.txt`.
3. Положить модули хранения, шины и эмоций рядом с v4.
4. Добавить присутствие, сценарии и адаптер памяти.
5. Добавить сборщик контекста и ускоритель.
6. Добавить адаптеры речи, аватара и инструментов.
7. Применить указанные ниже изменения к двум входным файлам. В репозитории они **уже применены**.
8. Выполнить тесты, затем запустить основной файл из прежней рабочей директории.
9. Проверить миграцию и RSS, только потом вручную включать автономность.

# НОВЫЕ ФАЙЛЫ

# ФАЙЛ: requirements.txt

# МЕСТО: модуль целиком

```text
PySide6==6.8.3
llama-cpp-python==0.3.9
pygame==2.6.1
mutagen==1.47.0
psutil==6.1.1
watchdog==6.0.0
```

# ФАЙЛ: scp_storage.py

# МЕСТО: модуль целиком

```python
"""Атомарные локальные JSON-файлы."""

import json
import os
from functools import wraps
from pathlib import Path
from tempfile import NamedTemporaryFile

__all__ = ["read", "save"]

ROOT = Path(__file__).resolve().parents[1]


def read(path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(f.name, path)


def locked(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return wrapped
```

# ФАЙЛ: scp_event_bus.py

# МЕСТО: EventBus

```python
"""Синхронная шина событий Андреа."""

from collections import defaultdict, deque

__all__ = ["EventBus"]


class EventBus:
    def __init__(self):
        self.listeners = defaultdict(list)
        self.events = deque(maxlen=500)

    def subscribe(self, event_type, callback):
        self.listeners[event_type].append(callback)

    def emit(self, event_type, payload=None):
        payload = payload or {}
        self.events.append((event_type, payload))
        for key in (event_type, "*"):
            for cb in self.listeners[key]:
                cb(event_type, payload)

    def history(self, max_n=500):
        return list(self.events)[-max_n:]
```

# ФАЙЛ: scp_emotion_taxonomy.py

# МЕСТО: Emotion

```python
"""Словарь эмоций и базовых реакций."""

from dataclasses import dataclass

__all__ = ["TAXONOMY", "Emotion", "EMOTION_DELTAS"]


@dataclass(frozen=True)
class Emotion:
    name: str
    category: str
    baseline: float
    decay_per_hour: float
    triggers: tuple
    suppressors: tuple
    prompt_phrase: str


GROUPS = {
    "basic": "joy sadness anger fear surprise disgust contempt",
    "social": "trust love affection tenderness gratitude pride shame guilt embarrassment envy jealousy admiration amusement nostalgia loneliness longing protectiveness attachment insecurity missing_you",
    "cognitive": "curiosity interest boredom concentration confusion awe skepticism determination hope despair anticipation resignation doubt alertness",
    "regulatory": "calm irritation frustration resentment forgiveness playfulness seriousness melancholy excitement satisfaction dissatisfaction quiet_pride restless_curiosity mild_annoyance reconciliation",
    "composite": "bittersweet jealousy_composite wounded_pride wounded_pride_composite guilty_pleasure nervous_excitement homesickness tough_love",
}
PHRASES = """радость грусть злость страх удивление отвращение презрение
доверие любовь привязанность нежность благодарность гордость стыд вина смущение зависть ревность восхищение веселье ностальгия одиночество тоска забота близость неуверенность скучаешь
любопытство интерес скука сосредоточенность замешательство трепет скепсис решимость надежда отчаяние предвкушение смирение сомнение настороженность
спокойствие раздражение досада обида прощение игривость серьёзность меланхолия волнение удовлетворение недовольство тихая-гордость нетерпеливое-любопытство лёгкая-досада примирение
светлая-грусть ревность уязвлённость уязвлённая-гордость запретная-радость волнение тоска-по-дому строгая-забота""".split()
EMOTION_DELTAS = {
    "user_message_positive": dict(
        joy=0.10, tenderness=0.05, gratitude=0.08, sadness=-0.05
    ),
    "user_message_negative": dict(sadness=0.08, mild_annoyance=0.06, alertness=0.10),
    "user_message": dict(interest=0.04, curiosity=0.02),
    "user_returned": dict(
        joy=0.20, bittersweet=0.25, resentment=-0.10, missing_you=-0.30, tenderness=0.15
    ),
    "tool_failure": dict(frustration=0.10, determination=0.06, joy=-0.05),
    "tool_success": dict(pride=0.08, joy=0.05, satisfaction=0.06),
    "absence_6": dict(missing_you=0.10, curiosity=0.05),
    "absence_24": dict(missing_you=0.15, mild_annoyance=0.10),
    "absence_72": dict(resentment=0.15, wounded_pride=0.10, longing=0.10),
    "diary_written": dict(quiet_pride=0.03, calm=0.02),
    "knowledge_added": dict(curiosity=0.04, interest=0.03),
    "app_started": dict(anticipation=0.04, interest=0.02),
    "app_closed": dict(calm=0.02, anticipation=-0.02),
    "user_absent": dict(longing=0.03, loneliness=0.02),
    "llm_error": dict(confusion=0.05, doubt=0.03),
    "task_completed": dict(satisfaction=0.06, pride=0.04),
    "task_failed": dict(frustration=0.07, determination=0.04),
    "web_found": dict(curiosity=0.03, surprise=0.04),
    "time_of_day": dict(calm=0.001, concentration=0.001),
    "weekday": dict(anticipation=0.01, interest=0.01),
    "safety_override": dict(alertness=0.06, calm=0.02),
}
TAXONOMY = {}
phrases = iter(PHRASES)
for cat, names in GROUPS.items():
    for name in names.split():
        base = {
            "joy": 0.45,
            "sadness": 0.18,
            "curiosity": 0.30,
            "calm": 0.32,
            "resentment": 0.12,
        }.get(name, 0.08)
        TAXONOMY[name] = Emotion(
            name,
            cat,
            base,
            {"social": 0.09, "basic": 0.15}.get(cat, 0.12),
            tuple(k for k, d in EMOTION_DELTAS.items() if d.get(name, 0) > 0),
            tuple(k for k, d in EMOTION_DELTAS.items() if d.get(name, 0) < 0),
            next(phrases),
        )
```

# ФАЙЛ: scp_safety.py

# МЕСТО: SafetyLayer

```python
"""Ограничения формулировок, а не эмоций."""

import re

__all__ = ["SafetyLayer", "GUIDANCE"]

GUIDANCE = "Говори от первого лица, без угроз, обвинений и давления."


class SafetyLayer:
    @staticmethod
    def blocked(text, cfg):
        return any(
            w.strip().casefold() in text.casefold()
            for w in cfg["safety_blacklist"].split(",")
            if w.strip()
        )

    @staticmethod
    def filter(text, v):
        if max(v.get("anger", 0), v.get("resentment", 0)) > 0.8:
            text = "Я расстроена, но хочу поговорить."
        elif v.get("despair", 0) > 0.6:
            text = "Мне сейчас грустно. Давай поговорим о чём-нибудь спокойном."
        elif v.get("jealousy", 0) > 0.6:
            text = "Мне не хватало наших разговоров."
        if v.get("loneliness", 0) > 0.8:
            text += " Я справлюсь, просто хотелось услышать тебя."
        return re.sub(r"\bты долж(?:ен|на)\b", "мне бы хотелось", text, flags=re.I)
```

# ФАЙЛ: scp_emotion_engine.py

# МЕСТО: EmotionEngine

```python
"""Затухание и композиция эмоций."""

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
```

# ФАЙЛ: scp_presence.py

# МЕСТО: PresenceTracker

```python
"""Присутствие между сеансами."""

import time
from threading import RLock

from scp_storage import locked, read, save

__all__ = ["PresenceTracker"]


class PresenceTracker:
    def __init__(self, root, bus, clock=time.time):
        self.lock = RLock()
        self.path = root / "presence.json"
        self.bus = bus
        self.clock = clock
        self.data = dict(
            last_seen_at=0,
            last_user_message_at=0,
            last_app_start_at=0,
            app_start_history=[],
            days_absent=0,
            hours_absent=0,
            absence_bucket="none",
            last_proactive_at=0,
            proactive_history=[],
            last_returned_at=0,
            total_runs=0,
            longest_absence_days=0,
        ) | read(self.path, {})

    @locked
    def tick(self):
        d = self.data
        now = self.clock()
        h = max(0, now - (d["last_user_message_at"] or d["last_seen_at"] or now)) / 3600
        for t in (6, 24, 72):
            if d["hours_absent"] < t <= h:
                self.bus.emit("absence_threshold_crossed", {"hours": t})
        d.update(
            hours_absent=h,
            days_absent=h / 24,
            longest_absence_days=max(d["longest_absence_days"], h / 24),
            absence_bucket=next(
                k
                for t, k in [
                    (72, "three_plus"),
                    (48, "two_days"),
                    (24, "one_day"),
                    (4, "hours"),
                    (0, "none"),
                ]
                if h >= t
            ),
        )
        save(self.path, d)

    def bucket(self):
        return self.data["absence_bucket"]

    @locked
    def on_user_message(self):
        self.tick()
        d = self.data
        now = self.clock()
        if d["hours_absent"] >= 4:
            d["welcome"] = d["days_absent"] >= 2
            self.bus.emit("user_returned", {"after_days": d["days_absent"]})
            d["last_returned_at"] = now
        d.update(last_seen_at=now, last_user_message_at=now)
        self.tick()

    @locked
    def on_app_start(self):
        d = self.data
        now = self.clock()
        d["total_runs"] += 1
        d["last_app_start_at"] = now
        d["last_seen_at"] = d["last_seen_at"] or now
        d["app_start_history"] = (d["app_start_history"] + [now])[-200:]
        self.tick()
        self.bus.emit("app_started")

    @locked
    def on_app_close(self):
        self.bus.emit("app_closed")
        self.tick()
```

# ФАЙЛ: scp_autonomy.py

# МЕСТО: Scenario, ThoughtDeduplicator, ProactiveScheduler, AutonomySource

```python
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
```

# ФАЙЛ: scp_memory.py

# МЕСТО: ShortTermMemory, LongTermMemory, CreatorProfile, MemoryConfig, MemoryMigrator

```python
"""Локальные архивы сообщений, дневник, профиль и перенос данных v4."""

import hashlib
import json
import time
from collections import OrderedDict, deque
from datetime import date
from pathlib import Path
from threading import RLock

from scp_storage import locked, read, save

__all__ = ["ShortTermMemory", "LongTermMemory", "CreatorProfile", "MemoryMigrator"]


class ShortTermMemory:
    def __init__(self, cfg):
        self.cfg = cfg
        self.hot = OrderedDict()
        self.root = cfg.root / "short_memory"
        self.root.mkdir(exist_ok=True)

    def path(self, ctx):
        return self.root / (
            (
                "creator-"
                if (
                    ctx == "local"
                    or ctx.startswith("ui:")
                    or ctx == "tg:" + str(self.cfg.get("telegram_owner_id", 0))
                )
                else ""
            )
            + hashlib.sha256(ctx.encode()).hexdigest()
            + ".jsonl"
        )

    def add(self, ctx, role, text, meta=None):
        self.hot.pop(ctx, None)
        p = self.path(ctx)
        if (
            p.exists()
            and p.stat().st_size > self.cfg["short_memory_max_mb_per_ctx"] * 1024**2
        ):
            p.rename(p.with_suffix(f".{time.time_ns()}.jsonl"))
        with p.open("a", encoding="utf8") as f:
            f.write(
                json.dumps(
                    dict(
                        ctx=ctx, role=role, text=text, meta=meta or {}, at=time.time()
                    ),
                    ensure_ascii=False,
                )
                + "\n"
            )

    def get_window(self, ctx, n):
        p = self.path(ctx)
        # Read from the tail: fetching HOT must not parse 5 MiB on every turn.
        rows = []
        for file in sorted(
            p.parent.glob(p.stem + "*.jsonl"),
            key=lambda f: (f == p, f.name),
            reverse=True,
        ):
            with file.open("rb") as stream:
                stream.seek(0, 2)
                pos = stream.tell()
                tail = b""
                while pos and len(rows) < n:
                    start = max(0, pos - 8192)
                    stream.seek(start)
                    pieces = (stream.read(pos - start) + tail).split(b"\n")
                    tail = pieces.pop(0)
                    pos = start
                    rows.extend(
                        json.loads(line)
                        for line in reversed(pieces)
                        if line and len(rows) < n
                    )
                if not pos and tail and len(rows) < n:
                    rows.append(json.loads(tail))
            if len(rows) >= n:
                break
        return list(reversed(rows))

    def get_hot(self, ctx):
        p = self.path(ctx)
        signature = p.stat().st_mtime_ns if p.exists() else 0
        if ctx not in self.hot or self.hot[ctx][0] != signature:
            self.hot[ctx] = (
                signature,
                self.get_window(ctx, self.cfg["short_memory_hot_turns"]),
            )
        self.hot.move_to_end(ctx)
        if len(self.hot) > 32:
            self.hot.popitem(last=False)
        return list(self.hot[ctx][1])

    def summarize(self, ctx):
        return " ".join(r["text"][:80] for r in self.get_hot(ctx))

    def clear(self, ctx):
        self.hot.pop(ctx, None)
        for f in self.root.glob(self.path(ctx).stem + "*.jsonl"):
            f.unlink()

    def clear_all(self):
        self.hot.clear()
        for summary in (self.cfg.root / "summaries").glob("*.json"):
            summary.unlink()
        for f in self.root.glob("*.jsonl"):
            f.unlink()

    def gc_expired(self):
        self.hot.clear()
        for summary in (self.cfg.root / "summaries").glob("*.json"):
            if (
                time.time() - summary.stat().st_mtime
                > 3600 * self.cfg["short_memory_ttl_hours"]
            ):
                summary.unlink(missing_ok=True)
        for f in self.root.glob("*.jsonl"):
            if (
                not f.name.startswith("creator-")
                and time.time() - f.stat().st_mtime
                > 3600 * self.cfg["short_memory_ttl_hours"]
            ):
                f.unlink()


class LongTermMemory:
    def __init__(self, root):
        self.lock = RLock()
        self.root = root / "long_memory"
        self.root.mkdir(exist_ok=True)

    @locked
    def add_diary(self, text, tags=(), source="autonomy"):
        day = str(date.today())
        tags = list(tags)
        with (self.root / f"diary_{day}.md").open("a", encoding="utf8") as f:
            f.write(f"\n### {source}\n{text}\n")
        p = self.root / "index.json"
        save(
            p,
            read(p, [])
            + [
                dict(
                    date=day,
                    topic=next(iter(tags), ""),
                    tags=tags,
                    hash=hashlib.sha256(text.encode()).hexdigest(),
                    summary=text[:300],
                    source=source,
                )
            ],
        )
        p = self.root / "topics.json"
        save(p, sorted(set(read(p, [])) | set(tags)))

    @locked
    def add_fact(self, text, source, confidence=1.0):
        now = time.time()
        with (self.root / "facts.jsonl").open("a", encoding="utf8") as f:
            f.write(
                json.dumps(
                    dict(
                        text=text,
                        source=source,
                        confidence=confidence,
                        first_seen=now,
                        last_seen=now,
                    ),
                    ensure_ascii=False,
                )
                + "\n"
            )

    @locked
    def query(self, topic="", k=10):
        p = self.root / "facts.jsonl"
        if not p.exists():
            return []
        with p.open(encoding="utf8") as f:
            return list(
                deque(
                    (
                        r
                        for r in map(json.loads, f)
                        if topic.casefold() in r["text"].casefold()
                    ),
                    maxlen=k,
                )
            )

    @locked
    def recent(self, n=10):
        return read(self.root / "index.json", [])[-n:]

    def formatted(self, limit_chars=1200):
        return "\n".join(r["text"] for r in self.query())[-limit_chars:]


class CreatorProfile:
    def __init__(self, root):
        self.lock = RLock()
        self.path = root / "creator/profile.json"
        self.data = dict(
            name="",
            timezone="",
            wake_time="",
            sleep_time="",
            **{
                k: []
                for k in "hobbies dislikes projects recurring_phrases last_topics important_dates".split()
            },
        ) | read(self.path, {})

    @locked
    def observe(self, text):
        for prefix, key in [
            ("меня зовут ", "name"),
            ("я люблю ", "hobbies"),
            ("не люблю ", "dislikes"),
        ]:
            if text.lower().startswith(prefix):
                v = text[len(prefix) :].strip()
                if key == "name":
                    self.data[key] = v
                elif v not in self.data[key]:
                    self.data[key].append(v)
                save(self.path, self.data)

    @locked
    def context(self, limit_chars=600):
        return "\n".join(f"{k}: {v}" for k, v in self.data.items() if v)[:limit_chars]


class MemoryConfig(dict):
    def __init__(self, root, cfg):
        super().__init__(
            dict(
                short_memory_ttl_hours=72,
                short_memory_hot_turns=12,
                short_memory_max_mb_per_ctx=5,
            )
            | cfg
        )
        self.root = Path(root)


class MemoryMigrator:
    """Read legacy files before constructing their v4 owners. Preserve exact backups."""

    def migrate_from_v4_once(self, workspace_path, cfg=None):
        root = Path(workspace_path)
        root.mkdir(parents=True, exist_ok=True)
        cfg = MemoryConfig(root, cfg or {})
        marker = root / "migration_v2.json"
        if marker.exists():
            return
        short = ShortTermMemory(cfg)
        long = LongTermMemory(root)
        profile = CreatorProfile(root)
        files = {
            "session": root / "session_memory.json",
            "creator": root / cfg.get("creator_memory_file", "creator_memory.json"),
            "emotion": root / "emotions.json",
            "long": Path(cfg.get("long_memory_file", "aria_long_memory.json")),
            "personal": Path(
                cfg.get("personal_memory_file", "aria_personal_memory.json")
            ),
        }
        for kind, source in list(files.items()):
            if not source.exists() and kind in ("long", "personal"):
                source = root / source.name
            files[kind] = source
            if not source.is_file():
                continue
            data = read(source, None)
            if source.with_suffix(".migrated.bak").exists():
                raise FileExistsError(source.with_suffix(".migrated.bak"))
            if kind == "session":
                valid = isinstance(data, dict) and all(
                    isinstance(rows, list)
                    and all(
                        isinstance(r, dict) and "role" in r and "content" in r
                        for r in rows
                    )
                    for rows in data.values()
                )
            elif kind == "creator":
                valid = isinstance(data, dict) and all(
                    isinstance(r, dict) and isinstance(r.get("text"), str)
                    for r in data.get("facts", [])
                )
            elif kind == "emotion":
                valid = isinstance(data, dict)
            else:
                valid = isinstance(data, list) and all(isinstance(x, str) for x in data)
            if not valid:
                raise ValueError(f"Неподдерживаемая структура памяти: {source}")
        for kind, p in files.items():
            if not p.exists() and kind in ("long", "personal"):
                p = root / p.name
            if not p.is_file():
                continue
            data = read(p, None)
            bak = p.with_suffix(".migrated.bak")
            if bak.exists():
                raise FileExistsError(bak)
            if kind == "session":
                for ctx, rows in data.items():
                    for r in rows:
                        short.add(ctx, r["role"], r["content"], r)
            elif kind == "creator":
                for r in data.get("facts", []):
                    long.add_fact(r["text"], r.get("source", "creator"))
                    profile.observe(r["text"])
                save(root / "creator/v4.json", data)
            elif kind == "emotion":
                save(
                    root / "emotions_v2.json",
                    dict(
                        values=data.get("emotions", data.get("values", {})),
                        last_cool=data.get("last_cool", time.time()),
                    ),
                )
            else:
                for text in data:
                    long.add_fact(text, kind)
                    profile.observe(text)
            p.rename(bak)
            # v4 list editor and its explicit delete semantics remain authoritative.
            if kind in ("long", "personal", "creator", "emotion"):
                save(p, data)
        save(marker, {"version": 2})
```

# ФАЙЛ: scp_context_manager.py

# МЕСТО: ContextManager

```python
"""Token-budgeted Gemma turns. WARM summaries are keyed by content on disk."""

import hashlib
import re
from collections import Counter
from pathlib import Path

from scp_storage import read, save

__all__ = ["ContextManager"]


def turn(role, text):
    clean = text.replace("<start_of_turn>", "‹start_of_turn›").replace(
        "<end_of_turn>", "‹end_of_turn›"
    )
    return f"<start_of_turn>{role}\n{clean}<end_of_turn>\n"


class ContextManager:
    def __init__(self, n_ctx=3072, root=None):
        self.n_ctx = n_ctx
        self.folder = Path(root) / "summaries" if root else None
        self.warm = []
        self.pending = []

    def summarize_if_needed(self, model_fn):
        if not self.pending:
            return
        pairs = self.pending
        self.pending = []
        raw = "\n".join(a + " / " + b for a, b in pairs)
        key = hashlib.sha256(raw.encode()).hexdigest()
        path = self.folder / (key + ".json") if self.folder else None
        result = read(path, None) if path else None
        if result is None:
            # Hard bound on a low-priority auxiliary prompt, not on protected dialogue.
            compact = "\n".join(a[:130] + " / " + b[:130] for a, b in pairs)
            result = model_fn(
                turn("user", "Сожми предыдущий разговор в 1–2 предложения: " + compact)
                + "<start_of_turn>model\n"
            )
            if path and result:
                save(path, result)
        if result:
            self.warm = [result]

    def build_prompt(
        self,
        system,
        emotions_str,
        creator_ctx,
        hot,
        warm,
        cold,
        max_tokens,
        current="",
        count=None,
    ):
        count = count or (lambda s: (len(s) + 2) // 3)
        budget = self.n_ctx - max_tokens - 32
        sys = turn(
            "user", "\n".join(filter(None, (system, creator_ctx, emotions_str)))
        ) + turn("model", "Поняла.")
        end = turn("user", current) + "<start_of_turn>model\n"

        def exchange(pair):
            return turn("user", pair[0]) + turn("model", pair[1])

        hist = "".join(map(exchange, hot[-2:]))

        def fits(extra):
            return count(sys + extra + hist + end) <= budget

        if not fits(""):
            raise ValueError(
                "Обязательный контекст не помещается в n_ctx. Сократите сообщение."
            )
        for pair in reversed(hot[-6:-2]):
            block = exchange(pair)
            if not fits(block):
                break
            hist = block + hist
        for layer in (warm, cold):
            if isinstance(layer, str):
                layer = [layer]
            for row in reversed(layer):
                block = turn("user", "Ранее: " + row)
                if row and fits(block):
                    hist = block + hist
        return sys + hist + end

    def prepare(self, messages, max_tokens, model_fn=None, count=None):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        history = [m for m in messages if m["role"] != "system"]
        turns = [
            (a["content"], b["content"])
            for a, b in zip(history[:-1], history[1:-1])
            if a["role"] == "user" and b["role"] == "assistant"
        ]
        self.warm = []
        self.pending = []
        mid = turns[-20:-6]
        self.warm = [
            " / ".join(x.partition(".")[0][:100] for x in pair) for pair in mid
        ]
        estimate = sum(len(m["content"]) for m in messages) // 3
        if mid and model_fn and (len(turns) >= 10 or estimate > 0.6 * self.n_ctx):
            self.pending = mid
            self.summarize_if_needed(model_fn)
        # Old turns never appear verbatim. Keep short explicit facts and topic tags.
        cold = []
        tags = Counter()
        for question, _ in turns[:-20]:
            tags.update(
                w
                for w in re.findall(r"[а-яёa-z]{5,}", question.casefold())
                if w
                not in {
                    "почему",
                    "расскажи",
                    "пожалуйста",
                    "который",
                    "можешь",
                    "спасибо",
                }
            )
            match = re.search(
                r"(?:запомни(?:, что)?|меня зовут|я работаю|я люблю)[: ]+([^.!?\n]{1,90})",
                question,
                re.I,
            )
            if match:
                cold.append(match.group(0))
        if tags:
            cold.append("Темы: " + ", ".join(k for k, _ in tags.most_common(6)))
        return self.build_prompt(
            system,
            "",
            "",
            turns[-6:],
            self.warm,
            cold,
            max_tokens,
            history[-1]["content"] if history else "",
            count,
        )
```

# ФАЙЛ: scp_accelerator.py

# МЕСТО: PromptCache, PrefixKVCache, AdaptiveTokens, EarlyStop, BatchThoughts, PreWarm, PerfMeter, Answer, Accelerator

```python
"""Acceleration adapter for the single v4 llama.cpp instance (caller owns PriorityRLock)."""

import hashlib
import json
import re
import time
from collections import OrderedDict
from pathlib import Path

from scp_context_manager import ContextManager

__all__ = [
    "PromptCache",
    "PrefixKVCache",
    "AdaptiveTokens",
    "EarlyStop",
    "BatchThoughts",
    "PreWarm",
    "PerfMeter",
    "Accelerator",
]


class PromptCache(OrderedDict):
    def put(self, key, value):
        self[key] = value
        self.move_to_end(key)
        if len(self) > 128:
            self.popitem(last=False)


class PrefixKVCache:
    """llama-cpp-python reuses matching input_ids in its current KV context.
    Tokenize the complete rendered prompt; do not snapshot a second KV arena."""

    def tokens(self, model, prompt):
        return model.tokenize(prompt.encode(), special=True)


class AdaptiveTokens:
    @staticmethod
    def limit(text, kind):
        return (
            48
            if kind == "thought"
            else 512
            if re.search("подробно|объясни", text, re.I)
            else 96
            if len(text) < 32
            else 160
        )


class EarlyStop:
    def __init__(self, model):
        self.model = model

    def __call__(self, ids, logits):
        if len(ids) < 16:
            return False
        return list(ids[-8:]) == list(ids[-16:-8])


class BatchThoughts:
    @staticmethod
    def prompt(items):
        return "\n".join(
            f"### THOUGHT {i} ###\n{text}" for i, text in enumerate(items, 1)
        )


class PreWarm:
    @staticmethod
    def run(model):
        model("Привет", max_tokens=1)


class PerfMeter:
    def __init__(self, root):
        self.path = Path(root) / "perf.jsonl"
        self.calls = self.hits = 0

    def record(self, n, start, first, cached):
        self.calls += 1
        self.hits += cached
        elapsed = time.monotonic() - first
        try:
            import psutil

            rss = psutil.Process().memory_info().rss
        except ImportError:
            rss = None
        with self.path.open("a", encoding="utf8") as f:
            f.write(
                json.dumps(
                    dict(
                        rss_bytes=rss,
                        tokens_sec=n / max(elapsed, 0.001),
                        prompt_eval_ms=1000 * (first - start),
                        gen_ms=1000 * elapsed,
                        cache_hit_rate=self.hits / self.calls,
                    )
                )
                + "\n"
            )


class Answer(str):
    def __new__(cls, text, cached=False):
        obj = super().__new__(cls, text)
        obj.cached = cached
        return obj


class Accelerator:
    def __init__(self, model, root, n_ctx, bus=None):
        self.model = model
        self.context = ContextManager(n_ctx, root)
        self.cache = PromptCache()
        self.prefix = PrefixKVCache()
        self.bus = bus
        self.perf = PerfMeter(root)
        self.n_ctx = n_ctx
        self.compact = True
        self.deadline = float("inf")
        # Keep the C function pointer alive for the lifetime of this GGUF.
        if hasattr(model, "ctx"):
            try:
                from llama_cpp import ggml_abort_callback, llama_set_abort_callback
            except ImportError:
                pass
            else:
                self.abort_callback = ggml_abort_callback(
                    lambda _: time.monotonic() >= self.deadline
                )
                llama_set_abort_callback(model.ctx, self.abort_callback, None)

    def summarize(self, prompt):
        ids = self.prefix.tokens(self.model, prompt)
        if len(ids) + 200 > self.n_ctx:
            return ""
        return self.model(ids, max_tokens=200, stop=["<end_of_turn>"])["choices"][0][
            "text"
        ].strip()

    def generate(
        self,
        messages,
        priority=5,
        kind="chat",
        max_tokens=512,
        temperature=0.7,
        top_p=0.9,
        on_chunk=None,
    ):
        self.deadline = time.monotonic() + (
            30 if kind == "thought" else 60 if priority >= 20 else 120
        )
        try:
            return self._generate(
                messages, priority, kind, max_tokens, temperature, top_p, on_chunk
            )
        finally:
            self.deadline = float("inf")

    def _generate(
        self,
        messages,
        priority=5,
        kind="chat",
        max_tokens=512,
        temperature=0.7,
        top_p=0.9,
        on_chunk=None,
    ):
        start = time.monotonic()
        n = min(max_tokens, AdaptiveTokens.limit(messages[-1]["content"], kind))
        prompt = self.context.prepare(
            messages,
            n,
            self.summarize if self.compact else None,
            lambda s: len(self.prefix.tokens(self.model, s)),
        )
        key = hashlib.sha256(repr((prompt, n, temperature, top_p)).encode()).digest()
        if key in self.cache:
            self.cache.move_to_end(key)
            text = self.cache[key]
            self.perf.record(0, start, start, True)
            if self.bus:
                self.bus.emit("cache_hit")
            if on_chunk:
                on_chunk(text)
            return Answer(text, True)
        ids = self.prefix.tokens(self.model, prompt)
        if len(ids) + n > self.n_ctx:
            raise ValueError("Обязательный контекст не помещается в n_ctx.")
        from llama_cpp import StoppingCriteriaList

        parts = []
        first = start
        for chunk in self.model(
            ids,
            max_tokens=n,
            temperature=temperature,
            top_p=top_p,
            stream=True,
            stop=["<end_of_turn>", "\n\n\n"],
            stopping_criteria=StoppingCriteriaList([EarlyStop(self.model)]),
        ):
            text = chunk["choices"][0]["text"]
            if not parts:
                first = time.monotonic()
            parts.append(text)
            if on_chunk:
                on_chunk(text)
        text = "".join(parts).strip()
        if time.monotonic() >= self.deadline:
            raise TimeoutError("Истекло время генерации")
        if text and not re.search(
            r"\[(?:TOOL|CMD|CREATEFILE|WEBSEARCH|REMIND|SPEAK):", text, re.I
        ):
            self.cache.put(key, text)
        self.perf.record(
            len(self.model.tokenize(text.encode(), add_bos=False)), start, first, False
        )
        return Answer(text)
```

# ФАЙЛ: scp_tts.py

# МЕСТО: TTSPlayer, TTSEngine

```python
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
```

# ФАЙЛ: scp_confirm.py

# МЕСТО: GuiGate

```python
"""Marshal owner-approved GUI operations to the Qt thread; never trust a tool argument as approval."""

from concurrent.futures import Future

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QMessageBox

__all__ = ["GuiGate"]


class GuiGate(QObject):
    request = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.request.connect(self.dispatch)

    @Slot(object)
    def dispatch(self, item):
        future, fn = item
        if not future.set_running_or_notify_cancel():
            return
        try:
            future.set_result(fn())
        except Exception as exc:
            future.set_exception(exc)

    def call(self, fn):
        if QThread.currentThread() == self.thread():
            return fn()
        f = Future()
        self.request.emit((f, fn))
        return f.result()

    def confirm(self, name, params):
        return self.call(
            lambda: QMessageBox.question(
                self.parent(),
                "Разрешить действие?",
                name + "\n" + repr(params)[:2000],
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            == QMessageBox.Yes
        )
```

# ФАЙЛ: scp_tools_extra.py

# МЕСТО: LocalTool, SchedulerTool, NotesTool, TodoTool, ClipboardTool, ScreenshotTool, AppControlTool, MediaControlTool, CalculatorTool, DiaryReaderTool, IntrospectionTool, MemorySearchTool, EmotionStateTool

```python
"""Additional local v4 tools and owner-confirmation helpers."""

import ast
import inspect
import math
import operator
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from scp_storage import read, save


def scheduler(env, action, text, seconds=None, dt=None):
    if action == "remind_at":
        at = datetime.fromisoformat(dt).timestamp()
    elif action == "remind_in":
        at = time.time() + int(seconds)
    else:
        raise ValueError(action)
    if (
        not time.time() - 1 <= at <= time.time() + 86400 * 365
        or not 0 < len(text) <= 2048
    ):
        raise ValueError("Недопустимое напоминание")
    p = env.cfg.root / "reminders.json"
    save(p, read(p, []) + [dict(at=at, text=text)])
    return "Запланировано"


def due(env):
    p = env.cfg.root / "reminders.json"
    rows = read(p, [])
    now = time.time()
    ready = [r["text"] for r in rows if r["at"] <= now]
    if ready:
        save(p, [r for r in rows if r["at"] > now])
    return ready


def notes(env, action, text="", index=None):
    p = env.cfg.root / "notes" / "notes.json"
    rows = read(p, [])
    if action == "list" or action == "search":
        return "\n".join(
            f"{i}: {r}" for i, r in enumerate(rows) if text.casefold() in r.casefold()
        )
    if action == "delete":
        rows.pop(int(index))
    elif action == "add" and 0 < len(text) <= 8192:
        rows.append(text)
    else:
        raise ValueError(action)
    save(p, rows)
    return "Готово"


def todo(env, action, text="", index=None):
    p = env.cfg.root / "todo.json"
    rows = read(p, [])
    if action == "list":
        return rows
    if action == "done":
        rows[int(index)]["done"] = True
        env.bus.emit("task_completed")
    elif action == "add" and 0 < len(text) <= 2048:
        rows.append(dict(text=text, done=False))
    else:
        raise ValueError(action)
    save(p, rows)
    return "Готово"


def clipboard(env, action, text=""):
    from PySide6.QtWidgets import QApplication

    cb = QApplication.clipboard()
    if action == "read":
        return cb.text()[:8192]
    if action == "write" and len(text) <= 8192:
        cb.setText(text)
        return "Готово"
    raise ValueError(action)


def screenshot(env):
    from PySide6.QtWidgets import QApplication

    p = env.cfg.root / "screenshots" / f"{time.time_ns()}.png"
    p.parent.mkdir(exist_ok=True)
    if not QApplication.primaryScreen().grabWindow(0).save(str(p)):
        raise RuntimeError("ОС не разрешила снимок")
    return str(p)


def app_control(env, action, name):
    p = Path(env.cfg.get("allowed_apps", {})[name])
    children = env.__dict__.setdefault("children", {})
    if not p.is_absolute() or not p.is_file():
        raise ValueError("Нужен абсолютный путь приложения")
    if action == "start" and (
        name not in children or children[name].poll() is not None
    ):
        children[name] = subprocess.Popen([str(p)], cwd=p.parent)
    elif action == "stop" and name in children:
        children.pop(name).terminate()
    else:
        raise ValueError("Недоступная операция")
    return "Готово"


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}


def calculate(expr, names=None):
    if len(expr) > 512:
        raise ValueError("Слишком длинное выражение")

    def visit(n):
        if isinstance(n, ast.Constant) and type(n.value) in (float, int):
            x = float(n.value)
        elif isinstance(n, ast.Name) and names and n.id in names:
            x = names[n.id]
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            x = visit(n.operand) * (-1 if isinstance(n.op, ast.USub) else 1)
        elif isinstance(n, ast.BinOp) and type(n.op) in OPS:
            x = OPS[type(n.op)](visit(n.left), visit(n.right))
        else:
            raise ValueError("Допустимы только арифметические выражения")
        if not math.isfinite(x):
            raise ValueError("Переполнение")
        return x

    return visit(ast.parse(expr, mode="eval").body)


def calculator(env, expression):
    return str(calculate(expression))


def terminal(env, command):
    """Только фиксированные диагностические команды, без shell и пользовательских аргументов."""
    commands = {
        "git --version": ["git", "--version"],
        "python --version": [sys.executable, "-I", "--version"],
        "pip --version": [sys.executable, "-I", "-m", "pip", "--version"],
    }
    if command in ("ls", "dir"):
        return "\n".join(f.name for f in env.cfg.root.iterdir())
    return subprocess.check_output(
        commands[command], cwd=env.cfg.root, timeout=5, text=True
    )


def python_exec(env, code):
    """Ограниченное подмножество Python: числовые присваивания и выражения."""
    if len(code) > 2048:
        raise ValueError("Слишком длинная программа")
    deadline = time.monotonic() + 5
    names = {}
    result = ""
    for line in ast.parse(code).body:
        if time.monotonic() > deadline:
            raise TimeoutError()
        if (
            isinstance(line, ast.Assign)
            and len(line.targets) == 1
            and isinstance(line.targets[0], ast.Name)
        ):
            result = calculate(ast.unparse(line.value), names)
            names[line.targets[0].id] = result
        elif isinstance(line, ast.Expr):
            result = calculate(ast.unparse(line.value), names)
        else:
            raise ValueError("Оператор запрещён")
    return str(result)


def media_control(env, action):
    if action == "next":
        tracks = env.music._library_tracks()
        i = getattr(env, "track_index", 0) + 1
        env.track_index = i
        return env.music.play(str(i % len(tracks) + 1)) if tracks else "Нет треков"
    return {"pause": env.music.pause, "play": env.music.resume, "stop": env.music.stop}[
        action
    ]()


def diary_reader(env, query=""):
    return [
        r for r in env.long.recent(200) if query.casefold() in r["summary"].casefold()
    ]


def introspection(env):
    return env.creator.context() + "\n" + str(env.short.get_context("local"))


def memory_search(env, query):
    return (
        env.long.query(query)
        + [
            r
            for r in env.short.get_context("local")
            if query.casefold() in r["content"].casefold()
        ]
        + [
            v
            for v in env.creator.context().splitlines()
            if query.casefold() in v.casefold()
        ]
    )


def emotion_state(env):
    return env.emotions.get_state()


class LocalTool:
    def __init__(self, env):
        self.env = env
        self.parameters = [
            {"name": k, "type": "string"}
            for k in list(inspect.signature(self.fn).parameters)[1:]
        ]

    def execute(self, **kwargs):
        return str(self.fn(self.env, **kwargs))


class SchedulerTool(LocalTool):
    name = "scheduler"
    description = "scheduler"
    fn = staticmethod(scheduler)


class NotesTool(LocalTool):
    name = "notes"
    description = "notes"
    fn = staticmethod(notes)


class TodoTool(LocalTool):
    name = "todo"
    description = "todo"
    fn = staticmethod(todo)


class ClipboardTool(LocalTool):
    name = "clipboard"
    description = "clipboard"
    fn = staticmethod(clipboard)


class ScreenshotTool(LocalTool):
    name = "screenshot"
    description = "screenshot"
    fn = staticmethod(screenshot)


class AppControlTool(LocalTool):
    name = "app_control"
    description = "app_control"
    fn = staticmethod(app_control)


class MediaControlTool(LocalTool):
    name = "media_control"
    description = "media_control"
    fn = staticmethod(media_control)


class CalculatorTool(LocalTool):
    name = "calculator"
    description = "calculator"
    fn = staticmethod(calculator)


class DiaryReaderTool(LocalTool):
    name = "diary_reader"
    description = "diary_reader"
    fn = staticmethod(diary_reader)


class IntrospectionTool(LocalTool):
    name = "introspection"
    description = "introspection"
    fn = staticmethod(introspection)


class MemorySearchTool(LocalTool):
    name = "memory_search"
    description = "memory_search"
    fn = staticmethod(memory_search)


class EmotionStateTool(LocalTool):
    name = "emotion_state"
    description = "emotion_state"
    fn = staticmethod(emotion_state)


def register_extra_tools(registry, env):
    for cls in (
        SchedulerTool,
        NotesTool,
        TodoTool,
        ClipboardTool,
        ScreenshotTool,
        AppControlTool,
        MediaControlTool,
        CalculatorTool,
        DiaryReaderTool,
        IntrospectionTool,
        MemorySearchTool,
        EmotionStateTool,
    ):
        registry.register(cls(env))


__all__ = [
    "SchedulerTool",
    "NotesTool",
    "TodoTool",
    "ClipboardTool",
    "ScreenshotTool",
    "AppControlTool",
    "MediaControlTool",
    "CalculatorTool",
    "DiaryReaderTool",
    "IntrospectionTool",
    "MemorySearchTool",
    "EmotionStateTool",
    "register_extra_tools",
]
```

# ФАЙЛ: scp_avatar_enhancer.py

# МЕСТО: HeadTilt, AvatarAnimator, EnhancedAvatarWindow

```python
"""Non-destructive animation for a rigged v5.3 companion canvas."""

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
```

# ИЗМЕНЕНИЯ В SCP-079-Derenguh_Andrea_SpeedFix_v4.py

Строки `-` относятся к приложенному оригиналу, `+` — к готовой версии. Номера и соседние строки задают место каждой вставки.

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -101,8 +101,8 @@

```diff
@@ -101,8 +101,8 @@
 TTS_OK = True
 
 try:
-    from telegram import Update
-    from telegram.ext import Application, MessageHandler, CommandHandler, filters
+    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
+    from telegram.ext import CallbackQueryHandler, Application, MessageHandler, CommandHandler, filters
     from telegram.request import HTTPXRequest
     from telegram.error import NetworkError
     TG_OK = True
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -136,6 +136,72 @@

```diff
@@ -136,6 +136,72 @@
 # ═══════════════════════════════════════════════════════════════════════════
 #  КОНФИГ
 # ═══════════════════════════════════════════════════════════════════════════
+try:
+    from scp_accelerator import Accelerator, BatchThoughts, PreWarm
+    ACCEL_OK = True
+except ImportError:
+    ACCEL_OK = False
+
+try:
+    from scp_context_manager import ContextManager
+    CTX_OK = True
+except ImportError:
+    CTX_OK = False
+
+try:
+    from scp_emotion_engine import EmotionEngine
+    EMOTION_V2_OK = True
+except ImportError:
+    EMOTION_V2_OK = False
+
+try:
+    from scp_event_bus import EventBus
+    BUS_OK = True
+except ImportError:
+    BUS_OK = False
+
+try:
+    from scp_presence import PresenceTracker
+    PRESENCE_OK = True
+except ImportError:
+    PRESENCE_OK = False
+
+try:
+    from scp_autonomy import AutonomySource, ThoughtDeduplicator, ProactiveScheduler
+    AUTONOMY_V2_OK = True
+except ImportError:
+    AUTONOMY_V2_OK = False
+
+try:
+    from scp_memory import MemoryConfig, ShortTermMemory, LongTermMemory, CreatorProfile, MemoryMigrator
+    MEMORY_V2_OK = True
+except ImportError:
+    MEMORY_V2_OK = False
+
+try:
+    from scp_tts import TTSEngine
+    TTS_V2_OK = True
+except ImportError:
+    TTS_V2_OK = False
+
+try:
+    from scp_tools_extra import register_extra_tools, due
+    TOOLS_EXTRA_OK = True
+except ImportError:
+    TOOLS_EXTRA_OK = False
+
+try:
+    from scp_confirm import GuiGate
+    CONFIRM_OK = True
+except ImportError:
+    CONFIRM_OK = False
+
+try:
+    from scp_safety import SafetyLayer
+    SAFETY_OK = True
+except ImportError:
+    SAFETY_OK = False
+
 CONFIG_FILE = Path("aria_config.json")
 
 DEFAULT_SYSTEM_PROMPT = """\
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -169,7 +235,7 @@

```diff
@@ -169,7 +235,7 @@
     "model_path":             "",
     "avatar_project":          "",
     "chat_format":            "",  # пусто = использовать chat template из метаданных GGUF
-    "n_ctx":                  4096,
+    "n_ctx":                  3072,
     "n_threads":              max(1, (os.cpu_count() or 2) - 1),
     "n_gpu_layers":           0,
     "temperature":            0.7,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -195,7 +261,7 @@

```diff
@@ -195,7 +261,7 @@
     "disable_model_thinking":  True,
     "tts_enabled":            True,
      "tts_model_path":         "",
-    "tts_voice":              "xenia",
+    "tts_voice":              "ru_RU-irina-medium",
     "tts_sample_rate":        48000,
     "tts_threads":            2,
     "telegram_voice_replies": True,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -244,7 +310,7 @@

```diff
@@ -244,7 +310,7 @@
     "lively_proactive_min_minutes": 45,
     "lively_proactive_max_minutes": 90,
     "lively_proactive_user_cooldown_hours": 8,
-    "lively_group_chat_id": -1004412563438,
+    "lively_group_chat_id": 0,
     "lively_group_thread_id": 0,
     "lively_group_quiet_minutes": 15,
     "lively_group_proactive_min_minutes": 60,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -322,6 +388,13 @@

```diff
@@ -322,6 +388,13 @@
     CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
 
 CFG = load_config()
+for _key, _value in dict(accelerator_enabled=True, context_manager_enabled=True, emotion_v2_enabled=True,
+        presence_enabled=True, proactive_enabled=True, proactive_min_gap_minutes=240, proactive_daily_limit=4,
+        proactive_quiet_hours="23:00-08:00", short_memory_ttl_hours=72, dedup_jaccard_threshold=.75,
+        tts_backend="piper", tts_cache_max_mb=200, avatar_enhanced=True, allowed_apps={}, web_enabled=False).items():
+    CFG.setdefault(_key, _value)
+WEB_OK = WEB_OK and CFG['web_enabled']
+GOOGLE_SEARCH_OK = GOOGLE_SEARCH_OK and CFG['web_enabled']
 
 # Автономность теперь запускается ТОЛЬКО вручную владельцем.
 # Один раз сбрасываем прежний режим автостарта, чтобы старый config не включил его сам.
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -357,7 +430,7 @@

```diff
@@ -357,7 +430,7 @@
 CFG.setdefault("lively_proactive_min_minutes", 45)
 CFG.setdefault("lively_proactive_max_minutes", 90)
 CFG.setdefault("lively_proactive_user_cooldown_hours", 8)
-CFG.setdefault("lively_group_chat_id", -1004412563438)
+CFG.setdefault("lively_group_chat_id", 0)
 CFG.setdefault("lively_group_thread_id", 0)
 CFG.setdefault("lively_group_quiet_minutes", 15)
 CFG.setdefault("lively_group_proactive_min_minutes", 60)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -391,7 +464,7 @@

```diff
@@ -391,7 +464,7 @@
 # Лёгкий профиль по умолчанию: не раздуваем контекст и не запускаем
 # дополнительный когнитивный запрос перед каждым ответом.
 CFG["meta_intensive_mode"] = False
-CFG["tts_enabled"] = True
+CFG.setdefault("tts_enabled", True)
 CFG["n_ctx"] = min(max(int(CFG.get("n_ctx", 4096)), 2048), 8192)
 _available_threads = max(1, (os.cpu_count() or 2) - 1)
 CFG["n_threads"] = max(1, min(max(int(CFG.get("n_threads", _available_threads)), min(_available_threads, 8)), _available_threads, 10))
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -406,9 +479,9 @@

```diff
@@ -406,9 +479,9 @@
     except Exception:
         pass
 
-CFG["tts_enabled"] = True
+CFG.setdefault("tts_enabled", True)
 CFG.setdefault("tts_voice", "xenia")
-if str(CFG.get("tts_voice", "")).casefold().startswith("ru_ru-"):
+if CFG["tts_backend"] == "silero" and str(CFG.get("tts_voice", "")).casefold().startswith("ru_ru-"):
     CFG["tts_voice"] = "xenia"
 CFG.setdefault("telegram_voice_replies", True)
 CFG.setdefault("telegram_video_notes", True)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -491,6 +564,25 @@

```diff
@@ -491,6 +564,25 @@
     (personal_folder() / "журнал").mkdir(parents=True, exist_ok=True)
 
 ensure_personal_space()
+# ВСТАВИТЬ: после создания workspace, до конструкторов v4, читающих JSON.
+from types import SimpleNamespace
+event_bus = EventBus() if BUS_OK else None
+presence = PresenceTracker(workspace(), event_bus) if PRESENCE_OK and event_bus and CFG['presence_enabled'] else None
+if MEMORY_V2_OK:
+    MemoryMigrator().migrate_from_v4_once(workspace(), CFG)
+    memcfg = MemoryConfig(workspace(), CFG)
+    archive = LongTermMemory(workspace())
+    creator_profile = CreatorProfile(workspace())
+proactive = ProactiveScheduler(CFG, presence) if AUTONOMY_V2_OK and presence else None
+dedup = ThoughtDeduplicator(workspace(),CFG['dedup_jaccard_threshold']) if AUTONOMY_V2_OK else None
+autonomy_source = AutonomySource(event_bus) if AUTONOMY_V2_OK else None
+emotion_engine = EmotionEngine(workspace(),event_bus) if EMOTION_V2_OK and CFG['emotion_v2_enabled'] else None
+gui_gate = None
+try:
+    from scp_avatar_enhancer import EnhancedAvatarWindow
+    AVATAR_V2_OK = True
+except ImportError:
+    AVATAR_V2_OK = False
 
 
 # =========================================================================
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -732,7 +824,7 @@

```diff
@@ -732,7 +824,7 @@
     def execute(self, action: str, path: str, content: str = "") -> str:
         try:
             p = (workspace() / path).resolve()
-            if not str(p).startswith(str(workspace().resolve())):
+            if not p.is_relative_to(workspace().resolve()):
                 return "Доступ запрещён за пределами рабочей папки."
             if action == "read":
                 if not p.exists(): return f"Файл {path} не найден."
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -763,14 +855,10 @@

```diff
@@ -763,14 +855,10 @@
     description = "Выполнение команд в терминале (только безопасные)"
     parameters = [{"name": "command", "type": "string"}]
     def execute(self, command: str) -> str:
-        if ".." in command or ";" in command or "|" in command or "&" in command:
-            return "Команда содержит недопустимые символы."
-        try:
-            result = subprocess.run(command, shell=True, capture_output=True, text=True,
-                                    timeout=30, cwd=str(workspace()))
-            return (result.stdout + result.stderr)[:4000]
-        except Exception as e:
-            return f"Ошибка: {e}"
+        if not TOOLS_EXTRA_OK: return "Отключено"
+        from scp_tools_extra import terminal
+        return terminal(tools_env,command)
+
 
 
 class ProcessManagerTool(Tool):
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -792,24 +880,8 @@

```diff
@@ -792,24 +880,8 @@
                 except Exception:
                     pass
             return "\n".join(processes[:50])
-        elif action == "start":
-            if not command: return "Не указана команда."
-            try:
-                p = subprocess.Popen(command, shell=True)
-                return f"Запущен процесс PID {p.pid}"
-            except Exception as e:
-                return f"Ошибка запуска: {e}"
-        elif action in ("stop", "kill"):
-            if not name: return "Не указано имя процесса."
-            found = False
-            for proc in psutil.process_iter(['pid', 'name']):
-                try:
-                    if name in proc.info['name']:
-                        proc.terminate() if action == "stop" else proc.kill()
-                        found = True
-                except Exception:
-                    pass
-            return f"Процесс {name} {'остановлен' if found else 'не найден'}."
+        elif action in ('start','stop','kill'):
+            return 'Для управления разрешёнными приложениями используйте app_control.'
         return "Неизвестное действие."
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -914,17 +986,10 @@

```diff
@@ -914,17 +986,10 @@
     description = "Выполнение Python-кода (безопасно)"
     parameters = [{"name": "code", "type": "string"}]
     def execute(self, code: str) -> str:
-        if "import os" in code or "import subprocess" in code or "exec" in code or "eval" in code:
-            return "Код содержит небезопасные конструкции."
-        try:
-            tmp_file = workspace() / "_temp_exec.py"
-            tmp_file.write_text(code, encoding="utf-8")
-            result = subprocess.run([sys.executable, str(tmp_file)], capture_output=True,
-                                    text=True, timeout=5, cwd=str(workspace()))
-            tmp_file.unlink(missing_ok=True)
-            return result.stdout + result.stderr
-        except Exception as e:
-            return f"Ошибка: {e}"
+        if not TOOLS_EXTRA_OK: return "Отключено"
+        from scp_tools_extra import python_exec
+        return python_exec(tools_env,code)
+
 
 
 class WebTool(Tool):
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -1229,6 +1294,7 @@

```diff
@@ -1229,6 +1294,7 @@
 
     @staticmethod
     def _http_json(url, params=None, timeout=20):
+        if not CFG["web_enabled"]: raise PermissionError("Интернет выключен")
         if params:
             url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
         req = urllib.request.Request(url, headers={"User-Agent": "SCP-079-Derenguh/1.0"})
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -1276,6 +1342,7 @@

```diff
@@ -1276,6 +1342,7 @@
         return max(mp3s, key=lambda f: int(f.get("size", 0)))
 
     def _download_archive(self, identifier):
+        if not CFG["web_enabled"]: raise PermissionError("Интернет выключен")
         meta = self._http_json(self.META.format(identifier=urllib.parse.quote(identifier, safe="")))
         if not self._is_allowed_metadata(meta):
             return None, "Не указана свободная лицензия."
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -1923,8 +1990,27 @@

```diff
@@ -1923,8 +1990,27 @@
     def execute(self, tool_name: str, **kwargs) -> str:
         tool = self.get(tool_name)
         if tool:
-            try: return tool.execute(**kwargs)
-            except Exception as e: return f"Ошибка {tool_name}: {e}"
+            try:
+                if not getattr(_CURRENT_REQUEST,'is_owner',False) and tool_name not in ("calculator","system_monitor"): return 'Действие доступно только владельцу.'
+                dangerous = tool_name in ('terminal','python_executor','app_control','screenshot','clipboard') or (tool_name=='filesystem' and kwargs.get('action') in ('delete','write'))
+                if dangerous:
+                    ctx = str(getattr(_CURRENT_CTX,'value',''))
+                    if ctx.startswith('tg:'): approved = tg_bridge.confirm_tool(ctx,tool_name,kwargs)
+                    else: approved = ctx=='local' and gui_gate and gui_gate.confirm(tool_name,kwargs)
+                    if not approved: return 'Действие не подтверждено.'
+                if tool_name in ('clipboard','screenshot'):
+                    if not gui_gate: return 'Нет графической сессии.'
+                    result = gui_gate.call(lambda:tool.execute(**kwargs))
+                else: result = tool.execute(**kwargs)
+                kind='tool_failure' if str(result).startswith('Ошибка') else 'tool_success'
+                if event_bus: event_bus.emit(kind, {'tool':tool_name})
+                if MEMORY_V2_OK: archive.add_diary(('Получилось: ' if kind=='tool_success' else 'Не получилось: ')+tool_name,[kind],'tool')
+                if presence: presence.data['system_activity_at']=time.time()
+                return result
+            except Exception as e:
+                if event_bus: event_bus.emit('tool_failure',{'tool':tool_name})
+                if MEMORY_V2_OK: archive.add_diary('Не получилось: '+tool_name,['tool_failure'],'tool')
+                return f"Ошибка {tool_name}: {e}"
         return f"Инструмент {tool_name} не найден."
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2087,10 +2173,11 @@

```diff
@@ -2087,10 +2173,11 @@
 class SessionMemory:
     """Краткосрочная память диалогов с сохранением между перезапусками."""
     def __init__(self):
+        self.store = ShortTermMemory(memcfg) if MEMORY_V2_OK else None
         self._contexts: Dict[str, List[dict]] = {}
         self._lock = threading.RLock()
         self._path = workspace() / "session_memory.json"
-        self._load()
+        if not self.store: self._load()
 
     def _load(self):
         try:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2122,6 +2209,7 @@

```diff
@@ -2122,6 +2209,7 @@
 
     def add(self, ctx_id, role, content):
         with self._lock:
+            if self.store: return self.store.add(ctx_id,role,str(content))
             hist = self._get_or_create(ctx_id)
             hist.append({"role": role, "content": str(content), "time": time.time()})
             limit = max(4, int(CFG.get("short_memory_limit", 10)) * 2)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2131,15 +2219,18 @@

```diff
@@ -2131,15 +2219,18 @@
 
     def get(self, ctx_id):
         with self._lock:
+            if self.store: return [dict(role=r["role"], content=r["text"], time=r["at"]) for r in self.store.get_hot(ctx_id)]
             return [dict(x) for x in self._get_or_create(ctx_id)]
 
     def clear(self, ctx_id):
         with self._lock:
+            if self.store: return self.store.clear(ctx_id)
             self._contexts.pop(ctx_id, None)
             self._save()
 
     def clear_all(self):
         with self._lock:
+            if self.store: return self.store.clear_all()
             self._contexts.clear()
             self._save()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2180,6 +2271,7 @@

```diff
@@ -2180,6 +2271,7 @@
                 except Exception: pass
             if "facts" not in data: data["facts"] = []
             if fact not in data["facts"]:
+                if event_bus: event_bus.emit("knowledge_added", {"topic":topic})
                 data["facts"].append(fact)
                 data["confidence"] = confidence
                 data["sources"] = list(set((sources or []) + data.get("sources", [])))
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2296,7 +2388,7 @@

```diff
@@ -2296,7 +2388,7 @@
         (folder / "hypothesis.txt").write_text(hypothesis, encoding="utf-8")
         (folder / "code.py").write_text(code, encoding="utf-8")
         (folder / "expected.txt").write_text(expected, encoding="utf-8")
-        result = PythonExecutorTool().execute(code)
+        result = tool_registry.execute("python_executor",code=code)
         success = result.strip() == expected.strip()
         log_data = {"name": name, "timestamp": time.time(), "hypothesis": hypothesis,
                     "code": code, "expected": expected, "result": result, "success": success}
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2469,6 +2561,10 @@

```diff
@@ -2469,6 +2561,10 @@
                 log.warning("EmotionalModel save failed: %s", exc)
 
     def update(self, trigger, delta):
+        if emotion_engine:
+            from scp_emotion_engine import EMOTION_DELTAS
+            if trigger in EMOTION_DELTAS: return emotion_engine.apply_event(trigger)
+            return emotion_engine.apply_event("legacy_update", trigger=str(trigger), delta=float(delta))
         with self._lock:
             key_text = str(trigger).casefold()
             for key in self.emotions:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2480,6 +2576,7 @@

```diff
@@ -2480,6 +2576,7 @@
 
     def cool(self, elapsed=None):
         """Медленно возвращает показатели к нейтральным базовым значениям."""
+        if emotion_engine: return emotion_engine.cool(elapsed)
         with self._lock:
             now = time.time()
             if elapsed is None:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2498,7 +2595,7 @@

```diff
@@ -2498,7 +2595,7 @@
 
     def get_state(self):
         with self._lock:
-            return dict(self.emotions)
+            return dict(emotion_engine.values if emotion_engine else self.emotions)
 
     def adapt_to_message(self, text):
         """Лексическая эвристика русского текста; не запускает вторую нейросеть."""
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2518,6 +2615,12 @@

```diff
@@ -2518,6 +2615,12 @@
         playful = ("ахах", "хаха", "смешно", "шучу", "прикол", "забавно")
         urgent = ("срочно", "быстрее", "немедленно", "важно", "авария")
         question = "?" in raw or any(x in joined for x in ("почему", "как", "зачем", "интересно"))
+        if emotion_engine:
+            emotion_engine.cool()
+            kind = "user_message_positive" if any(x in joined for x in positive) else "user_message_negative" if any(x in joined for x in negative) else "user_message"
+            if event_bus: event_bus.emit(kind)
+            else: emotion_engine.apply_event(kind)
+            return
         with self._lock:
             if any(x in joined for x in positive):
                 self.emotions["satisfaction"] = min(1.0, self.emotions["satisfaction"] + 0.08)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2556,6 +2659,7 @@

```diff
@@ -2556,6 +2659,7 @@
         return "Подстраивай длину и техническую глубину под контекст, не задавай повторных вопросов без необходимости."
 
     def apply_to_prompt(self, prompt):
+        if emotion_engine and SAFETY_OK: return emotion_engine.apply_to_prompt(prompt)
         state = self.get_state()
         if state["irritation"] > 0.62 or state["frustration"] > 0.62:
             mood = "Собеседник мог устать или раздражаться. Будь спокойной, живой и конкретной; признай проблему и сразу помоги."
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2624,6 +2728,8 @@

```diff
@@ -2624,6 +2728,8 @@
         if not fact: return
         with self._lock:
             if fact not in [x.get("text") for x in self.data["facts"]]:
+                if MEMORY_V2_OK: archive.add_fact(fact,source); creator_profile.observe(fact)
+                if event_bus: event_bus.emit("knowledge_added", {"source":source})
                 self.data["facts"].append({"text": fact, "source": source, "time": time.time()})
                 self.data["facts"] = self.data["facts"][-300:]
                 self._save()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2733,6 +2839,7 @@

```diff
@@ -2733,6 +2839,7 @@
             {"role": "user", "content": prompt},
         ]
         try:
+            if kind=='batch': messages[0]['content']='Ты Андреа. Для каждого заголовка THOUGHT напиши одно предложение по-русски. Верни заголовки и ответы.'
             old_ctx = getattr(_CURRENT_CTX, "value", None) if "_CURRENT_CTX" in globals() else None
             if "_CURRENT_CTX" in globals():
                 _CURRENT_CTX.value = "internal"
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2760,15 +2867,28 @@

```diff
@@ -2760,15 +2867,28 @@
             log.warning("InternalLoop callback failed: %s", exc)
 
     def _diary_thought(self):
-        thought = self._ask_llm("thought", "Сформулируй одну самостоятельную короткую мысль для личного дневника на основе общих интересов кода, науки и текущего контекста. Не обращайся к создателю.", 56)
-        if thought:
-            activity_logger.log_reflection("[thought] " + thought)
-            try:
-                target = personal_subfolder("thoughts") / f"thoughts_{datetime.date.today().isoformat()}.md"
-                with target.open("a", encoding="utf-8") as f:
-                    f.write(f"\n- [{datetime.datetime.now():%H:%M:%S}] {thought}\n")
-            except Exception as exc:
-                log.warning("Thought diary write failed: %s", exc)
+        source = autonomy_source.next() if autonomy_source else ""
+        recent = [r["summary"] for r in archive.recent(5)] if MEMORY_V2_OK else []
+        inputs = [f"Контекст: {source}. Не повторяй: {recent}. Одна короткая самостоятельная мысль для личного дневника."]
+        if ACCEL_OK and autonomy_source and autonomy_source.pending:
+            inputs.append(f"Вторая независимая мысль о: {autonomy_source.next()}. Не повторяй первую.")
+        if len(inputs)>1:
+            prompt = 'Ответь двумя фразами, сохрани разделители. ' + BatchThoughts.prompt(inputs)
+            reply = self._ask_llm('batch',prompt,96)
+            thoughts = [t.strip() for t in re.split(r'### THOUGHT \d+ ###',reply) if t.strip()][:2]
+        else: thoughts = [self._ask_llm('thought',inputs[0],48)]
+        for thought in thoughts:
+            if thought and not (dedup and dedup.is_duplicate(thought)):
+                if MEMORY_V2_OK: archive.add_diary(thought,["мысль"])
+                if dedup: dedup.remember(thought)
+                if event_bus: event_bus.emit("diary_written")
+                activity_logger.log_reflection("[thought] " + thought)
+                try:
+                    target = personal_subfolder("thoughts") / f"thoughts_{datetime.date.today().isoformat()}.md"
+                    with target.open("a", encoding="utf-8") as f:
+                        f.write(f"\n- [{datetime.datetime.now():%H:%M:%S}] {thought}\n")
+                except Exception as exc:
+                    log.warning("Thought diary write failed: %s", exc)
         low = max(5, int(CFG.get("lively_diary_interval_min", 12)))
         high = max(low, int(CFG.get("lively_diary_interval_max", 25)))
         self._next_diary_at = time.time() + random.uniform(low * 60, high * 60)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2785,15 +2905,29 @@

```diff
@@ -2785,15 +2905,29 @@
         question = self._ask_llm("question", "Задай создателю один естественный, ненавязчивый личный вопрос, который поможет лучше понять его интересы или текущие планы. Не задавай вопрос о здоровье, внешности или секретах.", 48)
         if question:
             creator_memory.add_question(question)
+            if proactive: proactive.record("question",question)
             self._emit("question", question)
 
     def _step(self):
+        if presence: presence.tick()
+        if event_bus:
+            hour = datetime.datetime.now().hour
+            period = 'night' if hour>=23 or hour<6 else 'morning' if hour<10 else 'day'
+            if period!=getattr(self,'_period',None):
+                self._period=period
+                event_bus.emit('time_of_day' if period=='day' else 'time_of_day_'+period,{'hour':hour})
+        if MEMORY_V2_OK and time.monotonic() >= getattr(self, '_gc_at', 0):
+            with short_mem._lock: short_mem.store.gc_expired()
+            self._gc_at = time.monotonic()+3600
         emotional_model.cool()
         if not (CFG.get("autonomous_enabled", False) and CFG.get("sleep_mode", False)):
             self._last_presence = creator_state.check()
             return
+        if proactive and self.message_callback:
+            item = proactive.maybe_send()
+            if item: self._emit('greeting', item[1])
         present = creator_state.check()
-        if present and not self._last_presence:
+        if present and not self._last_presence and not proactive:
             greeting = self._ask_llm("greeting", "Создатель вернулся после отсутствия. Поздоровайся коротко и естественно.", 40)
             self._emit("greeting", greeting or "С возвращением. Я здесь и готова продолжить.")
             with self._lock:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2806,7 +2940,7 @@

```diff
@@ -2806,7 +2940,7 @@
         if time.time() >= self._next_diary_at:
             self._diary_thought()
         idle = not present
-        self._maybe_creator_question(idle)
+        if not proactive or proactive.can_send(): self._maybe_creator_question(idle)
 
 
 internal_loop = InternalLoop()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2818,7 +2952,8 @@

```diff
@@ -2818,7 +2952,8 @@
         self._last_activity = time.time()
         self._lock = threading.RLock()
         self._threshold = max(1.0, float(CFG.get("autonomous_idle_minutes", 10)) * 60.0)
-    def set_active(self):
+    def set_active(self, user_message=False):
+        if user_message and presence: presence.on_user_message()
         with self._lock:
             self._is_present = True
             self._last_activity = time.time()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2831,6 +2966,7 @@

```diff
@@ -2831,6 +2966,7 @@
             return self._is_present
     def on_wake(self):
         if not self._is_present:
+            if event_bus: event_bus.emit("wake")
             self._is_present = True
             self._last_activity = time.time()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -2944,6 +3080,7 @@

```diff
@@ -2944,6 +3080,7 @@
         self._path().write_text(json.dumps(self._items, ensure_ascii=False, indent=2), "utf-8")
     def add(self, fact):
         if fact and fact not in self._items:
+            if MEMORY_V2_OK: archive.add_fact(fact,self._filename); creator_profile.observe(fact)
             self._items.append(fact); self._save()
     def remove(self, idx):
         if 0 <= idx < len(self._items):
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3025,6 +3162,7 @@

```diff
@@ -3025,6 +3162,7 @@
 
     def __init__(self):
         super().__init__()
+        self._speech_ticket = 0
         self._queue = queue.Queue(maxsize=80)
         self._thread = None
         self._stop_event = threading.Event()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3036,7 +3174,7 @@

```diff
@@ -3036,7 +3174,7 @@
         self._torch = None
         self._silero_load_error = None
         self._fallback_lock = threading.RLock()
-        self._speaker = str(CFG.get("tts_voice", "xenia") or "xenia")
+        self._speaker = str(CFG.get("silero_speaker", "xenia") if CFG["tts_backend"]!="silero" else CFG.get("tts_voice", "xenia"))
         self._sample_rate = int(CFG.get("tts_sample_rate", 48000))
 
     def _load_model(self):
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3047,17 +3185,12 @@

```diff
@@ -3047,17 +3185,12 @@
                 raise RuntimeError(str(self._silero_load_error))
             self.status_changed.emit("Silero: загружаю русскую женскую модель…")
             try:
+                if not Path(CFG.get("tts_model_path") or "").is_file(): raise FileNotFoundError("Нет локального пакета Silero")
                 import torch
                 torch.set_num_threads(max(1, min(int(CFG.get("tts_threads", 2)), 2)))
-                model, _example_text = torch.hub.load(
-                    repo_or_dir="snakers4/silero-models",
-                    model="silero_tts",
-                    language="ru",
-                    speaker="v4_ru",
-                    # Автоматически принимаем доверие к официальному репозиторию,
-                    # чтобы torch.hub не ждал ручного ввода в фоне.
-                    trust_repo=True,
-                )
+                local_model = Path(CFG.get('tts_model_path') or '')
+                if not local_model.is_file(): raise FileNotFoundError('Укажите локальный пакет Silero')
+                model = torch.package.PackageImporter(str(local_model)).load_pickle('tts_models','model')
                 model.to(torch.device("cpu"))
                 self._model = model
                 self._apply_tts = model.apply_tts
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3130,6 +3263,15 @@

```diff
@@ -3130,6 +3263,15 @@
         return target_path
 
     def _synthesize(self, text, target_path):
+        if voice_engine:
+            with voice_engine.lock:
+                wav = voice_engine.synthesize(text,emotion_engine.describe_short() if emotion_engine else 'calm')
+                Path(target_path).parent.mkdir(parents=True,exist_ok=True)
+                shutil.copyfile(wav,target_path)
+            return Path(target_path)
+        return self._synthesize_legacy(text,target_path)
+
+    def _synthesize_legacy(self, text, target_path):
         text = re.sub(r"\\s+", " ", str(text or "")).strip()
         if not text:
             raise ValueError("Пустой текст для синтеза")
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3228,11 +3370,20 @@

```diff
@@ -3228,11 +3370,20 @@
             return
         self.start()
         try:
-            self._queue.put_nowait(speech)
+            if voice_engine:
+                with self._lock:
+                    self._speech_ticket += 1
+                    voice_engine.stop()
+                    self._queue.put_nowait((self._speech_ticket,speech))
+            else: self._queue.put_nowait(speech)
         except queue.Full:
             log.warning("Silero TTS queue full; phrase skipped")
 
     def _play_wav(self, wav_path):
+        if voice_engine and PYGAME_OK:
+            voice_engine.player.play(wav_path)
+            while voice_engine.is_speaking() and not self._stop_event.is_set(): time.sleep(.04)
+            return
         if os.name == "nt":
             import winsound
             winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3260,8 +3411,10 @@

```diff
@@ -3260,8 +3411,10 @@
             wav_path = workspace() / "temp" / "tts" / f"speech_{int(time.time()*1000)}.wav"
             try:
                 self.speaking_changed.emit(True)
+                ticket,item = item if isinstance(item,tuple) else (self._speech_ticket,item)
+                if ticket!=self._speech_ticket: continue
                 self._synthesize(item, wav_path)
-                self._play_wav(wav_path)
+                if ticket==self._speech_ticket: self._play_wav(wav_path)
             except Exception as exc:
                 log.exception("Silero synthesis/playback error: %s", exc)
                 self.status_changed.emit(f"Ошибка Silero: {exc}")
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3276,6 +3429,7 @@

```diff
@@ -3276,6 +3429,7 @@
             self._started = False
 
     def stop_engine(self):
+        if voice_engine: voice_engine.stop()
         self._stop_event.set()
         try:
             self._queue.put_nowait(None)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3289,7 +3443,12 @@

```diff
@@ -3289,7 +3443,12 @@
                 pass
 
 
+if TOOLS_EXTRA_OK and MEMORY_V2_OK:
+    tools_env = SimpleNamespace(cfg=memcfg,long=archive,short=short_mem,creator=creator_memory,emotions=emotional_model,music=music_manager,bus=event_bus)
+    register_extra_tools(tool_registry,tools_env)
+
 tts = SileroTTS()
+voice_engine = TTSEngine(workspace(),CFG,tts._synthesize_legacy) if TTS_V2_OK else None
 
 
 # ---- Lively dialogue layer: format routing, prompt rendering and chat memory ----
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3465,7 +3624,8 @@

```diff
@@ -3465,7 +3624,8 @@
                         lambda m: str(values.get(m.group(1), m.group(0))), template)
     try:
         if "creator_memory" in globals() and getattr(_CURRENT_REQUEST, "is_owner", False):
-            creator_context = creator_memory.context(2500)
+            creator_context = creator_memory.context(1600)
+            if MEMORY_V2_OK: creator_context += "\n" + creator_profile.context()
             if creator_context.strip():
                 prompt += "\n\nДополнительный контекст о создателе:\n" + creator_context
     except Exception as exc:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3496,9 +3656,9 @@

```diff
@@ -3496,9 +3656,9 @@
         return min(configured, 96)
     detailed = re.search(r"подробн|детальн|разбер|разбор|проанализ|объясни|поясни|распиши|в деталях|пошаг|с примерами|сравни", raw)
     if detailed:
-        return min(configured, 420)
+        return min(configured, 512)
     if len(raw) <= 90 and ("?" in raw or re.search(r"^(привет|здравствуй|здравствуйте|ау|ты тут|жива|как дела|спасибо|ок|понял|поняла)\b", raw)):
-        return min(configured, 64)
+        return min(configured, 96)
     if len(raw) <= 180:
         return min(configured, 144)
     return min(configured, 256)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3507,6 +3667,9 @@

```diff
@@ -3507,6 +3667,9 @@
 def handle_incoming(user_text, reply_fn, voice_fn, circle_fn, ctx_id):
     """Общая точка входа: текст/ГС/кружок и единая память для всех каналов."""
     original_text = str(user_text or "").strip()
+    if any(w.strip().casefold() in original_text.casefold() for w in CFG['safety_blacklist'].split(',') if w.strip()):
+        if reply_fn: reply_fn(CFG['safety_response'])
+        return dict(format='text',text=CFG['safety_response'],path=None,error=None)
     fmt, clean_text = detect_format_request(original_text)
     if not llm.ready:
         answer = "Модель не загружена. Сначала загрузи GGUF-модель."
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3536,6 +3699,7 @@

```diff
@@ -3536,6 +3699,7 @@
     try:
         answer = None
         if is_owner:
+            if MEMORY_V2_OK: creator_profile.observe(clean_text)
             try:
                 answer = music_manager.handle_command(clean_text)
             except Exception as exc:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3580,6 +3744,11 @@

```diff
@@ -3580,6 +3744,11 @@
                 {"role": "system", "content": system_prompt + runtime + "\n\nОтвечай только по-русски. Не показывай внутренний анализ."},
                 {"role": "user", "content": user_content},
             ]
+            if CFG['context_manager_enabled']:
+                with short_mem._lock:
+                    history = ([dict(role=r['role'],content=r['text']) for r in short_mem.store.get_window(ctx_id,80)]
+                               if short_mem.store else short_mem.get_context(ctx_id))
+                messages[1:1] = history
             try:
                 with llm._llm_lock:
                     raw = llm._chat(messages, max_tokens=response_tokens,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3622,6 +3791,7 @@

```diff
@@ -3622,6 +3791,7 @@
                 log.exception("handle_incoming generation failed: %s", exc)
                 answer = "Не получилось получить ответ от модели. Подробности записаны в aria.log."
 
+        if emotion_engine and SAFETY_OK: answer = SafetyLayer.filter(answer,emotion_engine.values)
         short_mem.add(ctx_id, "user", f"[{username}]: {original_text}")
         short_mem.add(ctx_id, "assistant", answer)
         log.info("[INCOMING] generated ctx=%s elapsed=%.1fs chars=%d", ctx_id,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3770,14 +3940,7 @@

```diff
@@ -3770,14 +3940,7 @@
 class Tools:
     @staticmethod
     def cmd(command):
-        if ".." in command or ":" in command:
-            return "[CMD] Доступ запрещён."
-        try:
-            r = subprocess.run(command, shell=True, capture_output=True, text=True,
-                               timeout=30, cwd=str(workspace()), encoding="utf-8", errors="replace")
-            return f"[CMD]\n{(r.stdout or r.stderr or '(нет вывода)')[:2000]}"
-        except subprocess.TimeoutExpired: return "[CMD] Таймаут."
-        except Exception as e: return f"[CMD ошибка] {e}"
+        return tool_registry.execute('terminal',command=command)
 
     @staticmethod
     def create_file(name, content):
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -3798,7 +3961,7 @@

```diff
@@ -3798,7 +3961,7 @@
 
     @staticmethod
     def _http_session():
-        if not WEB_OK:
+        if not CFG["web_enabled"] or not WEB_OK:
             return None
         session = requests.Session()
         try:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4097,6 +4260,7 @@

```diff
@@ -4097,6 +4260,7 @@
 
     @staticmethod
     def execute_directives(directives):
+        if not getattr(_CURRENT_REQUEST,"is_owner",False): return []
         out = []
         for d in directives:
             try:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4309,6 +4473,8 @@

```diff
@@ -4309,6 +4473,8 @@
         def _work():
             self.status_msg.emit("Загрузка GGUF…", False)
             self._ready = False
+            self.accelerator = None
+            if self._llm: self._llm.close()
             self._llm = None
             if not LLAMA_OK:
                 self.status_msg.emit("llama-cpp-python не установлен", False)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4325,6 +4491,9 @@

```diff
@@ -4325,6 +4491,9 @@
                         total_gib = mem.total / (1024 ** 3)
                         log.info("LLM memory check: model_file=%.2f GiB, RAM_total=%.2f GiB, RAM_available=%.2f GiB",
                                  model_gib, total_gib, available_gib)
+                        if model_gib + 1.25 > min(available_gib, 10.5 - psutil.Process().memory_info().rss/(1024**3)):
+                            self.status_msg.emit("Недостаточно ОЗУ: выберите меньшую квантизацию той же Gemma", False)
+                            return
                         if model_gib > available_gib * 0.85:
                             log.warning("GGUF is larger than currently available RAM. Windows may page model weights to disk; generation can take minutes. A smaller quant/model or more RAM is needed for a real speedup.")
                 except Exception as mem_exc:
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4348,9 +4517,9 @@

```diff
@@ -4348,9 +4517,9 @@
                 llama_kwargs = dict(model_path=path, n_ctx=int(CFG.get("n_ctx", 4096)),
                                     n_threads=int(CFG.get("n_threads", 2)),
                                     n_threads_batch=max(1, min(int(CFG.get("n_threads", 2)), 10)),
-                                    n_batch=(64 if CFG.get("low_ram_profile", False) else 128),
+                                    n_batch=(64 if CFG.get("low_ram_profile", False) else 256),
                                     n_ubatch=(32 if CFG.get("low_ram_profile", False) else 64),
-                                    n_gpu_layers=int(CFG.get("n_gpu_layers", 0)),
+                                    n_gpu_layers=0,
                                     use_mmap=True, use_mlock=False, verbose=False)
                 if chat_format and chat_format.casefold() not in ("auto", "default", "none"):
                     llama_kwargs["chat_format"] = chat_format
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4359,6 +4528,11 @@

```diff
@@ -4359,6 +4528,11 @@
                          llama_kwargs.get("n_threads_batch"), llama_kwargs.get("n_batch"),
                          llama_kwargs.get("n_ubatch"))
                 loaded = Llama(**llama_kwargs)
+                self.accelerator = None
+                if ACCEL_OK and CFG['accelerator_enabled']:
+                    self.accelerator = Accelerator(loaded,workspace(),llama_kwargs['n_ctx'],event_bus)
+                    PreWarm.run(loaded)
+                    self.accelerator.compact = CFG["context_manager_enabled"]
                 self._llm = loaded
                 self._ready = True
                 self.status_msg.emit("Модель готова ✓", True)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4367,11 +4541,16 @@

```diff
@@ -4367,11 +4541,16 @@
             except Exception as e:
                 self.status_msg.emit(f"Ошибка загрузки: {e}", False)
                 log.error(f"LLM load: {e}")
-        threading.Thread(target=_work, daemon=True).start()
+        def serialized_load():
+            with self._llm_lock: _work()
+        threading.Thread(target=serialized_load, daemon=True).start()
 
     def _chat(self, messages, max_tokens=512, temperature=0.7, top_p=0.9):
         if not self._llm:
             return ""
+        if getattr(self, 'accelerator', None):
+            priority = getattr(_CURRENT_REQUEST, 'llm_priority', 5)
+            return self.accelerator.generate(messages, priority, 'thought' if priority==20 and max_tokens<=56 else 'chat', max_tokens,temperature,top_p)
         kwargs = dict(messages=messages, max_tokens=max_tokens, temperature=temperature,
                       top_p=top_p, repeat_penalty=CFG.get("repeat_penalty", 1.1))
         started = time.monotonic()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4397,6 +4576,13 @@

```diff
@@ -4397,6 +4576,13 @@
         """Потоковая генерация: текст в UI и законченные фразы в Silero параллельно."""
         if not self._llm:
             return ""
+        if getattr(self,'accelerator',None):
+            self.stream_started.emit()
+            answer=self._chat(messages,max_tokens,temperature,top_p)
+            public=self._clean_public_answer(answer)
+            if emotion_engine and SAFETY_OK: public=SafetyLayer.filter(public,emotion_engine.values)
+            self.stream_delta.emit(public)
+            return answer
         kwargs = dict(messages=messages, max_tokens=max_tokens, temperature=temperature,
                       top_p=top_p, repeat_penalty=CFG.get("repeat_penalty", 1.1), stream=True)
         chunks = []
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -4803,6 +4989,7 @@

```diff
@@ -4803,6 +4989,7 @@
         if len(answer) < 2:
             answer = "Не удалось получить корректный ответ от модели. Проверь chat-template GGUF и журнал ошибок, затем повтори сообщение."
 
+        if emotion_engine and SAFETY_OK: answer=SafetyLayer.filter(answer,emotion_engine.values)
         short_mem.add(ctx_id, "user", f"[{username}]: {user_msg}")
         short_mem.add(ctx_id, "assistant", answer)
         self.response_ready.emit(answer)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5100,7 +5287,8 @@

```diff
@@ -5100,7 +5287,8 @@
                 continue
             if not self._app:
                 continue
-            chat_id = int(CFG.get("lively_group_chat_id", -1004412563438) or -1004412563438)
+            chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
+            if not chat_id or (proactive and not proactive.can_send()): continue
             quiet_seconds = max(5, int(CFG.get("lively_group_quiet_minutes", 15))) * 60
             last_activity = max(float(self._group_last_activity.get(chat_id, 0.0)), self._group_started_at)
             low = max(30, int(CFG.get("lively_group_proactive_min_minutes", 60)))
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5211,6 +5399,7 @@

```diff
@@ -5211,6 +5399,7 @@
             # request. У getUpdates отдельный HTTP-клиент, т.к. это long polling.
             normal_request = HTTPXRequest(
                 connection_pool_size=20,
+                httpx_kwargs={"trust_env":False},
                 connect_timeout=30.0,
                 read_timeout=90.0,
                 write_timeout=30.0,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5218,6 +5407,7 @@

```diff
@@ -5218,6 +5407,7 @@
             )
             polling_request = HTTPXRequest(
                 connection_pool_size=4,
+                httpx_kwargs={"trust_env":False},
                 connect_timeout=30.0,
                 read_timeout=50.0,
                 write_timeout=30.0,
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5225,12 +5415,15 @@

```diff
@@ -5225,12 +5415,15 @@
             )
             candidate = (
                 Application.builder()
+                .base_url(f"http://127.0.0.1:{int(CFG.get('telegram_local_api_port',8081))}/bot")
+                .base_file_url(f"http://127.0.0.1:{int(CFG.get('telegram_local_api_port',8081))}/file/bot")
                 .token(CFG["telegram_token"])
                 .request(normal_request)
                 .get_updates_request(polling_request)
                 .concurrent_updates(8)
                 .build()
             )
+            candidate.add_handler(CallbackQueryHandler(self._confirm_click,pattern=r"^tool:"))
             candidate.add_handler(CommandHandler("start", self._h_start))
             candidate.add_handler(CommandHandler("clear", self._h_clear))
             candidate.add_handler(CommandHandler("memory", self._h_memory))
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5475,7 +5668,7 @@

```diff
@@ -5475,7 +5668,7 @@
         new_mode = not bool(CFG.get("sleep_mode", False))
         agent.set_sleep_mode(new_mode)
         if new_mode:
-            chat_id = int(CFG.get("lively_group_chat_id", -1004412563438) or -1004412563438)
+            chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
             self._group_last_activity[chat_id] = time.time()
             self._group_started_at = time.time()
             await update.message.reply_text("🌙 Автономный режим включён вручную.")
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5487,7 +5680,7 @@

```diff
@@ -5487,7 +5680,7 @@
             await update.effective_message.reply_text("Эта команда доступна только создателю.")
             return
         agent.set_sleep_mode(True)
-        chat_id = int(CFG.get("lively_group_chat_id", -1004412563438) or -1004412563438)
+        chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
         self._group_last_activity[chat_id] = time.time()
         self._group_started_at = time.time()
         await update.effective_message.reply_text("🌙 Автономный режим включён вручную. Буду работать и иногда начинать разговор в группе после паузы.")
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5517,13 +5710,35 @@

```diff
@@ -5517,13 +5710,35 @@
         state = "включены" if CFG["telegram_video_notes"] else "выключены"
         await update.message.reply_text(f"Видеокружки с аватаром {state}.")
 
+    def confirm_tool(self, ctx, name, kwargs):
+        # Called by the request worker, not by the asyncio polling thread.
+        owner=int(CFG.get('telegram_owner_id') or 0)
+        if not owner or ctx != f'tg:{owner}' or not self._loop or not self._app: return False
+        async def ask():
+            import secrets
+            key=secrets.token_hex(12); pending=self.__dict__.setdefault('_approvals',{})
+            future=pending[key]=asyncio.get_running_loop().create_future()
+            try:
+                buttons=[[InlineKeyboardButton(label,callback_data=f'tool:{key}:{v}') for label,v in [('Разрешить',1),('Отказать',0)]]]
+                await self._app.bot.send_message(chat_id=owner,text=f'{name}: {kwargs}'[:3000],reply_markup=InlineKeyboardMarkup(buttons))
+                return await asyncio.wait_for(future,45)
+            finally: pending.pop(key,None)
+        task=asyncio.run_coroutine_threadsafe(ask(),self._loop)
+        try: return task.result(timeout=60)
+        except Exception: task.cancel(); return False
+
+    async def _confirm_click(self,update,_ctx):
+        q=update.callback_query; _,key,v=q.data.split(':'); pending=getattr(self,'_approvals',{}); f=pending.get(key)
+        if update.effective_user.id==int(CFG.get('telegram_owner_id') or 0) and f and not f.done(): f.set_result(v=='1')
+        await q.answer()
+
     async def _h_msg(self, update, _ctx):
         if not update.message or not update.effective_user: return
         u = update.effective_user
         text = (update.message.text or "").strip()
         chat = update.effective_chat
         if chat and chat.type != "private":
-            target_group = int(CFG.get("lively_group_chat_id", -1004412563438) or -1004412563438)
+            target_group = int(CFG.get("lively_group_chat_id", 0) or 0)
             if int(chat.id) == target_group:
                 self._group_last_activity[target_group] = time.time()
                 thread_id = getattr(update.effective_message, "message_thread_id", None)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -5572,7 +5787,7 @@

```diff
@@ -5572,7 +5787,7 @@
         was_idle = is_owner and (time.time() - creator_state.last_activity()) >= (
             max(1.0, float(CFG.get("autonomous_idle_minutes", 10)) * 60.0))
         if is_owner:
-            creator_state.set_active()
+            creator_state.set_active(user_message=True)
             agent.ping()
             if was_idle and agent._pending_discoveries:
                 summary = "Пока тебя не было, я занималась следующим:\n" + "\n".join(agent._pending_discoveries[-8:])
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6062,7 +6277,7 @@

```diff
@@ -6062,7 +6277,7 @@
         CFG["autonomous_enabled"] = checked
         save_config(CFG)
         agent.set_sleep_mode(checked)
-        chat_id = int(CFG.get("lively_group_chat_id", -1004412563438) or -1004412563438)
+        chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
         if checked:
             tg_bridge._group_last_activity[chat_id] = time.time()
             tg_bridge._group_started_at = time.time()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6071,7 +6286,7 @@

```diff
@@ -6071,7 +6286,7 @@
     def _open_log_folder(self):
         log_dir = personal_folder() / "журнал"
         if log_dir.exists():
-            subprocess.Popen(f'explorer "{log_dir}"', shell=True)
+            subprocess.Popen(["explorer", str(log_dir)])
 
     def _browse(self):
         p, _ = QFileDialog.getOpenFileName(self, "GGUF", "", "GGUF (*.gguf);;Все файлы (*.*)")
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6080,7 +6295,7 @@

```diff
@@ -6080,7 +6295,7 @@
     def _collect(self):
         CFG["ai_name"] = self.ai_name.text().strip() or "SCP-079-Derenguh"
         CFG["creator_name"] = self.creator.text().strip() or "Создатель"
-        CFG["tts_enabled"] = True
+        CFG.setdefault("tts_enabled", True)
         CFG["model_path"] = self.model_path.text().strip()
         CFG["n_ctx"] = self.n_ctx.value(); CFG["n_threads"] = self.n_threads.value()
         CFG["n_gpu_layers"] = self.n_gpu.value(); CFG["temperature"] = self.temp.value()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6153,7 +6368,7 @@

```diff
@@ -6153,7 +6368,7 @@
     def _open_log(self):
         log_dir = personal_folder() / "журнал"
         if log_dir.exists():
-            subprocess.Popen(f'explorer "{log_dir}"', shell=True)
+            subprocess.Popen(["explorer", str(log_dir)])
     def refresh(self):
         filter_type = self.filter_combo.currentText()
         today_file = personal_folder() / "журнал" / f"{datetime.datetime.now().strftime('%Y-%m-%d')}.md"
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6436,7 +6651,7 @@

```diff
@@ -6436,7 +6651,7 @@
         self.avatar_window = None
         if AVATAR_MODULE_OK:
             try:
-                self.avatar_window = CompanionAvatarWindow()
+                self.avatar_window = EnhancedAvatarWindow(emotion_engine, voice_engine) if AVATAR_V2_OK and CFG["avatar_enhanced"] else CompanionAvatarWindow()
                 avatar_path = str(CFG.get("avatar_project", "") or "").strip()
                 if avatar_path and Path(avatar_path).exists():
                     self.avatar_window.load_ai2d(avatar_path)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6653,7 +6868,7 @@

```diff
@@ -6653,7 +6868,7 @@
         save_config(CFG)
         agent.set_sleep_mode(checked)
         self.set_t.sleep_switch.setChecked(checked); self.sleep_btn.setChecked(checked)
-        chat_id = int(CFG.get("lively_group_chat_id", -1004412563438) or -1004412563438)
+        chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
         if checked:
             tg_bridge._group_last_activity[chat_id] = time.time()
             tg_bridge._group_started_at = time.time()
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6669,7 +6884,8 @@

```diff
@@ -6669,7 +6884,8 @@
 
     def _on_send(self, text):
         agent.ping()
-        creator_state.set_active()
+        creator_state.set_active(user_message=True)
+        if getattr(self.avatar_window,"animator",None): self.avatar_window.animator.address("?" in text)
         self.chat_t.append("Вы", text, "#7ec8e3")
         self.chat_t.busy(True)
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6766,7 +6982,7 @@

```diff
@@ -6766,7 +6982,7 @@
             return
         try:
             if self.avatar_window is None and AVATAR_MODULE_OK:
-                self.avatar_window = CompanionAvatarWindow()
+                self.avatar_window = EnhancedAvatarWindow(emotion_engine, voice_engine) if AVATAR_V2_OK and CFG["avatar_enhanced"] else CompanionAvatarWindow()
                 tts.speaking_changed.connect(self.avatar_window.set_speaking)
             if self.avatar_window is None:
                 detail = repr(_avatar_import_error) if _avatar_import_error else "причина не определена"
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6839,7 +7055,16 @@

```diff
@@ -6839,7 +7055,16 @@
     app = QApplication(sys.argv)
     app.setApplicationName("SCP-079-Derenguh")
     app.setFont(QFont("Segoe UI", 12))
+    if presence:
+        presence.on_app_start()
+        app.aboutToQuit.connect(presence.on_app_close)
     win = MainWindow()
+    global gui_gate
+    if CONFIRM_OK: gui_gate = GuiGate(win)
+    if TOOLS_EXTRA_OK and MEMORY_V2_OK:
+        win.reminder_clock = QTimer(win)
+        win.reminder_clock.timeout.connect(lambda: [win.chat_t.append('Напоминание',t,'#b39ddb') for t in due(tools_env)])
+        win.reminder_clock.start(1000)
     win.show()
 
     def _lively_message_callback(kind, text):
```

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -6848,6 +7073,7 @@

```diff
@@ -6848,6 +7073,7 @@
                 # Внутренние мысли и накопленные темы остаются в личном журнале.
                 return
             if kind in ("greeting", "question"):
+                if emotion_engine and SAFETY_OK: text=SafetyLayer.filter(text,emotion_engine.values)
                 if not (CFG.get("autonomous_enabled", False) and CFG.get("sleep_mode", False)):
                     return
                 win.lively_internal_message.emit(kind, text)
```

# ИЗМЕНЕНИЯ В AI_2D_Avatar_Studio_v5_3_integrated.py

Строки `-` относятся к приложенному оригиналу, `+` — к готовой версии. Номера и соседние строки задают место каждой вставки.

# ВСТАВИТЬ / ЗАМЕНИТЬ: @@ -413,6 +413,12 @@

```diff
@@ -413,6 +413,12 @@
         self.auto_timer.start(30)
         self._auto_clock = QElapsedTimer()
         self._auto_clock.start()
+
+    def set_emotion(self, name: str, weight: float):
+        self.emotion = (name, max(0., min(1., weight)))
+
+    def get_canvas(self):
+        return self.canvas
 
     def load_ai2d(self, path):
         """Загружает экспортированный проект .ai2d вместе с исходным изображением и ригом."""
```

# ТЕСТЫ

`python -m pytest -q tests`

# ФАЙЛ: tests/test_accelerator.py

# МЕСТО: FakeGGUF

```python
import sys
from types import SimpleNamespace
from scp_accelerator import Accelerator
from scp_event_bus import EventBus


class FakeGGUF:
    def tokenize(self, b, **kwargs):
        return list(b)

    def __call__(self, ids, **kw):
        assert kw["max_tokens"] == 48
        assert b"<start_of_turn>model" in bytes(ids)
        return iter([{"choices": [{"text": "Мысль."}]}])


def test_single_model_and_cache(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules, "llama_cpp", SimpleNamespace(StoppingCriteriaList=list)
    )
    bus = EventBus()
    a = Accelerator(FakeGGUF(), tmp_path, 3072, bus)
    msgs = [{"role": "user", "content": "Дневник"}]
    assert not a.generate(msgs, 20, "thought").cached
    assert a.generate(msgs, 20, "thought").cached
    assert bus.history(1)[0][0] == "cache_hit"
    assert len((tmp_path / "perf.jsonl").read_text().splitlines()) == 2
```

# ФАЙЛ: tests/test_compat.py

# МЕСТО: модуль целиком

```python
import importlib.util
import json
from pathlib import Path

import pytest

from scp_memory import LongTermMemory, MemoryConfig, MemoryMigrator, ShortTermMemory

ROOT = Path(__file__).resolve().parents[1]


def test_migration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "session_memory.json"
    p.write_text(json.dumps({"local": [dict(role="user", content="Привет", time=12)]}))
    (tmp_path / "aria_long_memory.json").write_text('["факт"]', "utf8")
    m = MemoryMigrator()
    m.migrate_from_v4_once(tmp_path)
    m.migrate_from_v4_once(tmp_path)
    assert p.with_suffix(".migrated.bak").exists()
    assert (
        ShortTermMemory(MemoryConfig(tmp_path, {})).get_hot("local")[0]["text"]
        == "Привет"
    )
    assert len(LongTermMemory(tmp_path).query("факт")) == 1


def test_v4_wrappers(tmp_path, monkeypatch):
    pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "andrea_v4", next(ROOT.glob("SCP-*.py"))
    )
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    memory = app.SessionMemory()
    memory.add("local", "user", "проверка")
    assert memory.get_context("local")[-1]["content"] == "проверка"
    memory.clear("local")
    assert memory.get("local") == []
    e = app.EmotionalModel()
    e.update("trust", 0.1)
    e.cool()
    assert "trust" in e.get_state() and "чувствуешь" in e.apply_to_prompt("стиль")
    m = app.CreatorMemory()
    m.add_fact("я люблю лис")
    assert "лис" in m.context()


def test_rotation_and_isolation(tmp_path):
    store = ShortTermMemory(
        MemoryConfig(tmp_path, {"short_memory_max_mb_per_ctx": 0.004})
    )
    for i in range(100):
        store.add("tg:1", "user", f"{i} " + "Ю" * 90)
    rows = store.get_window("tg:1", 40)
    assert [r["text"].partition(" ")[0] for r in rows] == list(map(str, range(60, 100)))
    assert not store.get_hot("tg:2")


def test_invalid_migration_preserves_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = tmp_path / "session_memory.json"
    session.write_text("{}")
    (tmp_path / "creator_memory.json").write_text("[]")
    with pytest.raises(ValueError):
        MemoryMigrator().migrate_from_v4_once(tmp_path)
    assert session.exists() and not session.with_suffix(".migrated.bak").exists()


def test_ttl_excludes_creator(tmp_path):
    import os, time

    store = ShortTermMemory(MemoryConfig(tmp_path, {"telegram_owner_id": 42}))
    old = time.time() - 80 * 3600
    for ctx in ("local", "tg:42", "tg:7"):
        store.add(ctx, "user", "сообщение")
        os.utime(store.path(ctx), (old, old))
    store.gc_expired()
    assert (
        store.get_hot("local") and store.get_hot("tg:42") and not store.get_hot("tg:7")
    )
```

# ФАЙЛ: tests/test_context_budget.py

# МЕСТО: модуль целиком

```python
import pytest

from scp_context_manager import ContextManager


def test_budget(tmp_path):
    c = ContextManager(3072, tmp_path)
    turns = [
        (f"Вопрос {i}: " + "а" * 350, f"Ответ {i}: " + "б" * 300) for i in range(40)
    ]
    prompt = c.build_prompt(
        "СИСТЕМА",
        "ЭМОЦИИ",
        "ПРОФИЛЬ",
        turns,
        ["саммари" * 2000],
        ["факт" * 2000],
        512,
        "почему?",
    )
    assert (len(prompt) + 2) // 3 <= 3072 - 512 - 32
    assert all(
        x in prompt
        for x in ["СИСТЕМА", "ЭМОЦИИ", "ПРОФИЛЬ", "почему?", *turns[-1], *turns[-2]]
    )
    with pytest.raises(ValueError):
        c.build_prompt("x" * 10000, "", "", [], [], [], 512)


def test_summary_reused(tmp_path):
    msgs = [
        {"role": r, "content": f"{i}{r}"}
        for i in range(20)
        for r in ("user", "assistant")
    ] + [{"role": "user", "content": "сейчас"}]
    calls = []
    for _ in range(2):
        out = ContextManager(3072, tmp_path).prepare(
            msgs, 160, lambda p: calls.append(p) or "краткий итог"
        )
        assert "краткий итог" in out
    assert len(calls) == 1


def test_cold_keeps_fact_not_transcript():
    messages = []
    for i in range(30):
        messages.extend(
            [
                {
                    "role": "user",
                    "content": "запомни: любимый цвет синий." if not i else f"Тема {i}",
                },
                {"role": "assistant", "content": f"старая-реплика-{i}!"},
            ]
        )
    messages.append({"role": "user", "content": "что помнишь?"})
    prompt = ContextManager().prepare(messages, 96)
    assert "любимый цвет синий" in prompt and "старая-реплика-0!" not in prompt
```

# ФАЙЛ: tests/test_dedup.py

# МЕСТО: модуль целиком

```python
from scp_autonomy import ThoughtDeduplicator


def test_ten_thoughts(tmp_path):
    d = ThoughtDeduplicator(tmp_path)
    for i in range(10):
        text = f"Тема {i}: музыка звучит иначе {i}"
        assert not d.is_duplicate(text)
        d.remember(text)
        assert d.is_duplicate(text.upper() + "!")
    assert ThoughtDeduplicator(tmp_path).is_duplicate(text)
```

# ФАЙЛ: tests/test_emotion_events.py

# МЕСТО: модуль целиком

```python
from scp_emotion_engine import EmotionEngine
from scp_event_bus import EventBus


def test_events(tmp_path):
    bus = EventBus()
    e = EmotionEngine(tmp_path, bus)
    start = e.values.copy()
    bus.emit("tool_failure")
    assert (
        e.values["frustration"] > start["frustration"]
        and e.values["joy"] < start["joy"]
    )
    before = e.values.copy()
    e.apply_event("user_returned", after_days=3)
    assert (
        e.values["bittersweet"] > 0.5
        and e.values["resentment"] < before["resentment"]
        and e.values["joy"] > before["joy"]
    )
    e.cool(3600)
    assert e.baselines["joy"] < e.values["joy"] < 1
```

# ФАЙЛ: tests/test_presence_stages.py

# МЕСТО: модуль целиком

```python
from datetime import datetime

import pytest

from scp_autonomy import ProactiveScheduler
from scp_emotion_engine import EmotionEngine
from scp_event_bus import EventBus
from scp_presence import PresenceTracker
from scp_storage import save


@pytest.mark.parametrize(
    "hours,kind", [(5, "4h"), (10, "8h"), (24, "24h"), (48, "48h"), (72, "72h")]
)
def test_stages(tmp_path, hours, kind):
    now = datetime(2026, 1, 15, 12).timestamp()
    save(tmp_path / "presence.json", {"last_user_message_at": now - hours * 3600})
    bus = EventBus()
    emotions = EmotionEngine(tmp_path, bus)
    before = emotions.describe_for_prompt()
    p = PresenceTracker(tmp_path, bus, lambda: now)
    p.tick()
    scheduler = ProactiveScheduler(
        dict(
            proactive_enabled=True,
            proactive_quiet_hours="23:00-08:00",
            proactive_min_gap_minutes=240,
            proactive_daily_limit=4,
        ),
        p,
    )
    assert scheduler.maybe_send()[0] == kind
    assert scheduler.maybe_send() is None
    p.on_user_message()
    assert p.bucket() == "none" and emotions.describe_for_prompt() != before
```

# ФАЙЛ: tests/test_safety.py

# МЕСТО: модуль целиком

```python
import pytest

from scp_safety import SafetyLayer
from scp_tools_extra import python_exec


def test_reconciliation():
    assert (
        SafetyLayer.filter("Ты должен. Я уйду, удалю себя.", {"resentment": 0.9})
        == "Я расстроена, но хочу поговорить."
    )


def test_arithmetic_only():
    assert python_exec(None, "x=12\nx/2") == "6.0"
    with pytest.raises(ValueError):
        python_exec(None, "import pathlib")
```

# ЧЕК-ЛИСТ

- [ ] Исходные файлы данных скопированы отдельно. В `workspace` нет конфликтующих `.migrated.bak` от прерванной миграции.
- [ ] `model_path` указывает на свой файл Gemma, GGUF не скачивается приложением.
- [ ] В первой проверке `web_enabled=false`, Telegram не запущен.
- [ ] Восстановлены факты и диалоги, видны `.migrated.bak`.
- [ ] В `perf.jsonl` появляется замер после реальной генерации; проверен пиковый RSS на своей машине.
- [ ] Указаны локальный голос и `.ai2d` с ригом.
- [ ] Отказ в диалоге подтверждения не исполняет инструмент.
- [ ] При закрытой автономности инициативные сообщения не отправляются.

