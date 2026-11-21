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
