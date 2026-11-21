"""Additional local v4 tools and owner-confirmation helpers."""

from scp_diagnostics import measured

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

    @measured('tools_extra')
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
