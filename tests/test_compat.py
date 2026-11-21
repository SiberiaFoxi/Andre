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
