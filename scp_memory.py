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
