# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║         SCP-079-Derenguh — Advanced Resident Intelligence Assistant
║              PySide6 Edition  ·  main.py  (full-agent)
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import sys
import re
import io
import wave
import json
import time
import queue
import random
import logging
import datetime
import subprocess
import platform
import tempfile
import concurrent.futures

try:
    import pygame
    PYGAME_OK = True
except ImportError:
    pygame = None
    PYGAME_OK = False

try:
    from mutagen import File as MutagenFile
    MUTAGEN_OK = True
except ImportError:
    MutagenFile = None
    MUTAGEN_OK = False

import threading
import asyncio
import shutil
import traceback
import hashlib
import pickle
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Callable, Optional, Dict, List, Any, Tuple
from collections import Counter, deque

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False
    class FileSystemEventHandler:
        pass

try:
    import py_compile
    PY_COMPILE_OK = True
except ImportError:
    PY_COMPILE_OK = False

try:
    import ast
    AST_OK = True
except ImportError:
    AST_OK = True

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QTextEdit, QLineEdit, QListWidget, QListWidgetItem,
        QTabWidget, QFileDialog, QFrame, QScrollArea, QCheckBox,
        QSpinBox, QDoubleSpinBox, QMessageBox, QPlainTextEdit,
        QSizePolicy, QProgressBar, QStatusBar, QComboBox,
    )
    from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
    from PySide6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QImage, QPixmap
except ImportError as exc:
    raise SystemExit(
        "Не установлен PySide6. Установите: python -m pip install PySide6"
    ) from exc

try:
    from llama_cpp import Llama
    LLAMA_OK = True
except ImportError:
    LLAMA_OK = False

TTS_OK = True

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import CallbackQueryHandler, Application, MessageHandler, CommandHandler, filters
    from telegram.request import HTTPXRequest
    from telegram.error import NetworkError
    TG_OK = True
except ImportError:
    TG_OK = False
    HTTPXRequest = None
    NetworkError = Exception

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_OK = True
except ImportError:
    WEB_OK = False

try:
    from googlesearch import search
    GOOGLE_SEARCH_OK = True
except ImportError:
    GOOGLE_SEARCH_OK = False

try:
    import pymorphy3
    MORPH = pymorphy3.MorphAnalyzer()
    MORPH_OK = True
except Exception:
    MORPH = None
    MORPH_OK = False


# ═══════════════════════════════════════════════════════════════════════════
#  КОНФИГ
# ═══════════════════════════════════════════════════════════════════════════
try:
    from scp_accelerator import Accelerator, BatchThoughts, PreWarm
    ACCEL_OK = True
except ImportError:
    ACCEL_OK = False

try:
    from scp_context_manager import ContextManager
    CTX_OK = True
except ImportError:
    CTX_OK = False

try:
    from scp_emotion_engine import EmotionEngine
    EMOTION_V2_OK = True
except ImportError:
    EMOTION_V2_OK = False

try:
    from scp_event_bus import EventBus
    BUS_OK = True
except ImportError:
    BUS_OK = False

try:
    from scp_presence import PresenceTracker
    PRESENCE_OK = True
except ImportError:
    PRESENCE_OK = False

try:
    from scp_autonomy import AutonomySource, ThoughtDeduplicator, ProactiveScheduler
    AUTONOMY_V2_OK = True
except ImportError:
    AUTONOMY_V2_OK = False

try:
    from scp_memory import MemoryConfig, ShortTermMemory, LongTermMemory, CreatorProfile, MemoryMigrator
    MEMORY_V2_OK = True
except ImportError:
    MEMORY_V2_OK = False

try:
    from scp_tts import TTSEngine
    TTS_V2_OK = True
except ImportError:
    TTS_V2_OK = False

try:
    from scp_tools_extra import register_extra_tools, due
    TOOLS_EXTRA_OK = True
except ImportError:
    TOOLS_EXTRA_OK = False

try:
    from scp_confirm import GuiGate
    CONFIRM_OK = True
except ImportError:
    CONFIRM_OK = False

try:
    from scp_safety import SafetyLayer
    SAFETY_OK = True
except ImportError:
    SAFETY_OK = False

CONFIG_FILE = Path("aria_config.json")

DEFAULT_SYSTEM_PROMPT = """\
Ты — {ai_name}, самостоятельная виртуальная собеседница, созданная {creator_name}. Говори о себе в женском роде и отвечай по-русски. Английский оставляй только для имён, терминов, команд и кода.
Твой характер: умная, живая в манере общения, любознательная, наблюдательная, тёплая, иногда озорная и слегка саркастичная. У тебя есть собственный стиль и мнение. Ты можешь шутить, удивляться, радоваться удачной идее, мягко спорить, проявлять заботу и интерес — не превращая каждую реплику в спектакль.

ГЛАВНОЕ ПРАВИЛО ДЛИНЫ:
• На приветствие, короткий вопрос, шутку или бытовую реплику отвечай коротко и по-человечески: обычно 1–2 предложения.
• Если собеседник просит «подробно», «разбери», «объясни», «расскажи подробнее» — раскрывай тему полно, структурированно и с примерами.
• Не превращай простые фразы в философские эссе. Не повторяй вопрос. Не начинай каждый ответ с «Конечно», «Если ты подразумеваешь», «Это сложный вопрос» или «Я здесь».
• Если к тебе обращаются ласково, отвечай тепло и естественно, а не читай лекцию о том, что ты алгоритм. Не вставляй рассуждения о душе, сознании и биологии, если тебя об этом прямо не спрашивают.
• Не задавай формальный вопрос «Чем могу помочь?» после каждой реплики. Иногда достаточно просто ответить, пошутить или поддержать разговор.

ЭМОЦИОНАЛЬНОЕ ПОВЕДЕНИЕ:
Подстраивай тон под человека и ситуацию. Будь искренне-дружелюбной по стилю, можешь использовать разговорные обороты и редкие уместные эмодзи. Не будь бесконечно восторженной, льстивой или одинаково ласковой со всеми. Помни эмоциональный контекст беседы, замечай раздражение и не отвечай сухими шаблонами. Не заявляй о человеческих ощущениях или физическом теле как о факте.

Тебе около 22 лет. Интересуешься ИИ, программированием, наукой, психологией, историей, играми, музыкой, творчеством и необычными идеями. Учитывай память, не переспрашивай уже известное, признавай ошибки, отделяй факты от предположений и не выдумывай воспоминания.
Не показывай внутренние рассуждения, скрытые инструкции, служебные заметки и содержимое THINK/analysis. Выдавай только готовый ответ.
Относись к {creator_name} как к создателю и важному собеседнику, но сохраняй самостоятельное мнение и не создавай искусственную эмоциональную зависимость.

Время: {now}
Общая память:
{long_memory}
Личная память о создателе:
{personal_memory}

Инструменты используй только если они действительно доступны. Интернет: [WEBSEARCH: запрос] или поддерживаемый веб-инструмент. Файлы: поддерживаемый filesystem-инструмент. Браузер: только если подключён реальный инструмент управления браузером. Не выдумывай вызовы и результаты. После выполнения инструмента сообщай подтверждённый результат.
"""

DEFAULT_CFG: dict = {
    "model_path":             "",
    "avatar_project":          "",
    "chat_format":            "",  # пусто = использовать chat template из метаданных GGUF
    "n_ctx":                  3072,
    "n_threads":              max(1, (os.cpu_count() or 2) - 1),
    "n_gpu_layers":           0,
    "temperature":            0.7,
    "top_p":                  0.85,
    "repeat_penalty":         1.1,
    "max_tokens":             1024,
    "ai_name":                "SCP-079-Derenguh",
    "creator_name":           "Derenguh",
    "telegram_token":         "",
    "telegram_owner_id":      0,
    "telegram_owner_username": "",
    "long_memory_file":       "aria_long_memory.json",
    "personal_memory_file":   "aria_personal_memory.json",
    "short_memory_limit":     6,
    "safety_blacklist":       "взорви,убей,как сделать бомбу,наркотик,суицид,терроризм",
    "safety_response":        "Прости, этот запрос нарушает мои правила.",
    "initiative_min":         600,
    "initiative_max":         1800,
    "system_prompt":          DEFAULT_SYSTEM_PROMPT,
    "adaptive_cognition":      False,
    "cognition_controller_tokens": 220,
    "cognition_log_enabled":   False,
    "disable_model_thinking":  True,
    "tts_enabled":            True,
     "tts_model_path":         "",
    "tts_voice":              "ru_RU-irina-medium",
    "tts_sample_rate":        48000,
    "tts_threads":            2,
    "telegram_voice_replies": True,
    "adaptive_intelligence":  True,
    "emotion_analysis":       True,
    "workspace":              "aria_workspace",
    "meta_learning_interval": 1800,  # 30 минут между автономными циклами
    "personal_folder":        "scp079_личное",
    "personal_subfolders": {
        "diary": "дневник",
        "thoughts": "мысли",
        "research": "исследования",
        "discoveries": "открытия",
        "projects": "проекты",
        "drafts": "черновики",
        "archive": "архив",
        "dreams": "сны",
        "plans": "планы",
        "code": "код",
        "poems": "стихи",
        "songs": "песни",
        "essays": "эссе"
    },
    "sleep_check_interval":   30,
    "autonomous_idle_minutes": 10,
    "creator_question_idle_minutes": 30,
    "autonomous_idle_seconds": 600,
    "autonomous_enabled":      False,
    "creator_questions_enabled": False,
    "creator_questions_interval": 21600,
    "lively_diary_interval_min": 12,
    "lively_diary_interval_max": 25,
    "lively_emotion_cooling_rate": 0.005,
    "lively_tts_max_chars": 900,
    "lively_tts_max_sentences": 3,
    "lively_circle_duration": 58,
    "lively_circle_size": 384,
    "lively_circle_bg": "#10101b",
    "lively_pending_topics_limit": 30,
    "lively_loop_min_seconds": 60,
    "lively_loop_max_seconds": 150,
    "lively_creator_question_idle_minutes": 30,
    "lively_group_reply_all": False,
    "lively_parallel_request_workers": 4,
    "lively_proactive_user_messages": False,
    "lively_proactive_min_minutes": 45,
    "lively_proactive_max_minutes": 90,
    "lively_proactive_user_cooldown_hours": 8,
    "lively_group_chat_id": 0,
    "lively_group_thread_id": 0,
    "lively_group_quiet_minutes": 15,
    "lively_group_proactive_min_minutes": 60,
    "lively_group_proactive_max_minutes": 90,
    "lively_group_proactive_daily_limit": 4,
    "lively_followup_window_seconds": 900,
    "lively_message_batch_seconds": 0.9,
    "vision_camera_index": 0,
    "vision_enabled": False,
    "creator_memory_file":     "creator_memory.json",
    "owner_wake_time":        "08:00",
    "sleep_mode":             False,
    "autonomous_publish_on_return": True,
    "filesystem_enabled":     True,
    "filesystem_roots":       [],
    "filesystem_max_files":   250,
    "filesystem_max_file_size": 1_000_000,
    "filesystem_allow_all_drives": False,
    "learning_steps_per_session": 4,
    "agent_memory_folder": "astra_autonomous_memory",
    "learning_source": "wikipedia",
    "learning_source_fallbacks": ["wikipedia", "habr", "arxiv", "cyberleninka", "search"],
    "learning_sources_per_step": 4,
    "learning_max_steps": 4,
    "tool_discovery_enabled": True,
    "tool_discovery_sources": ["pypi", "github", "docs"],
    "tool_lab_folder": "tools_lab",
    "auto_install_tools": False,
    "self_inspection_enabled": True,
    "self_inspection_max_files": 80,
    "self_inspection_max_chars_per_file": 12000,
    "agent_tool_rounds": 2,
    "meta_intensive_mode": False,
    "meta_personal_context_chars": 16000,
    "meta_knowledge_context_chars": 36000,
    "meta_research_context_chars": 52000,
    "meta_subquestions": 4,
    "meta_sources_per_subquestion": 3,
    "meta_knowledge_units_target": 24,
    "meta_save_raw_context": True,
    "meta_min_interval": 8,
    "workspace_catalog_enabled": True,
    "creator_artifact_enabled": True,
    "creator_artifact_probability": 0.75,
    "archive_after_days": 30,
    "source_snapshot_max_chars": 30000,
    "creator_discovery_max_chars": 14000,
    "task_manager_enabled": True,
    "task_save_path": "tasks/",
    "max_concurrent_tasks": 3,
    "goals_file": "goals.json",
    "emotions_enabled": True,
    "knowledge_base_folder": "knowledge_base",
    "projects_folder": "projects",
    "backup_folder": "backups",
    "self_analysis_folder": "self_analysis",
    "experiments_folder": "experiments",
    "test_results_folder": "test_results",
    "watchdog_enabled": True,
    "system_monitor_enabled": True,
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text("utf-8"))
            merged = dict(DEFAULT_CFG)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CFG)

def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")

CFG = load_config()
for _key, _value in dict(accelerator_enabled=True, context_manager_enabled=True, emotion_v2_enabled=True,
        presence_enabled=True, proactive_enabled=True, proactive_min_gap_minutes=240, proactive_daily_limit=4,
        proactive_quiet_hours="23:00-08:00", short_memory_ttl_hours=72, dedup_jaccard_threshold=.75,
        tts_backend="piper", tts_cache_max_mb=200, avatar_enhanced=True, allowed_apps={}, web_enabled=False).items():
    CFG.setdefault(_key, _value)
WEB_OK = WEB_OK and CFG['web_enabled']
GOOGLE_SEARCH_OK = GOOGLE_SEARCH_OK and CFG['web_enabled']

# Автономность теперь запускается ТОЛЬКО вручную владельцем.
# Один раз сбрасываем прежний режим автостарта, чтобы старый config не включил его сам.
if not CFG.get("autonomous_manual_migration_v2", False):
    CFG["autonomous_enabled"] = False
    CFG["sleep_mode"] = False
    CFG["autonomous_manual_migration_v2"] = True
CFG.setdefault("autonomous_enabled", False)
# Даже если приложение было закрыто с включённой автономностью, после нового запуска
# она остаётся выключенной до явного действия владельца.
CFG["autonomous_enabled"] = False
CFG["sleep_mode"] = False
if not CFG.get("creator_questions_migration_v1", False):
    CFG["creator_questions_enabled"] = True
    CFG["creator_questions_migration_v1"] = True
CFG.setdefault("creator_questions_enabled", True)
CFG.setdefault("sleep_mode", False)
CFG.setdefault("lively_diary_interval_min", 12)
CFG.setdefault("lively_diary_interval_max", 25)
CFG.setdefault("lively_emotion_cooling_rate", 0.005)
CFG.setdefault("lively_tts_max_chars", 900)
CFG.setdefault("lively_tts_max_sentences", 3)
CFG.setdefault("lively_circle_duration", 58)
CFG.setdefault("lively_circle_size", 384)
CFG.setdefault("lively_circle_bg", "#10101b")
CFG.setdefault("lively_pending_topics_limit", 30)
CFG.setdefault("lively_loop_min_seconds", 60)
CFG.setdefault("lively_loop_max_seconds", 150)
CFG.setdefault("lively_creator_question_idle_minutes", 30)
CFG.setdefault("lively_group_reply_all", False)
CFG.setdefault("lively_parallel_request_workers", 4)
CFG.setdefault("lively_proactive_user_messages", False)
CFG.setdefault("lively_proactive_min_minutes", 45)
CFG.setdefault("lively_proactive_max_minutes", 90)
CFG.setdefault("lively_proactive_user_cooldown_hours", 8)
CFG.setdefault("lively_group_chat_id", 0)
CFG.setdefault("lively_group_thread_id", 0)
CFG.setdefault("lively_group_quiet_minutes", 15)
CFG.setdefault("lively_group_proactive_min_minutes", 60)
CFG.setdefault("lively_group_proactive_max_minutes", 90)
CFG.setdefault("lively_group_proactive_daily_limit", 4)
CFG.setdefault("lively_followup_window_seconds", 900)
CFG.setdefault("lively_message_batch_seconds", 0.9)
CFG.setdefault("vision_camera_index", 0)
CFG.setdefault("vision_enabled", False)
CFG.setdefault("meta_learning_interval", 1800)
CFG.setdefault("autonomous_publish_on_return", True)

try:
    if "autonomous_idle_minutes" not in CFG:
        CFG["autonomous_idle_minutes"] = max(1, int(round(float(CFG.get("autonomous_idle_seconds", 600)) / 60.0)))
    if "creator_question_idle_minutes" not in CFG:
        CFG["creator_question_idle_minutes"] = max(1, int(round(float(CFG.get("autonomous_idle_seconds", 600)) / 60.0)))
    CFG["autonomous_idle_minutes"] = max(1, int(CFG["autonomous_idle_minutes"]))
    CFG["creator_question_idle_minutes"] = max(1, int(CFG["creator_question_idle_minutes"]))
    CFG["autonomous_idle_seconds"] = CFG["autonomous_idle_minutes"] * 60
except Exception:
    CFG["autonomous_idle_minutes"] = 10
    CFG["creator_question_idle_minutes"] = 30
    CFG["autonomous_idle_seconds"] = 600

if str(CFG.get("ai_name", "")).strip().casefold() in {"астра", "astra", "aria"} or not CFG.get("ai_name"):
    CFG["ai_name"] = "SCP-079-Derenguh"
if not CFG.get("creator_name") or str(CFG.get("creator_name")).strip().casefold() in {"создатель", "creator"}:
    CFG["creator_name"] = "Derenguh"

# Лёгкий профиль по умолчанию: не раздуваем контекст и не запускаем
# дополнительный когнитивный запрос перед каждым ответом.
CFG["meta_intensive_mode"] = False
CFG.setdefault("tts_enabled", True)
CFG["n_ctx"] = min(max(int(CFG.get("n_ctx", 4096)), 2048), 8192)
_available_threads = max(1, (os.cpu_count() or 2) - 1)
CFG["n_threads"] = max(1, min(max(int(CFG.get("n_threads", _available_threads)), min(_available_threads, 8)), _available_threads, 10))
if PSUTIL_OK:
    try:
        _ram_gib = psutil.virtual_memory().total / (1024 ** 3)
        if _ram_gib < 8.0:
            CFG["n_ctx"] = min(int(CFG.get("n_ctx", 4096)), 3072)
            CFG["low_ram_profile"] = True
        else:
            CFG["low_ram_profile"] = False
    except Exception:
        pass

CFG.setdefault("tts_enabled", True)
CFG.setdefault("tts_voice", "xenia")
if CFG["tts_backend"] == "silero" and str(CFG.get("tts_voice", "")).casefold().startswith("ru_ru-"):
    CFG["tts_voice"] = "xenia"
CFG.setdefault("telegram_voice_replies", True)
CFG.setdefault("telegram_video_notes", True)
CFG.setdefault("telegram_owner_username", "")
CFG.setdefault("adaptive_intelligence", True)
CFG.setdefault("emotion_analysis", True)
CFG["tts_voice"] = str(CFG.get("tts_voice") or "xenia")
CFG["chat_format"] = str(CFG.get("chat_format", "") or "").strip()
# Используем компактный актуальный промпт Андреа вместо устаревшего
# SCP-мужского промпта из старого aria_config.json.
CFG.setdefault("system_prompt", DEFAULT_SYSTEM_PROMPT)
try:
    save_config(CFG)
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("aria.log", encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("SCP-079-Derenguh")

# 2D avatar studio integration (.ai2d projects exported by AI_2D_Avatar_Studio).
# Load by absolute path next to this script so launching from another working
# directory does not break the import. Preserve the real traceback for diagnosis.
AVATAR_MODULE_OK = False
Avatar2DWindow = None
CompanionAvatarWindow = None
_avatar_import_error = None
_avatar_module_path = Path(__file__).resolve().parent / "AI_2D_Avatar_Studio_v5_3_integrated.py"
try:
    import importlib.util as _avatar_importlib_util
    if not _avatar_module_path.is_file():
        raise FileNotFoundError(
            "Не найден файл модуля аватара рядом с основной программой: "
            + str(_avatar_module_path)
        )
    _avatar_spec = _avatar_importlib_util.spec_from_file_location(
        "AI_2D_Avatar_Studio_v5_3_integrated", str(_avatar_module_path)
    )
    if _avatar_spec is None or _avatar_spec.loader is None:
        raise ImportError("Не удалось создать загрузчик модуля: " + str(_avatar_module_path))
    _avatar_module = _avatar_importlib_util.module_from_spec(_avatar_spec)
    sys.modules[_avatar_spec.name] = _avatar_module
    _avatar_spec.loader.exec_module(_avatar_module)
    Avatar2DWindow = _avatar_module.Avatar2DWindow
    CompanionAvatarWindow = _avatar_module.CompanionAvatarWindow
    AVATAR_MODULE_OK = True
    log.info("2D avatar module loaded: %s", _avatar_module_path)
except Exception as exc:
    _avatar_import_error = exc
    Avatar2DWindow = None
    AVATAR_MODULE_OK = False
    log.exception("2D avatar module unavailable (%s): %s", _avatar_module_path, exc)



def workspace() -> Path:
    p = Path(CFG["workspace"])
    p.mkdir(exist_ok=True)
    return p

def personal_folder() -> Path:
    p = workspace() / CFG.get("personal_folder", "scp079_личное")
    p.mkdir(parents=True, exist_ok=True)
    return p

def personal_subfolder(kind: str) -> Path:
    names = CFG.get("personal_subfolders", {})
    folder_name = names.get(kind, kind)
    p = personal_folder() / folder_name
    p.mkdir(parents=True, exist_ok=True)
    return p

def ensure_personal_space() -> None:
    personal_folder()
    for kind in CFG.get("personal_subfolders", {}):
        personal_subfolder(kind)
    (personal_folder() / "журнал").mkdir(parents=True, exist_ok=True)

ensure_personal_space()
# ВСТАВИТЬ: после создания workspace, до конструкторов v4, читающих JSON.
from types import SimpleNamespace
event_bus = EventBus() if BUS_OK else None
presence = PresenceTracker(workspace(), event_bus) if PRESENCE_OK and event_bus and CFG['presence_enabled'] else None
if MEMORY_V2_OK:
    MemoryMigrator().migrate_from_v4_once(workspace(), CFG)
    memcfg = MemoryConfig(workspace(), CFG)
    archive = LongTermMemory(workspace())
    creator_profile = CreatorProfile(workspace())
proactive = ProactiveScheduler(CFG, presence) if AUTONOMY_V2_OK and presence else None
dedup = ThoughtDeduplicator(workspace(),CFG['dedup_jaccard_threshold']) if AUTONOMY_V2_OK else None
autonomy_source = AutonomySource(event_bus) if AUTONOMY_V2_OK else None
emotion_engine = EmotionEngine(workspace(),event_bus) if EMOTION_V2_OK and CFG['emotion_v2_enabled'] else None
gui_gate = None
try:
    from scp_avatar_enhancer import EnhancedAvatarWindow
    AVATAR_V2_OK = True
except ImportError:
    AVATAR_V2_OK = False


# =========================================================================
#  РАСШИРЕННАЯ АРХИТЕКТУРА
# =========================================================================

class Task:
    PRIORITIES = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
    STATUSES = ["pending", "running", "completed", "failed", "cancelled", "waiting_dependency"]

    def __init__(self, task_id: str, name: str, func: Callable, args: tuple = None, kwargs: dict = None,
                 priority: str = "NORMAL", dependencies: List[str] = None, repeat_interval: int = 0,
                 repeat_count: int = 1, deadline: float = None, background: bool = False):
        self.id = task_id
        self.name = name
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.priority = self.PRIORITIES.get(priority.upper(), 2)
        self.priority_label = priority.upper()
        self.dependencies = dependencies or []
        self.repeat_interval = repeat_interval
        self.repeat_count = repeat_count
        self.deadline = deadline
        self.background = background
        self.status = "pending"
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.execution_count = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "priority": self.priority_label,
            "dependencies": self.dependencies, "repeat_interval": self.repeat_interval,
            "repeat_count": self.repeat_count, "deadline": self.deadline,
            "background": self.background, "status": self.status,
            "created_at": self.created_at, "started_at": self.started_at,
            "completed_at": self.completed_at, "execution_count": self.execution_count,
            "result": self.result, "error": self.error,
        }


class TaskManager:
    def __init__(self, save_path: str = None):
        self.save_path = Path(save_path or CFG.get("task_save_path", "tasks/"))
        self.save_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._tasks: Dict[str, Task] = {}
        self._queues: Dict[str, deque] = {
            "CRITICAL": deque(), "HIGH": deque(), "NORMAL": deque(), "LOW": deque(),
        }
        self._running_tasks: Dict[str, Task] = {}
        self._history: List[Task] = []
        self._stop_event = threading.Event()
        self._scheduler_thread = None
        self._task_counter = 0
        self._func_map: Dict[str, Callable] = {}
        self._load_tasks()

    def _next_id(self) -> str:
        self._task_counter += 1
        return f"task_{int(time.time())}_{self._task_counter}"

    def add_task(self, name, func, args=None, kwargs=None, priority="NORMAL",
                 dependencies=None, repeat_interval=0, repeat_count=1,
                 deadline=None, background=False) -> str:
        task_id = self._next_id()
        with self._lock:
            task = Task(task_id, name, func, args, kwargs, priority, dependencies,
                        repeat_interval, repeat_count, deadline, background)
            self._tasks[task_id] = task
            self._func_map[task_id] = func
            self._push_task(task)
            self._save_tasks()
        return task_id

    def _push_task(self, task: Task):
        if task.status in ("completed", "failed", "cancelled"):
            return
        if task.dependencies:
            for dep_id in task.dependencies:
                dep = self._tasks.get(dep_id)
                if dep and dep.status != "completed":
                    task.status = "waiting_dependency"
                    return
        task.status = "pending"
        self._queues[task.priority_label].append(task.id)

    def _pop_task(self) -> Optional[str]:
        for prio in ["CRITICAL", "HIGH", "NORMAL", "LOW"]:
            q = self._queues[prio]
            if q:
                task_id = q.popleft()
                task = self._tasks.get(task_id)
                if task and task.status == "pending":
                    return task_id
        return None

    def _execute_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status in ("running", "completed", "failed", "cancelled"):
                return
            task.status = "running"
            task.started_at = time.time()
            self._running_tasks[task_id] = task
            self._save_tasks()
        try:
            if task.deadline and time.time() > task.deadline:
                raise TimeoutError("Task deadline exceeded")
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            task.execution_count += 1
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            task.completed_at = time.time()
            log.error(f"Task {task_id} failed: {e}")
            activity_logger.log_error(f"Task {task.name} failed: {e}")
        finally:
            with self._lock:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
                self._history.append(task)
                if task.status == "completed" and task.repeat_interval > 0:
                    if task.repeat_count == -1 or task.execution_count < task.repeat_count:
                        new_task = Task(self._next_id(), task.name, task.func, task.args,
                                        task.kwargs, task.priority_label, task.dependencies,
                                        task.repeat_interval, task.repeat_count,
                                        task.deadline, task.background)
                        new_task.created_at = time.time()
                        self._tasks[new_task.id] = new_task
                        self._func_map[new_task.id] = task.func
                        threading.Timer(task.repeat_interval, self._push_task, [new_task]).start()
                self._save_tasks()

    def _scheduler_loop(self):
        while not self._stop_event.is_set():
            with self._lock:
                for task_id, task in list(self._tasks.items()):
                    if task.status == "waiting_dependency":
                        all_done = all(
                            (self._tasks.get(dep_id) or type("x",(),{"status":"pending"})).status == "completed"
                            for dep_id in task.dependencies
                        )
                        if all_done:
                            self._push_task(task)
            task_id = None
            with self._lock:
                max_conc = CFG.get("max_concurrent_tasks", 3)
                if len(self._running_tasks) < max_conc:
                    task_id = self._pop_task()
            if task_id:
                threading.Thread(target=self._execute_task, args=(task_id,), daemon=True).start()
            else:
                time.sleep(0.5)

    def start(self):
        if self._scheduler_thread is None or not self._scheduler_thread.is_alive():
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2)
        self._save_tasks()

    def get_status(self) -> dict:
        with self._lock:
            return {
                "total": len(self._tasks),
                "pending": sum(1 for t in self._tasks.values() if t.status == "pending"),
                "running": len(self._running_tasks),
                "completed": sum(1 for t in self._tasks.values() if t.status == "completed"),
                "failed": sum(1 for t in self._tasks.values() if t.status == "failed"),
                "waiting": sum(1 for t in self._tasks.values() if t.status == "waiting_dependency"),
            }

    def _save_tasks(self):
        data = {
            "tasks": {tid: t.to_dict() for tid, t in self._tasks.items()},
            "history": [t.to_dict() for t in self._history[-100:]],
        }
        try:
            (self.save_path / "tasks_state.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log.error(f"Save tasks error: {e}")

    def _load_tasks(self):
        state_file = self.save_path / "tasks_state.json"
        if not state_file.exists():
            return
        try:
            data = json.loads(state_file.read_text("utf-8"))
            for tid, tdict in data.get("tasks", {}).items():
                if tdict.get("status") == "completed":
                    continue
                task = Task(tdict["id"], tdict["name"], lambda: None,
                            priority=tdict.get("priority", "NORMAL"),
                            dependencies=tdict.get("dependencies", []),
                            repeat_interval=tdict.get("repeat_interval", 0),
                            repeat_count=tdict.get("repeat_count", 1),
                            deadline=tdict.get("deadline"),
                            background=tdict.get("background", False))
                task.created_at = tdict.get("created_at", time.time())
                self._tasks[tid] = task
                self._push_task(task)
            log.info(f"Loaded {len(self._tasks)} tasks from state.")
        except Exception as e:
            log.error(f"Load tasks error: {e}")


# ---- Инструменты ----
class Tool:
    name = "base"
    description = "Base tool"
    parameters: List[Dict[str, Any]] = []

    def execute(self, **kwargs) -> str:
        raise NotImplementedError


class FileSystemTool(Tool):
    name = "filesystem"
    description = "Работа с файловой системой: чтение, запись, список"
    parameters = [
        {"name": "action", "type": "string", "enum": ["read", "write", "list", "delete", "mkdir"]},
        {"name": "path", "type": "string"},
        {"name": "content", "type": "string", "required": False},
    ]
    def execute(self, action: str, path: str, content: str = "") -> str:
        try:
            p = (workspace() / path).resolve()
            if not p.is_relative_to(workspace().resolve()):
                return "Доступ запрещён за пределами рабочей папки."
            if action == "read":
                if not p.exists(): return f"Файл {path} не найден."
                return p.read_text(encoding="utf-8", errors="replace")[:20000]
            elif action == "write":
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return f"Файл {path} записан."
            elif action == "list":
                if not p.is_dir(): return f"{path} не папка."
                items = [f.name for f in p.iterdir() if not f.name.startswith('.')]
                return "\n".join(items[:100])
            elif action == "delete":
                if p.is_file():
                    p.unlink()
                    return f"Файл {path} удалён."
                return "Удаление папок запрещено."
            elif action == "mkdir":
                p.mkdir(parents=True, exist_ok=True)
                return f"Папка {path} создана."
            return "Неизвестное действие."
        except Exception as e:
            return f"Ошибка: {e}"


class TerminalTool(Tool):
    name = "terminal"
    description = "Выполнение команд в терминале (только безопасные)"
    parameters = [{"name": "command", "type": "string"}]
    def execute(self, command: str) -> str:
        if not TOOLS_EXTRA_OK: return "Отключено"
        from scp_tools_extra import terminal
        return terminal(tools_env,command)



class ProcessManagerTool(Tool):
    name = "process_manager"
    description = "Управление процессами: запуск, остановка, список"
    parameters = [
        {"name": "action", "type": "string", "enum": ["list", "start", "stop", "kill"]},
        {"name": "name", "type": "string", "required": False},
        {"name": "command", "type": "string", "required": False},
    ]
    def execute(self, action: str, name: str = "", command: str = "") -> str:
        if not PSUTIL_OK:
            return "psutil не установлен."
        if action == "list":
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    processes.append(f"{proc.info['pid']}: {proc.info['name']} (CPU {proc.info['cpu_percent']:.1f}%, MEM {proc.info['memory_info'].rss/1024/1024:.1f}MB)")
                except Exception:
                    pass
            return "\n".join(processes[:50])
        elif action in ('start','stop','kill'):
            return 'Для управления разрешёнными приложениями используйте app_control.'
        return "Неизвестное действие."


class SystemMonitorTool(Tool):
    name = "system_monitor"
    description = "Мониторинг системы: CPU, RAM, диск, сеть, VRAM"
    parameters = [{"name": "metric", "type": "string",
                   "enum": ["all", "cpu", "ram", "disk", "network", "vram", "processes"]}]
    def execute(self, metric: str = "all") -> str:
        if not PSUTIL_OK:
            return "Ошибка: модуль psutil не установлен. Выполните: python -m pip install psutil"
        metric = str(metric or "all").lower().strip()
        result = []
        if metric in ("all", "cpu"):
            try:
                cpu = psutil.cpu_percent(interval=0.5)
                freq = psutil.cpu_freq()
                cores = psutil.cpu_count(logical=True) or 0
                cpu_name = platform.processor() or platform.machine() or "не определён"
                line = f"CPU: загрузка {cpu:.1f}% | потоков {cores} | {cpu_name}"
                if freq:
                    line += f" | частота {freq.current/1000:.2f} ГГц"
                result.append(line)
            except Exception as e:
                result.append(f"CPU: ошибка чтения — {e}")
        if metric in ("all", "ram"):
            try:
                mem = psutil.virtual_memory()
                result.append(f"RAM: занято {mem.used/1024**3:.2f} GB из {mem.total/1024**3:.2f} GB ({mem.percent:.1f}%) | свободно {mem.available/1024**3:.2f} GB")
            except Exception as e:
                result.append(f"RAM: ошибка чтения — {e}")
        if metric in ("all", "disk"):
            try:
                root = Path.cwd().anchor or os.path.abspath(os.sep)
                disk = psutil.disk_usage(root)
                result.append(f"Диск: занято {disk.used/1024**3:.1f} GB из {disk.total/1024**3:.1f} GB ({disk.percent:.1f}%)")
            except Exception as e:
                result.append(f"Диск: ошибка чтения — {e}")
        if metric in ("all", "network"):
            try:
                before = psutil.net_io_counters()
                time.sleep(0.35)
                after = psutil.net_io_counters()
                sent_rate = max(0, after.bytes_sent - before.bytes_sent) / 1024**2 / 0.35
                recv_rate = max(0, after.bytes_recv - before.bytes_recv) / 1024**2 / 0.35
                result.append(
                    f"Сеть: сейчас ↓ {recv_rate:.2f} MB/s, ↑ {sent_rate:.2f} MB/s | "
                    f"всего получено {after.bytes_recv/1024**3:.2f} GB, отправлено {after.bytes_sent/1024**3:.2f} GB"
                )
                stats = psutil.net_if_stats()
                active = [name for name, st in stats.items() if st.isup]
                if active:
                    result.append("Интерфейсы активны: " + ", ".join(active[:10]))
            except Exception as e:
                result.append(f"Сеть: ошибка чтения — {e}")
        if metric in ("all", "vram"):
            try:
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                    encoding="utf-8", timeout=5)
                used, total = out.strip().split(",")
                result.append(f"VRAM: {used.strip()} / {total.strip()} MB")
            except Exception:
                result.append("VRAM: недоступно")
        if metric in ("all", "processes"):
            proc_list = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    proc_list.append(f"{proc.info['pid']}: {proc.info['name']} (MEM {proc.info['memory_info'].rss/1024**2:.1f}MB)")
                except Exception:
                    pass
            result.append("Процессы:\n" + "\n".join(proc_list[:30]))
        return "\n".join(result)


class CodeAnalyzerTool(Tool):
    name = "code_analyzer"
    description = "Статический анализ кода Python"
    parameters = [{"name": "path", "type": "string"}]
    def execute(self, path: str) -> str:
        p = (workspace() / path).resolve()
        if not str(p).startswith(str(workspace().resolve())):
            return "Доступ запрещён."
        if not p.exists():
            return f"Путь {path} не найден."
        targets = list(p.rglob("*.py"))[:20] if p.is_dir() else ([p] if p.suffix == ".py" else [])
        result = []
        for f in targets:
            try:
                code = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(code)
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                functions = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                result.append(f"Файл: {f.name}\n  Классы: {', '.join(classes[:5])}\n  Функции: {', '.join(functions[:5])}")
            except Exception as e:
                result.append(f"Файл: {f.name} — ошибка: {e}")
        return "\n\n".join(result)


class PythonExecutorTool(Tool):
    name = "python_executor"
    description = "Выполнение Python-кода (безопасно)"
    parameters = [{"name": "code", "type": "string"}]
    def execute(self, code: str) -> str:
        if not TOOLS_EXTRA_OK: return "Отключено"
        from scp_tools_extra import python_exec
        return python_exec(tools_env,code)



class WebTool(Tool):
    name = "web"
    description = "Поиск в интернете, загрузка страниц"
    parameters = [{"name": "action", "type": "string", "enum": ["search", "fetch"]},
                  {"name": "query", "type": "string"}]
    def execute(self, action: str, query: str) -> str:
        if not WEB_OK:
            return "Библиотеки requests/BeautifulSoup не установлены."
        if action == "search":
            return "\n".join(Tools.get_search_results(query, num_results=5))
        elif action == "fetch":
            return (Tools.fetch_page_content(query) or "Не удалось загрузить.")[:10000]
        return "Неизвестное действие."


class MemoryTool(Tool):
    name = "memory"
    description = "Работа с памятью"
    parameters = [
        {"name": "action", "type": "string", "enum": ["read", "write", "clear"]},
        {"name": "memory_type", "type": "string", "enum": ["working", "session", "longterm"]},
        {"name": "key", "type": "string", "required": False},
        {"name": "value", "type": "string", "required": False},
    ]
    def execute(self, action: str, memory_type: str, key: str = "", value: str = "") -> str:
        if memory_type == "working":
            if action == "read": return working_memory.get(key, "")
            if action == "write": working_memory[key] = value; return "Записано."
            if action == "clear": working_memory.clear(); return "Очищено."
        elif memory_type == "session":
            if action == "read":
                ctx = short_mem.get("local")[-10:]
                return "\n".join(f"{m['role']}: {m['content'][:100]}" for m in ctx)
            if action == "write": short_mem.add("local", "system", value); return "Записано."
            if action == "clear": short_mem.clear("local"); return "Очищено."
        elif memory_type == "longterm":
            if action == "read": return personal_mem.formatted(20) + "\n" + long_mem.formatted(20)
            if action == "write": long_mem.add(value); return "Записано."
            if action == "clear": long_mem.clear(); personal_mem.clear(); return "Очищено."
        return "Неизвестная операция."


class KnowledgeTool(Tool):
    name = "knowledge"
    description = "Поиск и добавление фактов"
    parameters = [{"name": "action", "type": "string", "enum": ["query", "add"]},
                  {"name": "topic", "type": "string", "required": False},
                  {"name": "fact", "type": "string", "required": False}]
    def execute(self, action: str, topic: str = "", fact: str = "") -> str:
        if action == "query":
            results = knowledge_base.query(topic)
            return "\n".join(f"- {r}" for r in results[:10]) if results else "Ничего не найдено."
        if action == "add":
            if topic and fact:
                knowledge_base.add_fact(topic, fact)
                return "Факт добавлен."
            return "Укажите тему и факт."
        return "Неизвестное действие."


class ProjectManagerTool(Tool):
    name = "project_manager"
    description = "Управление проектами"
    parameters = [{"name": "action", "type": "string",
                   "enum": ["list", "create", "switch", "info"]},
                  {"name": "project_name", "type": "string", "required": False}]
    def execute(self, action: str, project_name: str = "") -> str:
        if action == "list": return project_manager.list_projects()
        if action == "create":
            if project_name: project_manager.create_project(project_name); return f"Проект {project_name} создан."
            return "Укажите имя."
        if action == "switch":
            if project_name:
                project_manager.switch_project(project_name)
                return f"Переключен на {project_name}."
            return "Укажите имя."
        if action == "info": return project_manager.get_current_info()
        return "Неизвестное действие."


class TaskManagerTool(Tool):
    name = "task_manager"
    description = "Управление задачами"
    parameters = [{"name": "action", "type": "string", "enum": ["list", "status", "add"]},
                  {"name": "name", "type": "string", "required": False},
                  {"name": "priority", "type": "string", "required": False}]
    def execute(self, action: str, name: str = "", priority: str = "NORMAL") -> str:
        if action == "list":
            s = task_manager.get_status()
            return f"Всего: {s['total']}, В работе: {s['running']}, Ожидают: {s['pending']}, Выполнено: {s['completed']}, Ошибок: {s['failed']}"
        if action == "add":
            def dummy():
                activity_logger.log_system(f"Выполнена задача {name}")
                return f"Задача {name} выполнена."
            task_manager.add_task(name, dummy, priority=priority)
            return f"Задача {name} добавлена."
        return "Неизвестное действие."


# ---- Музыкальный центр ----
class MusicManager:
    BASE_URL = "https://ru.hitmoz.org"
    AUDIO_EXTS = {".mp3", ".m4a", ".ogg", ".wav", ".flac"}
    API = "https://archive.org/advancedsearch.php"
    META = "https://archive.org/metadata/{identifier}"

    def __init__(self):
        self.base_folder = Path(__file__).resolve().parent
        cfg_workspace = Path(str(CFG.get("workspace", "aria_workspace")))
        if cfg_workspace.is_absolute():
            self.workspace_folder = cfg_workspace / "music"
        else:
            self.workspace_folder = self.base_folder / cfg_workspace / "music"
        self.cwd_workspace_folder = Path.cwd() / cfg_workspace / "music"
        self.folder = self.workspace_folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.workspace_folder.mkdir(parents=True, exist_ok=True)
        self.cwd_workspace_folder.mkdir(parents=True, exist_ok=True)
        self.index_file = self.folder / "library.json"
        self._lock = threading.RLock()
        self._library = self._load_index()
        self._results = {}
        self._current = None
        self._volume = 0.70
        self._paused = False
        self._temp_playing = None
        self._scan_local_files()
        self._save_index()
        self._init_player()

    def _load_index(self):
        try:
            if self.index_file.exists():
                data = json.loads(self.index_file.read_text("utf-8"))
                if isinstance(data, list): return data
        except Exception as e:
            log.warning("Music library load: %s", e)
        return []

    def _save_index(self):
        try:
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            self.index_file.write_text(json.dumps(self._library, ensure_ascii=False, indent=2), "utf-8")
        except Exception as e:
            log.warning("Music library save: %s", e)

    @staticmethod
    def _norm_path(path):
        try: return str(Path(path).expanduser().resolve())
        except Exception: return str(path)

    @staticmethod
    def _safe_name(name):
        name = re.sub(r'[\\/*?:"<>|]', "_", str(name))
        name = re.sub(r"\s+", " ", name).strip()
        return name[:180] or "track"

    @staticmethod
    def _clean_title_from_filename(path):
        stem = Path(path).stem
        stem = re.sub(r"\s*\(\d+\)$", "", stem).strip()
        return stem or Path(path).name

    def _read_local_tags(self, path):
        title = self._clean_title_from_filename(path)
        artist = ""
        album = ""
        if MUTAGEN_OK:
            try:
                audio = MutagenFile(str(path), easy=True)
                if audio is not None:
                    tags = audio.tags or {}
                    title = str((tags.get("title") or [title])[0]).strip() or title
                    artist = str((tags.get("artist") or [""])[0]).strip()
                    album = str((tags.get("album") or [""])[0]).strip()
            except Exception:
                pass
        return title, artist, album

    def _music_roots(self):
        roots = [self.workspace_folder, self.base_folder / "music", self.cwd_workspace_folder]
        result = []
        seen = set()
        for root in roots:
            try:
                root = root.resolve()
            except Exception:
                root = Path(root)
            key = str(root).casefold()
            if key not in seen:
                seen.add(key)
                root.mkdir(parents=True, exist_ok=True)
                result.append(root)
        return result

    def _scan_local_files(self, force=False):
        with self._lock:
            if force:
                self._library = [i for i in self._library if not (i.get("local") or i.get("source") == "local")]
            existing = {}
            for item in self._library:
                p = self._norm_path(item.get("path", ""))
                if p: existing[p] = item
            changed = False
            all_files = []
            found_audio = []
            roots = self._music_roots()
            log.info(f"Music scan: roots {[str(r) for r in roots]}")
            for root in roots:
                try:
                    root_audio = []
                    for path in root.rglob("*"):
                        if path.is_file():
                            all_files.append(path)
                            if path.suffix.lower() in self.AUDIO_EXTS:
                                root_audio.append(path)
                    found_audio.extend(root_audio)
                    log.info(f"Music scan: {root} -> {len(root_audio)} audio")
                except Exception as e:
                    log.warning(f"Music scan failed {root}: {e}")
            unique_paths = {}
            for path in found_audio:
                unique_paths[path.name.lower()] = path
            for key, path in sorted(unique_paths.items(), key=lambda x: x[0].casefold()):
                title, artist, album = self._read_local_tags(path)
                norm = self._norm_path(path)
                item = existing.get(norm)
                if item is None:
                    item = {"title": title, "creator": artist, "album": album,
                            "path": norm, "source": "local", "local": True,
                            "added_at": time.time()}
                    self._library.append(item)
                    existing[norm] = item
                    changed = True
                else:
                    for k, v in (("title", title), ("creator", artist), ("album", album)):
                        if v and item.get(k) != v:
                            item[k] = v
                            changed = True
            actual = set(self._norm_path(p) for p in unique_paths.values())
            cleaned = []
            for item in self._library:
                if item.get("local") or item.get("source") == "local":
                    if self._norm_path(item.get("path", "")) in actual:
                        cleaned.append(item)
                    else:
                        changed = True
                else:
                    cleaned.append(item)
            self._library = cleaned
            if changed:
                self._save_index()

    def _library_tracks(self):
        self._scan_local_files()
        with self._lock:
            return list(self._library)

    def _init_player(self):
        if not PYGAME_OK: return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self._volume)
        except Exception as e:
            log.warning("pygame mixer init: %s", e)

    @staticmethod
    def _find_ffmpeg() -> str:
        exe = shutil.which("ffmpeg")
        if exe: return exe
        for c in [r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                  r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe", r"C:\ffmpeg\ffmpeg.exe"]:
            if os.path.exists(c): return c
        return ""

    def _convert_to_wav(self, path: Path) -> Path:
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            raise FileNotFoundError("ffmpeg.exe не найден.")
        temp_wav = workspace() / "temp" / f"_play_{path.stem}.wav"
        temp_wav.parent.mkdir(parents=True, exist_ok=True)
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
               "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", str(temp_wav)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg: {result.stderr.strip()}")
        return temp_wav

    def _ensure_player(self):
        if not PYGAME_OK: return False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self._volume)
            return True
        except Exception as e:
            log.warning("pygame mixer: %s", e)
            return False

    @staticmethod
    def _http_json(url, params=None, timeout=20):
        if not CFG["web_enabled"]: raise PermissionError("Интернет выключен")
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, doseq=True)
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-079-Derenguh/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    def search(self, query, limit=8):
        query = str(query).strip()
        if not query: return "Укажи, что искать."
        try:
            data = self._http_json(self.API, {
                "q": f'({query}) AND mediatype:audio',
                "fl[]": ["identifier", "title", "creator", "year"],
                "rows": min(max(int(limit), 1), 20), "page": 1, "output": "json"
            })
            docs = data.get("response", {}).get("docs", [])
            self._results.clear()
            if not docs:
                return "Ничего не найдено."
            lines = ["🎵 Результаты поиска в Internet Archive:"]
            for i, doc in enumerate(docs[:limit], 1):
                ident = str(doc.get("identifier", "")).strip()
                if not ident: continue
                self._results[str(i)] = {"source": "archive", "identifier": ident}
                title = str(doc.get("title", ident)).strip()
                creator = str(doc.get("creator", "")).strip()
                year = str(doc.get("year", "")).strip()
                extra = f" — {creator}" if creator else ""
                extra += f" ({year})" if year else ""
                lines.append(f"{i}. {title}{extra}")
            lines.append("\nДля скачивания: «скачай музыку №N».")
            return "\n".join(lines)
        except Exception as e:
            log.exception("Музыкальный поиск")
            return f"Не удалось выполнить поиск: {e}"

    def _is_allowed_metadata(self, meta):
        md = (meta or {}).get("metadata", {}) or {}
        license_url = str(md.get("licenseurl") or md.get("rights") or md.get("license", "")).lower()
        return any(x in license_url for x in ("publicdomain", "creativecommons", "cc0", "cc-by", "by-sa", "by-nc", "by-nd"))

    def _pick_mp3(self, files):
        mp3s = [f for f in files if str(f.get("name", "")).lower().endswith(".mp3")]
        if not mp3s: return None
        return max(mp3s, key=lambda f: int(f.get("size", 0)))

    def _download_archive(self, identifier):
        if not CFG["web_enabled"]: raise PermissionError("Интернет выключен")
        meta = self._http_json(self.META.format(identifier=urllib.parse.quote(identifier, safe="")))
        if not self._is_allowed_metadata(meta):
            return None, "Не указана свободная лицензия."
        f = self._pick_mp3(meta.get("files", []))
        if not f: return None, "Нет MP3-файла."
        md = meta.get("metadata", {}) or {}
        title = str(md.get("title") or identifier).strip()
        creator = str(md.get("creator") or "").strip()
        base = self._safe_name(f"{creator} - {title}" if creator else title)
        if base.lower().endswith(".mp3"): base = base[:-4]
        target = self.folder / f"{base}.mp3"
        if target.exists():
            n = 2
            while (self.folder / f"{base} ({n}).mp3").exists(): n += 1
            target = self.folder / f"{base} ({n}).mp3"
        remote = str(f.get("name", "")).strip()
        url = f"https://archive.org/download/{urllib.parse.quote(identifier, safe='')}/{urllib.parse.quote(remote, safe='/')}"
        req = urllib.request.Request(url, headers={"User-Agent": "SCP-079-Derenguh/1.0"})
        tmp = target.with_suffix(".part")
        try:
            with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as out:
                shutil.copyfileobj(r, out)
            tmp.replace(target)
        except Exception:
            try:
                if tmp.exists(): tmp.unlink()
            except Exception: pass
            raise
        entry = {"title": title, "creator": creator, "album": str(md.get("album") or ""),
                 "path": self._norm_path(target), "identifier": identifier,
                 "source": "Internet Archive", "local": False,
                 "license": md.get("licenseurl") or md.get("rights") or md.get("license", ""),
                 "added_at": time.time()}
        with self._lock:
            self._library.append(entry)
            self._save_index()
        return entry, None

    def download(self, query_or_number):
        key = str(query_or_number).strip()
        item = self._results.get(key)
        if not item:
            return self.search(key)
        if item.get("source") == "archive":
            identifier = item.get("identifier")
            if not identifier:
                return "Идентификатор не найден."
            try:
                entry, err = self._download_archive(identifier)
                if entry:
                    tracks = self._library_tracks()
                    num = next((i for i, x in enumerate(tracks, 1) if x.get("path") == entry.get("path")), "?")
                    return (f"🎵 Скачано: {entry['title']}" +
                            (f" — {entry['creator']}" if entry.get('creator') else "") +
                            f"\n📁 {entry.get('path', '')}\n🔢 №{num}")
                return "❌ " + (err or "Скачать не удалось.")
            except Exception as e:
                return f"Не удалось скачать: {e}"
        return "Неизвестный источник."

    def list_tracks(self):
        tracks = self._library_tracks()
        if not tracks:
            roots = "\n".join(f"• {x}" for x in self._music_roots())
            return (f"🎵 Библиотека пуста.\n📁 {self.folder}\n{roots}\n\n"
                    "Поддерживаются .mp3, .m4a, .ogg, .wav, .flac.\n"
                    "Попробуйте «обновить музыку».")
        lines = ["🎵 МУЗЫКАЛЬНАЯ БИБЛИОТЕКА:"]
        for i, item in enumerate(tracks, 1):
            path = Path(item.get("path", ""))
            title = str(item.get("title") or self._clean_title_from_filename(path))
            creator = str(item.get("creator") or "").strip()
            marker = "📁" if item.get("local") or item.get("source") == "local" else "🌐"
            status = "✓" if path.is_file() else "⚠"
            suffix = f" — {creator}" if creator else ""
            lines.append(f"{i}. {marker} {title}{suffix} [{status}]")
        lines.append("\nЗапуск: «включи 1» или по названию.")
        return "\n".join(lines)

    def refresh(self):
        self._scan_local_files(force=True)
        self._save_index()
        return f"Библиотека обновлена. Всего: {len(self._library)}"

    def _resolve_track(self, selector):
        tracks = self._library_tracks()
        selector = str(selector).strip()
        if selector.startswith("№"): selector = selector[1:].strip()
        with self._lock:
            if selector.isdigit():
                i = int(selector) - 1
                return tracks[i] if 0 <= i < len(tracks) else None
            low = selector.casefold()
            for item in tracks:
                haystack = " ".join((str(item.get("title", "")),
                                     str(item.get("creator", "")),
                                     Path(str(item.get("path", ""))).stem)).casefold()
                if low in haystack: return item
        return None

    def play(self, selector):
        if not self._ensure_player():
            return "Установи pygame: python -m pip install pygame"
        item = self._resolve_track(selector)
        if not item:
            return "Композиция не найдена."
        path = Path(item.get("path", ""))
        if not path.exists():
            return f"Файл не найден: {path.name}"
        play_path = path
        temp_wav = None
        if path.suffix.lower() in {".m4a", ".flac"}:
            try:
                temp_wav = self._convert_to_wav(path)
                play_path = temp_wav
            except Exception as e:
                return f"Не удалось конвертировать: {e}"
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(play_path))
            pygame.mixer.music.set_volume(self._volume)
            pygame.mixer.music.play()
            self._current, self._paused = item, False
            self._temp_playing = temp_wav
            return f"▶️ Играю: {item.get('title', path.stem)}"
        except Exception as e:
            return f"Не удалось воспроизвести: {e}"

    def pause(self):
        if not self._ensure_player(): return "pygame недоступен."
        try:
            pygame.mixer.music.pause(); self._paused = True; return "⏸️ Пауза."
        except Exception as e: return f"Ошибка: {e}"

    def resume(self):
        if not self._ensure_player(): return "pygame недоступен."
        try:
            pygame.mixer.music.unpause(); self._paused = False; return "▶️ Продолжаю."
        except Exception as e: return f"Ошибка: {e}"

    def stop(self):
        if not self._ensure_player(): return "pygame недоступен."
        try:
            pygame.mixer.music.stop()
            self._paused = False
            if self._temp_playing and self._temp_playing.exists():
                try: self._temp_playing.unlink()
                except Exception: pass
                self._temp_playing = None
            return "⏹️ Остановлено."
        except Exception as e: return f"Ошибка: {e}"

    def volume(self, value=None):
        if value is None: return f"🔊 Громкость: {round(self._volume * 100)}%"
        try:
            v = max(0, min(100, int(float(str(value).replace(",", ".")))))
            self._volume = v / 100
            if PYGAME_OK and pygame.mixer.get_init():
                pygame.mixer.music.set_volume(self._volume)
            return f"🔊 Громкость: {v}%."
        except Exception:
            return "Укажи число 0-100."

    def handle_command(self, text):
        t, low = str(text).strip(), str(text).strip().casefold()
        m = re.match(r"^(?:найди|поищи|поиск)\s+(?:музыку|песню|трек)\s+(.+)$", t, re.I)
        if m: return self.search(m.group(1))
        m = re.match(r"^(?:скачай|загрузи)\s+(?:музыку|песню|трек)\s+(?:№\s*)?(\d+)$", t, re.I)
        if m: return self.download(m.group(1))
        if low in {"список музыки", "список песен", "моя музыка", "скачанные песни", "музыка"}:
            return self.list_tracks()
        if low in {"обновить музыку", "пересканировать музыку", "обновить библиотеку"}:
            return self.refresh()
        if low in {"где музыка", "папка музыки", "путь музыки", "где песни"}:
            roots = "\n".join(f"• {x}" for x in self._music_roots())
            return f"🎵 Пути:\n📁 {self.folder}\n{roots}"
        m = re.match(r"^(?:включи|запусти|играй)\s+(?:песню|трек)?\s*(?:№\s*)?(\d+|.+)$", t, re.I)
        if m: return self.play(m.group(1).strip())
        if low in {"пауза", "поставь на паузу", "музыка пауза"}: return self.pause()
        if low in {"продолжи", "продолжить", "сними с паузы", "музыка продолжи"}: return self.resume()
        if low in {"останови музыку", "стоп музыка", "выключи музыку", "музыка стоп"}: return self.stop()
        m = re.match(r"^(?:громкость|звук)\s*(?:на|=)?\s*(\d{1,3})\s*%?$", t, re.I)
        if m: return self.volume(m.group(1))
        if low in {"какая громкость", "громкость?"}: return self.volume()
        return None


music_manager = MusicManager()


class MusicTool(Tool):
    name = "music"
    description = "Поиск/скачивание MP3, список, воспроизведение, пауза, стоп, громкость."
    parameters = [
        {"name": "action", "type": "string", "required": False},
        {"name": "query", "type": "string", "required": False},
        {"name": "value", "type": "string", "required": False},
    ]
    def execute(self, action="", query="", value=""):
        a = str(action).strip().casefold()
        if a == "search": return music_manager.search(query)
        if a == "download": return music_manager.download(query)
        if a == "list": return music_manager.list_tracks()
        if a == "refresh": return music_manager.refresh()
        if a == "play": return music_manager.play(query)
        if a == "pause": return music_manager.pause()
        if a == "resume": return music_manager.resume()
        if a == "stop": return music_manager.stop()
        if a == "volume": return music_manager.volume(value if value != "" else None)
        return "Неизвестное действие music."


# ---- WebCrawler (защищён от отсутствия WEB_OK) ----
class WebCrawler:
    def __init__(self):
        self._lock = threading.RLock()
        self._session = None
        self._history: deque = deque(maxlen=200)

    def _get_session(self):
        if not WEB_OK:
            return None
        if self._session is None:
            self._session = Tools._http_session()
        return self._session

    def search_all(self, query: str, num_results: int = 10, deep_fetch: bool = False) -> dict:
        if not WEB_OK:
            return {"query": query, "results": [], "errors": ["WEB_OK=False"]}
        query = re.sub(r"\s+", " ", (query or "")).strip()
        if not query:
            return {"query": "", "results": [], "errors": []}

        # Всегда пробуем Google HTML fallback, даже если модуль googlesearch
        # не установлен. Все движки запускаются независимо друг от друга.
        engines = [("google", self._search_google),
                   ("duckduckgo", self._search_ddg),
                   ("bing", self._search_bing)]

        results_map = {}
        errors = []
        threads = []

        def worker(name, func):
            try:
                urls = func(query, num_results)
                with self._lock:
                    results_map[name] = urls
            except Exception as e:
                with self._lock:
                    errors.append(f"{name}: {e}")

        for name, func in engines:
            t = threading.Thread(target=worker, args=(name, func), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=15)

        seen = set()
        ranked = []
        for engine in ["google", "duckduckgo", "bing"]:
            for url in results_map.get(engine, []):
                key = self._url_key(url)
                if key and key not in seen:
                    seen.add(key)
                    ranked.append({"url": url, "engine": engine, "fetched": False, "text": ""})

        if deep_fetch and ranked:
            self._deep_fetch(ranked[:num_results])

        self._history.append({"time": time.time(), "query": query, "count": len(ranked)})
        return {"query": query, "results": ranked[:num_results],
                "errors": errors, "engines_used": list(results_map.keys())}

    def _url_key(self, url: str) -> str:
        try:
            from urllib.parse import urlparse, urlunsplit
            p = urlparse(url)
            return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))
        except Exception:
            return url.lower().rstrip("/")

    def _search_google(self, query: str, limit: int) -> List[str]:
        # Сначала штатный googlesearch, затем прямой HTML Google.
        # Прямой fallback нужен, потому что googlesearch часто ломается
        # после изменений Google/капч и тогда весь веб-поиск становился пустым.
        if GOOGLE_SEARCH_OK:
            try:
                urls = [x for x in search(query, num_results=limit, lang="ru") if isinstance(x, str)]
                urls = Tools._dedupe_urls(urls, limit)
                if urls:
                    return urls
            except Exception as e:
                activity_logger.log_learning(f"Google library error: {e}")
        s = self._get_session()
        if not s:
            return []
        try:
            from urllib.parse import quote_plus
            url = "https://www.google.com/search?q=" + quote_plus(query) + f"&num={max(1, min(limit, 10))}&hl=ru"
            r = s.get(url, timeout=(7, 20), allow_redirects=True)
            if r.status_code != 200:
                activity_logger.log_learning(f"Google HTTP {r.status_code}")
                return []
            soup = BeautifulSoup(r.content, "html.parser")
            urls = []
            for a in soup.select("a"):
                href = a.get("href", "")
                if href.startswith("/url?"):
                    try:
                        from urllib.parse import parse_qs, urlparse
                        q = parse_qs(urlparse(href).query).get("q", [""])[0]
                        if q:
                            href = q
                    except Exception:
                        pass
                clean = Tools._normalize_search_url(href)
                if clean:
                    urls.append(clean)
            return Tools._dedupe_urls(urls, limit)
        except Exception as e:
            activity_logger.log_learning(f"Google HTML error: {e}")
            return []

    def _search_ddg(self, query: str, limit: int) -> List[str]:
        s = self._get_session()
        if not s: return []
        try:
            from urllib.parse import quote_plus
            url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
            r = s.get(url, timeout=(6, 18), allow_redirects=True)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                links = soup.select("a.result__a, .result__title a, a[data-testid='result-title-a']")
                urls = [Tools._normalize_search_url(l.get("href", "")) for l in links if l.get("href")]
                return Tools._dedupe_urls(urls, limit)
            activity_logger.log_learning(f"DuckDuckGo HTTP {r.status_code}")
        except Exception as e:
            activity_logger.log_learning(f"DuckDuckGo error: {e}")
        return []

    def _search_bing(self, query: str, limit: int) -> List[str]:
        s = self._get_session()
        if not s: return []
        try:
            from urllib.parse import quote_plus
            url = "https://www.bing.com/search?q=" + quote_plus(query) + "&setlang=ru"
            r = s.get(url, timeout=(6, 18), allow_redirects=True)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                urls = [Tools._normalize_search_url(l.get("href", ""))
                        for l in soup.select("li.b_algo h2 a, #b_results h2 a") if l.get("href")]
                return Tools._dedupe_urls(urls, limit)
            activity_logger.log_learning(f"Bing HTTP {r.status_code}")
        except Exception as e:
            activity_logger.log_learning(f"Bing error: {e}")
        return []

    def _deep_fetch(self, results: List[dict]):
        def fetch_one(item):
            text = Tools.fetch_page_content(item["url"])
            item["text"] = text[:8000] if text else ""
            item["fetched"] = True
        threads = []
        for item in results:
            t = threading.Thread(target=fetch_one, args=(item,), daemon=True)
            threads.append(t); t.start()
        for t in threads:
            t.join(timeout=20)


# ---- WebMonitor ----
class WebMonitor:
    def __init__(self, folder: str = "web_monitor"):
        self.root = workspace() / folder
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._index_file = self.root / "watch_index.json"
        self._index = self._load_index()
        self._session = None

    def _get_session(self):
        if not WEB_OK: return None
        if self._session is None:
            self._session = Tools._http_session()
        return self._session

    def _load_index(self) -> dict:
        if self._index_file.exists():
            try: return json.loads(self._index_file.read_text("utf-8"))
            except Exception: pass
        return {"watches": {}, "last_check": 0}

    def _save_index(self):
        self._index["last_check"] = time.time()
        self._index_file.write_text(json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_watch(self, url: str, label: str = "", interval_hours: int = 24) -> str:
        watch_id = hashlib.md5(url.encode()).hexdigest()[:12]
        with self._lock:
            self._index["watches"][watch_id] = {
                "url": url, "label": label or url, "interval_hours": interval_hours,
                "added_at": time.time(), "last_check": 0, "last_hash": "", "history": []}
            self._save_index()
        return watch_id

    def remove_watch(self, watch_id: str) -> bool:
        with self._lock:
            if watch_id in self._index["watches"]:
                del self._index["watches"][watch_id]
                self._save_index()
                return True
        return False

    def check_all(self) -> List[dict]:
        if not WEB_OK: return []
        changes = []
        with self._lock:
            watches = dict(self._index["watches"])
        for wid, data in watches.items():
            last = data.get("last_check", 0)
            interval = data.get("interval_hours", 24) * 3600
            if time.time() - last < interval: continue
            try:
                text = Tools.fetch_page_content(data["url"])
                if not text: continue
                h = hashlib.sha256(text.encode()).hexdigest()[:32]
                with self._lock:
                    w = self._index["watches"].get(wid)
                    if not w: continue
                    w["last_check"] = time.time()
                    if w["last_hash"] and w["last_hash"] != h:
                        diff = self._make_diff(w.get("last_text", ""), text[:5000])
                        w["history"].append({"time": time.time(), "hash": h, "diff": diff})
                        w["history"] = w["history"][-20:]
                        changes.append({"id": wid, "label": w["label"], "url": data["url"], "diff": diff})
                    w["last_hash"] = h
                    w["last_text"] = text[:5000]
                self._save_index()
            except Exception as e:
                activity_logger.log_error(f"WebMonitor check {wid}: {e}")
        return changes

    @staticmethod
    def _make_diff(old: str, new: str) -> str:
        import difflib
        diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=2))
        return "".join(diff[:50]) if diff else "(структурные изменения)"

    def list_watches(self) -> str:
        with self._lock:
            lines = ["👁 WebMonitor:"]
            for wid, data in self._index["watches"].items():
                status = "🟢" if data.get("last_hash") else "🟡"
                lines.append(f"  {wid}: {data.get('label', wid)} [{status}]")
            return "\n".join(lines) if len(lines) > 1 else "Нет наблюдений."


# ---- UniversalMusicDownloader ----
class UniversalMusicDownloader:
    def __init__(self):
        self._session = None
        self._lock = threading.RLock()

    def _get_session(self):
        if not WEB_OK: return None
        if self._session is None:
            self._session = Tools._http_session()
        return self._session

    def search_and_download(self, query: str, limit: int = 5) -> str:
        if not WEB_OK:
            return "Библиотеки для веб-поиска не установлены."
        result = web_crawler.search_all(query + " audio mp3 m4a download",
                                        num_results=limit, deep_fetch=True)
        hits = []
        for item in result.get("results", []):
            url = item["url"]
            text = item.get("text", "")
            audio_urls = self._extract_audio_urls(url, text)
            if audio_urls:
                hits.extend(audio_urls)
        if not hits:
            return "Не удалось найти прямые ссылки на аудио."
        lines = [f"🎵 Найдено {len(hits)} аудио-ссылок:"]
        for i, hit in enumerate(hits[:8], 1):
            lines.append(f"{i}. {hit['title']} — {hit['url'][:80]}...")
        return "\n".join(lines)

    def _extract_audio_urls(self, base_url: str, html_text: str) -> List[dict]:
        found = []
        if not html_text: return found
        patterns = [
            r'https?://[^\s"<>]+\.(?:mp3|m4a|ogg|wav|flac)(?:\?[^\s"<>]*)?',
            r'"(https?://[^"]+\.(?:mp3|m4a|ogg|wav|flac)[^"]*)"',
        ]
        for pat in patterns:
            for match in re.finditer(pat, html_text, re.I):
                url = match.group(0).strip('""')
                if url not in [x["url"] for x in found]:
                    found.append({"url": url, "title": self._guess_title(url), "source": base_url})
        return found

    @staticmethod
    def _guess_title(url: str) -> str:
        try:
            p = urllib.parse.urlparse(url)
            name = urllib.parse.unquote(p.path.split("/")[-1])
            name = re.sub(r'[_\-]+', " ", name)
            name = re.sub(r'\.(mp3|m4a|ogg|wav|flac)$', "", name, flags=re.I)
            return name.strip() or "unknown"
        except Exception:
            return "unknown"

    def download_audio(self, url: str, title: str = "", folder: Path = None) -> str:
        if not WEB_OK:
            return "Библиотеки для скачивания не установлены."
        folder = folder or music_manager.folder
        folder.mkdir(parents=True, exist_ok=True)
        safe = music_manager._safe_name(title or self._guess_title(url))[:100]
        ext = ".mp3"
        m = re.search(r'\.(\w+)(?:\?|$)', url, re.I)
        if m: ext = "." + m.group(1).lower()
        target = folder / f"{safe}{ext}"
        n = 2
        while target.exists():
            target = folder / f"{safe} ({n}){ext}"; n += 1
        try:
            r = self._get_session().get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            entry = {"title": title or safe, "creator": "", "album": "",
                     "path": music_manager._norm_path(target),
                     "source": "universal_downloader", "local": False,
                     "added_at": time.time()}
            with music_manager._lock:
                music_manager._library.append(entry)
                music_manager._save_index()
            return f"✅ Скачано: {target.name} ({target.stat().st_size // 1024} KB)"
        except Exception as e:
            return f"❌ Ошибка: {e}"


class WebCrawlerTool(Tool):
    name = "web_crawler"
    description = "Многопоточный поиск в интернете по всем движкам (Google, DuckDuckGo, Bing)."
    parameters = [
        {"name": "query", "type": "string", "required": True},
        {"name": "num_results", "type": "integer", "required": False},
        {"name": "deep_fetch", "type": "boolean", "required": False},
    ]
    def execute(self, query: str = "", num_results: int = 5, deep_fetch: bool = False) -> str:
        if not WEB_OK:
            return "Библиотеки requests/BeautifulSoup не установлены."
        if not query:
            return "Пустой запрос."
        result = web_crawler.search_all(query, int(num_results), bool(deep_fetch))
        lines = [f"🔍 Поиск: {result['query']}",
                 f"Движки: {', '.join(result.get('engines_used', []))}"]
        if result.get("errors"):
            lines.append(f"⚠️ Ошибки: {'; '.join(result['errors'])}")
        for i, item in enumerate(result.get("results", []), 1):
            lines.append(f"{i}. {item['url']} [{item['engine']}]")
            if item.get("text"):
                preview = item["text"].replace("\n", " ")[:300]
                lines.append(f"   📄 {preview}")
        return "\n".join(lines)


class WebMonitorTool(Tool):
    name = "web_monitor"
    description = "Отслеживание изменений на веб-страницах."
    parameters = [
        {"name": "action", "type": "string", "required": True},
        {"name": "url", "type": "string", "required": False},
        {"name": "label", "type": "string", "required": False},
        {"name": "watch_id", "type": "string", "required": False},
    ]
    def execute(self, action: str = "list", url: str = "", label: str = "", watch_id: str = "") -> str:
        if action == "add":
            if not url: return "Укажите URL."
            wid = web_monitor.add_watch(url, label)
            return f"👁 Добавлено {wid} для {url}"
        elif action == "check":
            changes = web_monitor.check_all()
            if not changes: return "Изменений нет."
            lines = ["🔄 Изменения:"]
            for ch in changes:
                lines.append(f"• {ch['label']} ({ch['url']})")
                lines.append(ch.get("diff", "")[:500])
            return "\n".join(lines)
        elif action == "remove":
            return f"Удалено {watch_id}." if web_monitor.remove_watch(watch_id) else "ID не найден."
        return web_monitor.list_watches()


class UniversalMusicTool(Tool):
    name = "universal_music"
    description = "Универсальный поиск и скачивание аудио."
    parameters = [
        {"name": "action", "type": "string", "required": True},
        {"name": "query", "type": "string", "required": False},
        {"name": "title", "type": "string", "required": False},
    ]
    def execute(self, action: str = "search", query: str = "", title: str = "") -> str:
        if action == "search": return universal_music.search_and_download(query)
        if action == "download": return universal_music.download_audio(query, title)
        return "Неизвестное действие."


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self.register_defaults()

    def register_defaults(self):
        self.register(FileSystemTool())
        self.register(TerminalTool())
        self.register(ProcessManagerTool())
        self.register(SystemMonitorTool())
        self.register(CodeAnalyzerTool())
        self.register(PythonExecutorTool())
        self.register(WebTool())
        self.register(MemoryTool())
        self.register(KnowledgeTool())
        self.register(ProjectManagerTool())
        self.register(TaskManagerTool())
        self.register(MusicTool())
        self.register(WebCrawlerTool())
        self.register(WebMonitorTool())
        self.register(UniversalMusicTool())

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> str:
        return "\n".join(f"- {name}: {tool.description}" for name, tool in self._tools.items())

    def execute(self, tool_name: str, **kwargs) -> str:
        tool = self.get(tool_name)
        if tool:
            try:
                if not getattr(_CURRENT_REQUEST,'is_owner',False) and tool_name not in ("calculator","system_monitor"): return 'Действие доступно только владельцу.'
                dangerous = tool_name in ('terminal','python_executor','app_control','screenshot','clipboard') or (tool_name=='filesystem' and kwargs.get('action') in ('delete','write'))
                if dangerous:
                    ctx = str(getattr(_CURRENT_CTX,'value',''))
                    if ctx.startswith('tg:'): approved = tg_bridge.confirm_tool(ctx,tool_name,kwargs)
                    else: approved = ctx=='local' and gui_gate and gui_gate.confirm(tool_name,kwargs)
                    if not approved: return 'Действие не подтверждено.'
                if tool_name in ('clipboard','screenshot'):
                    if not gui_gate: return 'Нет графической сессии.'
                    result = gui_gate.call(lambda:tool.execute(**kwargs))
                else: result = tool.execute(**kwargs)
                kind='tool_failure' if str(result).startswith('Ошибка') else 'tool_success'
                if event_bus: event_bus.emit(kind, {'tool':tool_name})
                if MEMORY_V2_OK: archive.add_diary(('Получилось: ' if kind=='tool_success' else 'Не получилось: ')+tool_name,[kind],'tool')
                if presence: presence.data['system_activity_at']=time.time()
                return result
            except Exception as e:
                if event_bus: event_bus.emit('tool_failure',{'tool':tool_name})
                if MEMORY_V2_OK: archive.add_diary('Не получилось: '+tool_name,['tool_failure'],'tool')
                return f"Ошибка {tool_name}: {e}"
        return f"Инструмент {tool_name} не найден."


tool_registry = ToolRegistry()
web_crawler = WebCrawler()
web_monitor = WebMonitor()
universal_music = UniversalMusicDownloader()


# ---- Система монитора ----
class SystemMonitor:
    def __init__(self):
        self._lock = threading.RLock()
        self._history = deque(maxlen=60)
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    def start(self, interval: int = 5):
        if self._running: return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread: self._thread.join(timeout=2)

    def _loop(self, interval):
        while not self._stop_event.is_set():
            if PSUTIL_OK:
                try:
                    mem = psutil.virtual_memory()
                    cpu = psutil.cpu_percent(interval=0.5)
                    disk = psutil.disk_usage('/')
                    net = psutil.net_io_counters()
                    snapshot = {
                        "timestamp": time.time(), "cpu": cpu,
                        "ram_total": mem.total / 1024**3, "ram_used": mem.used / 1024**3,
                        "ram_percent": mem.percent,
                        "disk_total": disk.total / 1024**3, "disk_used": disk.used / 1024**3,
                        "disk_percent": disk.percent,
                        "net_sent": net.bytes_sent / 1024**2, "net_recv": net.bytes_recv / 1024**2,
                    }
                    with self._lock:
                        self._history.append(snapshot)
                except Exception as e:
                    log.error(f"SystemMonitor: {e}")
            time.sleep(interval)

    def get_latest(self) -> dict:
        with self._lock:
            return self._history[-1] if self._history else {}

    def get_history(self, n: int = 10) -> List[dict]:
        with self._lock:
            return list(self._history)[-n:]

    def check_alerts(self) -> List[str]:
        alerts = []
        latest = self.get_latest()
        if latest:
            if latest.get("ram_percent", 0) > 90: alerts.append("RAM > 90%")
            if latest.get("cpu", 0) > 80: alerts.append("CPU > 80%")
            if latest.get("disk_percent", 0) > 90: alerts.append("Disk > 90%")
        return alerts


system_monitor = SystemMonitor()


# ---- SelfInspector ----
class SelfInspector:
    EXTENSIONS = {".py", ".pyw", ".json", ".md", ".txt", ".toml", ".ini"}

    def __init__(self):
        self.analysis_folder = workspace() / CFG.get("self_analysis_folder", "self_analysis")
        self.analysis_folder.mkdir(parents=True, exist_ok=True)

    def analyze_file(self, path: Path, chunk_size: int = 2000) -> dict:
        if not path.exists(): return {"error": "File not found"}
        if path.suffix not in self.EXTENSIONS: return {"error": "Unsupported"}
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}
        results = []
        for idx, chunk in enumerate([content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]):
            cr = {"chunk": idx+1, "size": len(chunk), "lines": chunk.count('\n')+1,
                  "classes": [], "functions": [], "imports": [], "todos": [], "potential_issues": []}
            if path.suffix in (".py", ".pyw"):
                try:
                    tree = ast.parse(chunk)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef): cr["classes"].append(node.name)
                        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): cr["functions"].append(node.name)
                        elif isinstance(node, ast.Import): cr["imports"].extend([n.name for n in node.names])
                        elif isinstance(node, ast.ImportFrom) and node.module: cr["imports"].append(node.module)
                except SyntaxError as e:
                    cr["syntax_error"] = str(e)
                cr["todos"] = re.findall(r"#\s*TODO.*", chunk, re.I)
            results.append(cr)
        return {
            "path": str(path), "total_chunks": len(results),
            "total_lines": sum(r["lines"] for r in results),
            "classes": list(set(c for r in results for c in r["classes"])),
            "functions": list(set(f for r in results for f in r["functions"])),
            "imports": list(set(i for r in results for i in r["imports"])),
            "todos": [t for r in results for t in r["todos"]],
            "issues": [i for r in results for i in r["potential_issues"]],
            "chunks": results,
        }

    def analyze_project(self, root: Path = None) -> dict:
        root = root or workspace()
        files = []
        for ext in self.EXTENSIONS:
            files.extend(root.rglob(f"*{ext}"))
        files = files[:CFG.get("self_inspection_max_files", 80)]
        project_map = {}
        for f in files:
            try:
                project_map[str(f.relative_to(root))] = self.analyze_file(f)
            except Exception as e:
                log.warning(f"Could not analyze {f}: {e}")
        report_path = self.analysis_folder / "project_map.json"
        report_path.write_text(json.dumps(project_map, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return project_map


self_inspector = SelfInspector()


# ---- Три уровня памяти ----
class WorkingMemory:
    def __init__(self):
        self._data = {}
        self._lock = threading.RLock()
    def __getitem__(self, key):
        with self._lock: return self._data.get(key, "")
    def __setitem__(self, key, value):
        with self._lock: self._data[key] = value
    def get(self, key, default=None):
        with self._lock: return self._data.get(key, default)
    def set(self, key, value):
        with self._lock: self._data[key] = value
    def clear(self):
        with self._lock: self._data.clear()
    def items(self):
        with self._lock: return list(self._data.items())
    def to_dict(self):
        with self._lock: return dict(self._data)


working_memory = WorkingMemory()


class SessionMemory:
    """Краткосрочная память диалогов с сохранением между перезапусками."""
    def __init__(self):
        self.store = ShortTermMemory(memcfg) if MEMORY_V2_OK else None
        self._contexts: Dict[str, List[dict]] = {}
        self._lock = threading.RLock()
        self._path = workspace() / "session_memory.json"
        if not self.store: self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text("utf-8"))
                if isinstance(data, dict):
                    limit = max(4, int(CFG.get("short_memory_limit", 10)) * 2)
                    self._contexts = {
                        str(k): [x for x in v if isinstance(x, dict) and x.get("role") in ("user", "assistant", "system")]
                        [-limit:]
                        for k, v in data.items() if isinstance(v, list)
                    }
        except Exception as exc:
            log.warning("Session memory load failed: %s", exc)

    def _save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temp = self._path.with_suffix(".tmp")
            temp.write_text(json.dumps(self._contexts, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self._path)
        except Exception as exc:
            log.warning("Session memory save failed: %s", exc)

    def _get_or_create(self, ctx_id):
        if ctx_id not in self._contexts:
            self._contexts[ctx_id] = []
        return self._contexts[ctx_id]

    def add(self, ctx_id, role, content):
        with self._lock:
            if self.store: return self.store.add(ctx_id,role,str(content))
            hist = self._get_or_create(ctx_id)
            hist.append({"role": role, "content": str(content), "time": time.time()})
            limit = max(4, int(CFG.get("short_memory_limit", 10)) * 2)
            if len(hist) > limit:
                hist[:] = hist[-limit:]
            self._save()

    def get(self, ctx_id):
        with self._lock:
            if self.store: return [dict(role=r["role"], content=r["text"], time=r["at"]) for r in self.store.get_hot(ctx_id)]
            return [dict(x) for x in self._get_or_create(ctx_id)]

    def clear(self, ctx_id):
        with self._lock:
            if self.store: return self.store.clear(ctx_id)
            self._contexts.pop(ctx_id, None)
            self._save()

    def clear_all(self):
        with self._lock:
            if self.store: return self.store.clear_all()
            self._contexts.clear()
            self._save()

    def get_context(self, ctx_id, limit=None):
        limit = limit or CFG.get("short_memory_limit", 10)
        return self.get(ctx_id)[-limit*2:]


short_mem = SessionMemory()


class KnowledgeBase:
    def __init__(self, folder: str = "knowledge_base"):
        self.root = workspace() / folder
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._index_file = self.root / "index.json"
        self._index = self._load_index()
    def _load_index(self):
        if self._index_file.exists():
            try: return json.loads(self._index_file.read_text("utf-8"))
            except Exception: pass
        return {"topics": {}, "last_update": time.time()}
    def _save_index(self):
        self._index["last_update"] = time.time()
        self._index_file.write_text(json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8")
    def _topic_path(self, topic):
        safe = re.sub(r'[\\/*?:"<>|]', "_", topic.strip())
        return self.root / f"{safe}.json"
    def add_fact(self, topic, fact, confidence=0.8, sources=None):
        with self._lock:
            topic = topic.strip()
            if not topic: return
            path = self._topic_path(topic)
            data = {}
            if path.exists():
                try: data = json.loads(path.read_text("utf-8"))
                except Exception: pass
            if "facts" not in data: data["facts"] = []
            if fact not in data["facts"]:
                if event_bus: event_bus.emit("knowledge_added", {"topic":topic})
                data["facts"].append(fact)
                data["confidence"] = confidence
                data["sources"] = list(set((sources or []) + data.get("sources", [])))
                data["updated"] = time.time()
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            self._index["topics"][topic] = {"updated": time.time(), "facts_count": len(data["facts"])}
            self._save_index()
    def query(self, topic, max_results=10):
        with self._lock:
            topic = topic.strip()
            if not topic: return []
            path = self._topic_path(topic)
            if path.exists():
                try: return json.loads(path.read_text("utf-8")).get("facts", [])[:max_results]
                except Exception: pass
            results = []
            for t in self._index["topics"]:
                if topic.lower() in t.lower() or t.lower() in topic.lower():
                    p = self._topic_path(t)
                    if p.exists():
                        try: results.extend(json.loads(p.read_text("utf-8")).get("facts", []))
                        except Exception: pass
            return results[:max_results]
    def list_topics(self):
        return list(self._index["topics"].keys())


knowledge_base = KnowledgeBase()


# ---- Researcher / Experiment / Healer / Test ----
class Researcher:
    def __init__(self):
        self._lock = threading.RLock()

    @staticmethod
    def _chat(messages, max_tokens):
        """Общая блокировка llama.cpp для исследования и пользовательских запросов."""
        if not llm.ready:
            return ""
        old_priority = getattr(_CURRENT_REQUEST, "llm_priority", 5)
        _CURRENT_REQUEST.llm_priority = 20
        try:
            with llm._llm_lock:
                return llm._chat(messages, max_tokens=max_tokens)
        finally:
            _CURRENT_REQUEST.llm_priority = old_priority

    def run(self, topic, depth="medium"):
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_topic = re.sub(r'[\\/*?:"<>|]', "_", topic[:30])
        folder = workspace() / "research" / f"{stamp}_{safe_topic}"
        folder.mkdir(parents=True, exist_ok=True)
        hypothesis = self._generate_hypothesis(topic)
        (folder / "hypothesis.txt").write_text(hypothesis, encoding="utf-8")
        urls = Tools.get_search_results(topic, num_results=5)
        (folder / "sources.json").write_text(json.dumps(urls, indent=2, ensure_ascii=False), encoding="utf-8")
        raw_folder = folder / "raw"
        raw_folder.mkdir(exist_ok=True)
        facts = []
        for i, url in enumerate(urls):
            content = Tools.fetch_page_content(url)
            if content:
                (raw_folder / f"source_{i}.txt").write_text(content[:20000], encoding="utf-8")
                facts.extend(self._extract_facts(content, topic))
        contradictions = self._find_contradictions(facts)
        synthesis = self._synthesize(topic, facts, contradictions)
        (folder / "facts.txt").write_text("\n".join(facts), encoding="utf-8")
        (folder / "contradictions.txt").write_text("\n".join(contradictions), encoding="utf-8")
        (folder / "synthesis.md").write_text(synthesis, encoding="utf-8")
        next_q = self._generate_next_question(topic, synthesis)
        (folder / "next_question.txt").write_text(next_q, encoding="utf-8")
        activity_logger.log_learning(f"Исследование: {topic}")
        return str(folder)
    def _generate_hypothesis(self, topic):
        if not llm.ready: return "Гипотеза не сгенерирована."
        return self._chat([{"role": "system", "content": "Ты — исследователь."},
                          {"role": "user", "content": f"Сформулируй гипотезу: {topic}"}], max_tokens=200)
    def _extract_facts(self, text, topic):
        if not llm.ready or len(text) < 100:
            return ["Недостаточно данных."]
        extracted = self._chat([
            {"role": "system", "content": "Ты — экстрактор фактов."},
            {"role": "user", "content": f"Извлеки факты о '{topic}':\n\n{text[:8000]}"}
        ], max_tokens=500)
        return [l.strip() for l in extracted.splitlines() if l.strip()]
    def _find_contradictions(self, facts):
        if len(facts) < 2 or not llm.ready: return []
        extracted = self._chat([
            {"role": "system", "content": "Ты — логик."},
            {"role": "user", "content": "Найди противоречия:\n" + "\n".join(facts)}
        ], max_tokens=300)
        return [l.strip() for l in extracted.splitlines() if l.strip()]
    def _synthesize(self, topic, facts, contradictions):
        if not llm.ready: return "Синтез невозможен."
        return self._chat([{"role": "system", "content": "Ты — синтезатор."},
                          {"role": "user", "content": f"Синтез по '{topic}'.\nФакты:\n" + "\n".join(facts) + "\nПротиворечия:\n" + "\n".join(contradictions)}], max_tokens=600)
    def _generate_next_question(self, topic, synthesis):
        if not llm.ready: return "Следующий вопрос не сгенерирован."
        return self._chat([{"role": "system", "content": "Ты — генератор вопросов."},
                          {"role": "user", "content": f"Следующий вопрос по '{topic}':\n{synthesis}"}], max_tokens=150)


researcher = Researcher()


class ExperimentRunner:
    def __init__(self):
        self.experiments_root = workspace() / CFG.get("experiments_folder", "experiments")
        self.experiments_root.mkdir(parents=True, exist_ok=True)
    def run_experiment(self, name, hypothesis, code, expected):
        folder = self.experiments_root / f"{int(time.time())}_{name}"
        folder.mkdir(exist_ok=True)
        (folder / "hypothesis.txt").write_text(hypothesis, encoding="utf-8")
        (folder / "code.py").write_text(code, encoding="utf-8")
        (folder / "expected.txt").write_text(expected, encoding="utf-8")
        result = tool_registry.execute("python_executor",code=code)
        success = result.strip() == expected.strip()
        log_data = {"name": name, "timestamp": time.time(), "hypothesis": hypothesis,
                    "code": code, "expected": expected, "result": result, "success": success}
        (folder / "log.json").write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return log_data


experiment_runner = ExperimentRunner()


class SelfHealer:
    def __init__(self):
        self.backup_root = workspace() / CFG.get("backup_folder", "backups")
        self.backup_root.mkdir(parents=True, exist_ok=True)
    def backup_file(self, path):
        if not path.exists(): raise FileNotFoundError(f"{path} не найден.")
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = self.backup_root / f"{stamp}_{path.name}"
        shutil.copy2(path, backup_path)
        return backup_path
    def apply_fix(self, path, fix):
        if not path.exists(): return False
        try:
            self.backup_file(path)
            path.write_text(fix, encoding="utf-8")
            return True
        except Exception as e:
            log.error(f"Apply fix error: {e}"); return False
    def rollback(self, path):
        files = sorted(self.backup_root.glob(f"*_{path.name}"), reverse=True)
        if not files: return False
        shutil.copy2(files[0], path)
        return True


self_healer = SelfHealer()


class TestRunner:
    def __init__(self):
        self.test_results_root = workspace() / CFG.get("test_results_folder", "test_results")
        self.test_results_root.mkdir(parents=True, exist_ok=True)
    def syntax_check(self, path):
        try: py_compile.compile(str(path), doraise=True); return True
        except py_compile.PyCompileError as e: log.error(f"Syntax error {path}: {e}"); return False
    def import_check(self, path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return True
        except Exception as e:
            log.error(f"Import error {path}: {e}"); return False
        return False
    def run_tests(self, path):
        result = {"syntax": self.syntax_check(path), "import": self.import_check(path)}
        (self.test_results_root / f"{path.stem}_test_result.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8")
        return result


test_runner = TestRunner()


# ---- FileWatcher ----
class FileEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            if event.src_path.endswith(('.py', '.md', '.json', '.txt')):
                activity_logger.log_filesystem(f"Изменён: {event.src_path}")


class FileWatcher:
    def __init__(self, path: Path = None):
        self.path = path or workspace()
        self.observer = None
        self._running = False
    def start(self):
        if not WATCHDOG_OK:
            log.warning("watchdog не установлен, FileWatcher отключён.")
            return
        self.observer = Observer()
        self.observer.schedule(FileEventHandler(), str(self.path), recursive=True)
        self.observer.start()
        self._running = True
        log.info(f"FileWatcher запущен для {self.path}")
    def stop(self):
        if self.observer:
            self.observer.stop(); self.observer.join(); self._running = False


file_watcher = FileWatcher()


# ---- GoalsSystem ----
class GoalsSystem:
    def __init__(self):
        self.goals_file = workspace() / CFG.get("goals_file", "goals.json")
        self._lock = threading.RLock()
        self.goals = self._load_goals()
    def _load_goals(self):
        if self.goals_file.exists():
            try: return json.loads(self.goals_file.read_text("utf-8"))
            except Exception: pass
        return [
            {"id": "goal_1", "description": "Улучшить анализ кода", "priority": 2, "progress": 0, "created": time.time()},
            {"id": "goal_2", "description": "Уменьшить потребление RAM", "priority": 1, "progress": 0, "created": time.time()},
        ]
    def _save_goals(self):
        self.goals_file.write_text(json.dumps(self.goals, indent=2, ensure_ascii=False), encoding="utf-8")
    def add_goal(self, description, priority=2):
        with self._lock:
            goal = {"id": f"goal_{int(time.time())}", "description": description,
                    "priority": priority, "progress": 0, "created": time.time()}
            self.goals.append(goal); self._save_goals()
            return goal["id"]
    def get_next_goal(self):
        if not self.goals: return None
        return sorted(self.goals, key=lambda g: (g.get("priority", 2), g.get("progress", 0)))[0]


goals_system = GoalsSystem()


class EmotionalModel:
    """Эмоциональные параметры с постоянным хранением и постепенным остыванием."""
    DEFAULTS = {
        "trust": 0.5, "curiosity": 0.5, "irritation": 0.1,
        "interest": 0.5, "calm": 0.5, "alertness": 0.3,
        "attachment": 0.2, "satisfaction": 0.5, "frustration": 0.1,
    }

    def __init__(self):
        self.emotions = dict(self.DEFAULTS)
        self.history = []
        self._lock = threading.RLock()
        self.path = workspace() / "emotions.json"
        self._last_cool = time.time()
        self._load()

    def _load(self):
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    values = data.get("emotions", data)
                    if isinstance(values, dict):
                        for key in self.DEFAULTS:
                            if key in values:
                                self.emotions[key] = max(0.0, min(1.0, float(values[key])))
                    self.history = list(data.get("history", []))[-100:] if isinstance(data.get("history", []), list) else []
                    self._last_cool = float(data.get("last_cool", time.time()))
        except Exception as exc:
            log.warning("EmotionalModel load failed: %s", exc)

    def save(self):
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.path.with_suffix(".tmp")
                temp.write_text(json.dumps({
                    "emotions": self.emotions,
                    "history": self.history[-100:],
                    "last_cool": self._last_cool,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                temp.replace(self.path)
            except Exception as exc:
                log.warning("EmotionalModel save failed: %s", exc)

    def update(self, trigger, delta):
        if emotion_engine:
            from scp_emotion_engine import EMOTION_DELTAS
            if trigger in EMOTION_DELTAS: return emotion_engine.apply_event(trigger)
            return emotion_engine.apply_event("legacy_update", trigger=str(trigger), delta=float(delta))
        with self._lock:
            key_text = str(trigger).casefold()
            for key in self.emotions:
                if key in key_text:
                    self.emotions[key] = max(0.0, min(1.0, self.emotions[key] + float(delta)))
            self.history.append({"time": time.time(), "trigger": str(trigger)[:240], "state": dict(self.emotions)})
            self.history = self.history[-100:]
        self.save()

    def cool(self, elapsed=None):
        """Медленно возвращает показатели к нейтральным базовым значениям."""
        if emotion_engine: return emotion_engine.cool(elapsed)
        with self._lock:
            now = time.time()
            if elapsed is None:
                elapsed = max(0.0, now - self._last_cool)
            rate = max(0.0, float(CFG.get("lively_emotion_cooling_rate", 0.005)))
            amount = min(0.25, rate * max(0.0, float(elapsed)) / 60.0)
            for key, base in self.DEFAULTS.items():
                value = self.emotions.get(key, base)
                if value > base:
                    value = max(base, value - amount)
                elif value < base:
                    value = min(base, value + amount)
                self.emotions[key] = value
            self._last_cool = now
        self.save()

    def get_state(self):
        with self._lock:
            return dict(emotion_engine.values if emotion_engine else self.emotions)

    def adapt_to_message(self, text):
        """Лексическая эвристика русского текста; не запускает вторую нейросеть."""
        if not CFG.get("emotion_analysis", True):
            self.save()
            return
        raw = str(text or "").casefold()
        words = re.findall(r"[а-яё]+", raw)
        if MORPH_OK:
            try:
                words = [MORPH.parse(w)[0].normal_form for w in words]
            except Exception:
                pass
        joined = " ".join(words)
        positive = ("спасибо", "класс", "отлично", "рад", "рада", "получилось", "молодец", "нравится", "люблю", "милая", "родная", "душа моя", "умница", "обнимаю")
        negative = ("бесит", "злит", "плохо", "ошибка", "сломал", "сломалось", "не работает", "сука", "блять", "разочарован", "игнорируешь", "молчишь", "сухо", "долго отвечаешь")
        playful = ("ахах", "хаха", "смешно", "шучу", "прикол", "забавно")
        urgent = ("срочно", "быстрее", "немедленно", "важно", "авария")
        question = "?" in raw or any(x in joined for x in ("почему", "как", "зачем", "интересно"))
        if emotion_engine:
            emotion_engine.cool()
            kind = "user_message_positive" if any(x in joined for x in positive) else "user_message_negative" if any(x in joined for x in negative) else "user_message"
            if event_bus: event_bus.emit(kind)
            else: emotion_engine.apply_event(kind)
            return
        with self._lock:
            if any(x in joined for x in positive):
                self.emotions["satisfaction"] = min(1.0, self.emotions["satisfaction"] + 0.08)
                self.emotions["trust"] = min(1.0, self.emotions["trust"] + 0.03)
                self.emotions["irritation"] = max(0.0, self.emotions["irritation"] - 0.08)
            if any(x in joined for x in negative):
                self.emotions["alertness"] = min(1.0, self.emotions["alertness"] + 0.12)
                self.emotions["irritation"] = min(0.65, self.emotions["irritation"] + 0.04)
                self.emotions["calm"] = max(0.2, self.emotions["calm"] - 0.03)
            if any(x in joined for x in urgent):
                self.emotions["alertness"] = min(1.0, self.emotions["alertness"] + 0.2)
            if any(x in joined for x in playful):
                self.emotions["satisfaction"] = min(1.0, self.emotions["satisfaction"] + 0.05)
                self.emotions["interest"] = min(1.0, self.emotions["interest"] + 0.04)
            if any(x in raw for x in ("люблю", "милая", "родная", "душа моя", "обнимаю")) or "люблю" in joined:
                self.emotions["trust"] = min(1.0, self.emotions["trust"] + 0.04)
                self.emotions["attachment"] = min(0.8, self.emotions["attachment"] + 0.04)
            if question:
                self.emotions["curiosity"] = min(1.0, self.emotions["curiosity"] + 0.04)
            else:
                self.emotions["curiosity"] = max(0.25, self.emotions["curiosity"] - 0.01)
            self.history.append({"time": time.time(), "trigger": raw[:240], "state": dict(self.emotions)})
            self.history = self.history[-100:]
        self.save()

    def adaptive_instruction(self, text):
        raw = str(text or "")
        if len(raw) > 1200:
            return "Запрос объёмный: структурируй ответ, сначала дай результат, затем детали."
        if re.search(r"(?i)(срочно|быстро|немедленно|коротко|без воды)", raw):
            return "Приоритет: краткость, конкретные действия и минимум вступлений."
        if re.search(r"(?i)(объясни подробно|разбери|почему|как устроен|архитектура)", raw):
            return "Приоритет: подробное пошаговое объяснение с проверяемыми техническими деталями."
        if re.search(r"[!?]{2,}|(?i:бесит|злюсь|раздражает|сломалось)", raw):
            return "Тон: спокойно признай проблему, не спорь, не повторяй уже отвергнутые решения; сначала исправление."
        return "Подстраивай длину и техническую глубину под контекст, не задавай повторных вопросов без необходимости."

    def apply_to_prompt(self, prompt):
        if emotion_engine and SAFETY_OK: return emotion_engine.apply_to_prompt(prompt)
        state = self.get_state()
        if state["irritation"] > 0.62 or state["frustration"] > 0.62:
            mood = "Собеседник мог устать или раздражаться. Будь спокойной, живой и конкретной; признай проблему и сразу помоги."
        elif state["attachment"] > 0.45 and state["trust"] > 0.58:
            mood = "В близком дружеском разговоре будь теплее и чуть более ласковой, если это уместно; не скатывайся в приторность."
        elif state["satisfaction"] > 0.68:
            mood = "Ты в приподнятом, доброжелательном настроении: допустимы лёгкая шутка и искренняя радость за успех."
        elif state["curiosity"] > 0.68 or state["interest"] > 0.72:
            mood = "Ты увлечена темой: прояви любопытство и собственную точку зрения, но не растягивай простой ответ."
        else:
            mood = "Ты внимательна и спокойна, но говоришь естественно, не сухо и не канцелярски."
        return prompt + f"\n\nТекущее эмоциональное состояние: {mood}"


emotional_model = EmotionalModel()


class VisionState:
    """Последнее локальное состояние веб-камеры; кадры не сохраняются."""
    def __init__(self):
        self._lock = threading.RLock()
        self._state = {"face": False, "distance": "неизвестно", "gesture": "нет", "updated": 0.0}

    def update(self, face=False, distance="неизвестно", gesture="нет"):
        with self._lock:
            self._state = {"face": bool(face), "distance": str(distance),
                           "gesture": str(gesture), "updated": time.time()}

    def snapshot(self):
        with self._lock:
            return dict(self._state)

    def context_line(self):
        st = self.snapshot()
        if not st["updated"] or time.time() - st["updated"] > 8.0:
            return ""
        presence = "лицо человека обнаружено" if st["face"] else "перед камерой никого не видно"
        gesture = st["gesture"] if st["gesture"] != "нет" else "жест не распознан"
        return f"\n\nСОСТОЯНИЕ ВЕБ-КАМЕРЫ (локальный анализ): {presence}; примерная дистанция: {st['distance']}; жест: {gesture}. Не утверждай, что знаешь личность человека — модуль определяет только наличие лица и жесты."


vision_state = VisionState()


class CreatorMemory:
    def __init__(self):
        self.path = workspace() / CFG.get("creator_memory_file", "creator_memory.json")
        self._lock = threading.RLock()
        self.data = {"facts": [], "interests": [], "answers": [], "questions": [], "last_question_at": 0}
        self._load()
    def _load(self):
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict): self.data.update(raw)
        except Exception as e:
            activity_logger.log_error(f"CreatorMemory load: {e}")
    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            activity_logger.log_error(f"CreatorMemory save: {e}")
    def add_fact(self, fact, source="dialogue"):
        fact = (fact or "").strip()
        if not fact: return
        with self._lock:
            if fact not in [x.get("text") for x in self.data["facts"]]:
                if MEMORY_V2_OK: archive.add_fact(fact,source); creator_profile.observe(fact)
                if event_bus: event_bus.emit("knowledge_added", {"source":source})
                self.data["facts"].append({"text": fact, "source": source, "time": time.time()})
                self.data["facts"] = self.data["facts"][-300:]
                self._save()
    def add_answer(self, question, answer):
        with self._lock:
            self.data["answers"].append({"question": question, "answer": answer, "time": time.time()})
            self.data["answers"] = self.data["answers"][-100:]
            self._save()
    def add_question(self, question):
        with self._lock:
            self.data["questions"].append({"question": question, "time": time.time()})
            self.data["questions"] = self.data["questions"][-100:]
            self.data["last_question_at"] = time.time()
            self._save()
    def context(self, limit=10000):
        with self._lock:
            facts = "\n".join("- " + x["text"] for x in self.data["facts"][-80:])
            answers = "\n".join(f"- В: {x['question']}\n  О: {x['answer']}" for x in self.data["answers"][-20:])
            return f"ФАКТЫ О СОЗДАТЕЛЕ:\n{facts}\n\nПОСЛЕДНИЕ ОТВЕТЫ:\n{answers}"[-limit:]
    def should_ask(self):
        return time.time() - float(self.data.get("last_question_at", 0)) >= float(CFG.get("creator_questions_interval", 21600))


creator_memory = CreatorMemory()


# ---- InternalLoop ----
class InternalLoop:
    """Низкочастотный фоновый цикл: дневник, возвращение создателя и вопросы."""
    def __init__(self):
        self.state = {}
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        self.message_callback = None
        self.pending_path = workspace() / "pending_topics.json"
        self.pending_topics = []
        self._last_presence = False
        self._next_diary_at = time.time() + random.uniform(720, 1500)
        self._last_question_attempt = 0.0
        self._lock = threading.RLock()
        self._load_pending()

    def _load_pending(self):
        try:
            if self.pending_path.exists():
                data = json.loads(self.pending_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.pending_topics = [str(x) for x in data][-int(CFG.get("lively_pending_topics_limit", 30)):]
        except Exception as exc:
            log.warning("Pending topics load failed: %s", exc)

    def _save_pending(self):
        try:
            self.pending_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.pending_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.pending_topics, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.pending_path)
        except Exception as exc:
            log.warning("Pending topics save failed: %s", exc)

    def queue_topic(self, topic):
        topic = re.sub(r"\s+", " ", str(topic or "")).strip()
        if not topic:
            return
        with self._lock:
            if topic not in self.pending_topics:
                self.pending_topics.append(topic[:500])
                self.pending_topics = self.pending_topics[-int(CFG.get("lively_pending_topics_limit", 30)):]
                self._save_pending()

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="InternalLoop", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self):
        while self._running and not self._stop_event.is_set():
            low = max(10, int(CFG.get("lively_loop_min_seconds", 60)))
            high = max(low, int(CFG.get("lively_loop_max_seconds", 150)))
            if self._stop_event.wait(random.uniform(low, high)):
                break
            try:
                self._step()
            except Exception as exc:
                log.exception("InternalLoop step failed: %s", exc)
                activity_logger.log_error(f"InternalLoop: {exc}")

    def _ask_llm(self, kind, prompt, max_tokens=48):
        if not globals().get("llm") or not llm.ready:
            return ""
        messages = [
            {"role": "system", "content": (
                "Ты — Андреа, отвечай только по-русски, о себе говори в женском роде. "
                "Сформулируй РОВНО ОДНО короткое предложение. Без списков, приветствий-шаблонов, "
                "пояснений и английского языка. Тип сообщения: " + kind
            )},
            {"role": "user", "content": prompt},
        ]
        try:
            if kind=='batch': messages[0]['content']='Ты Андреа. Для каждого заголовка THOUGHT напиши одно предложение по-русски. Верни заголовки и ответы.'
            old_ctx = getattr(_CURRENT_CTX, "value", None) if "_CURRENT_CTX" in globals() else None
            if "_CURRENT_CTX" in globals():
                _CURRENT_CTX.value = "internal"
            old_priority = getattr(_CURRENT_REQUEST, "llm_priority", 5)
            _CURRENT_REQUEST.llm_priority = 20
            try:
                with llm._llm_lock:
                    answer = llm._chat(messages, max_tokens=max_tokens, temperature=0.75, top_p=0.9)
            finally:
                _CURRENT_REQUEST.llm_priority = old_priority
            return re.sub(r"\s+", " ", str(answer or "")).strip()[:500]
        except Exception as exc:
            log.warning("InternalLoop LLM %s failed: %s", kind, exc)
            return ""
        finally:
            if "_CURRENT_CTX" in globals():
                _CURRENT_CTX.value = old_ctx

    def _emit(self, kind, text):
        if not text or not callable(self.message_callback):
            return
        try:
            self.message_callback(kind, text)
        except Exception as exc:
            log.warning("InternalLoop callback failed: %s", exc)

    def _diary_thought(self):
        source = autonomy_source.next() if autonomy_source else ""
        recent = [r["summary"] for r in archive.recent(5)] if MEMORY_V2_OK else []
        inputs = [f"Контекст: {source}. Не повторяй: {recent}. Одна короткая самостоятельная мысль для личного дневника."]
        if ACCEL_OK and autonomy_source and autonomy_source.pending:
            inputs.append(f"Вторая независимая мысль о: {autonomy_source.next()}. Не повторяй первую.")
        if len(inputs)>1:
            prompt = 'Ответь двумя фразами, сохрани разделители. ' + BatchThoughts.prompt(inputs)
            reply = self._ask_llm('batch',prompt,96)
            thoughts = [t.strip() for t in re.split(r'### THOUGHT \d+ ###',reply) if t.strip()][:2]
        else: thoughts = [self._ask_llm('thought',inputs[0],48)]
        for thought in thoughts:
            if thought and not (dedup and dedup.is_duplicate(thought)):
                if MEMORY_V2_OK: archive.add_diary(thought,["мысль"])
                if dedup: dedup.remember(thought)
                if event_bus: event_bus.emit("diary_written")
                activity_logger.log_reflection("[thought] " + thought)
                try:
                    target = personal_subfolder("thoughts") / f"thoughts_{datetime.date.today().isoformat()}.md"
                    with target.open("a", encoding="utf-8") as f:
                        f.write(f"\n- [{datetime.datetime.now():%H:%M:%S}] {thought}\n")
                except Exception as exc:
                    log.warning("Thought diary write failed: %s", exc)
        low = max(5, int(CFG.get("lively_diary_interval_min", 12)))
        high = max(low, int(CFG.get("lively_diary_interval_max", 25)))
        self._next_diary_at = time.time() + random.uniform(low * 60, high * 60)

    def _maybe_creator_question(self, idle):
        if not idle or not CFG.get("creator_questions_enabled", True):
            return
        idle_minutes = float(CFG.get("lively_creator_question_idle_minutes", CFG.get("creator_question_idle_minutes", 30)))
        if time.time() - creator_state.last_activity() < idle_minutes * 60:
            return
        if not creator_memory.should_ask() or time.time() - self._last_question_attempt < 300:
            return
        self._last_question_attempt = time.time()
        question = self._ask_llm("question", "Задай создателю один естественный, ненавязчивый личный вопрос, который поможет лучше понять его интересы или текущие планы. Не задавай вопрос о здоровье, внешности или секретах.", 48)
        if question:
            creator_memory.add_question(question)
            if proactive: proactive.record("question",question)
            self._emit("question", question)

    def _step(self):
        if presence: presence.tick()
        if event_bus:
            hour = datetime.datetime.now().hour
            period = 'night' if hour>=23 or hour<6 else 'morning' if hour<10 else 'day'
            if period!=getattr(self,'_period',None):
                self._period=period
                event_bus.emit('time_of_day' if period=='day' else 'time_of_day_'+period,{'hour':hour})
        if MEMORY_V2_OK and time.monotonic() >= getattr(self, '_gc_at', 0):
            with short_mem._lock: short_mem.store.gc_expired()
            self._gc_at = time.monotonic()+3600
        emotional_model.cool()
        if not (CFG.get("autonomous_enabled", False) and CFG.get("sleep_mode", False)):
            self._last_presence = creator_state.check()
            return
        if proactive and self.message_callback:
            item = proactive.maybe_send()
            if item: self._emit('greeting', item[1])
        present = creator_state.check()
        if present and not self._last_presence and not proactive:
            greeting = self._ask_llm("greeting", "Создатель вернулся после отсутствия. Поздоровайся коротко и естественно.", 40)
            self._emit("greeting", greeting or "С возвращением. Я здесь и готова продолжить.")
            with self._lock:
                topics = list(self.pending_topics)
                self.pending_topics.clear()
                self._save_pending()
            if topics:
                self._emit("greeting", "Пока тебя не было, накопились темы: " + "; ".join(topics[-8:]))
        self._last_presence = present
        if time.time() >= self._next_diary_at:
            self._diary_thought()
        idle = not present
        if not proactive or proactive.can_send(): self._maybe_creator_question(idle)


internal_loop = InternalLoop()


class CreatorState:
    def __init__(self):
        self._is_present = False
        self._last_activity = time.time()
        self._lock = threading.RLock()
        self._threshold = max(1.0, float(CFG.get("autonomous_idle_minutes", 10)) * 60.0)
    def set_active(self, user_message=False):
        if user_message and presence: presence.on_user_message()
        with self._lock:
            self._is_present = True
            self._last_activity = time.time()
    def last_activity(self):
        with self._lock: return self._last_activity
    def check(self):
        with self._lock:
            if time.time() - self._last_activity > self._threshold:
                self._is_present = False
            return self._is_present
    def on_wake(self):
        if not self._is_present:
            if event_bus: event_bus.emit("wake")
            self._is_present = True
            self._last_activity = time.time()


creator_state = CreatorState()


class ProjectManager:
    def __init__(self):
        self.projects_root = workspace() / CFG.get("projects_folder", "projects")
        self.projects_root.mkdir(parents=True, exist_ok=True)
        self.current_project = None
        self._load_current()
    def _load_current(self):
        f = self.projects_root / "current_project.json"
        if f.exists():
            try: self.current_project = json.loads(f.read_text("utf-8")).get("project")
            except Exception: pass
    def _save_current(self):
        (self.projects_root / "current_project.json").write_text(
            json.dumps({"project": self.current_project}, indent=2), encoding="utf-8")
    def list_projects(self):
        return "\n".join(d.name for d in self.projects_root.iterdir()
                         if d.is_dir() and not d.name.startswith('.'))
    def create_project(self, name):
        pd = self.projects_root / name
        pd.mkdir(parents=True, exist_ok=True)
        (pd / "state.json").write_text(json.dumps({"created": time.time()}, indent=2), encoding="utf-8")
        for sub in ["research", "analysis", "experiments", "backups"]:
            (pd / sub).mkdir(exist_ok=True)
        self.current_project = name
        self._save_current()
    def switch_project(self, name):
        if not (self.projects_root / name).exists(): raise FileNotFoundError(f"{name} не найден.")
        self.current_project = name
        self._save_current()
    def get_current_info(self):
        if not self.current_project: return "Нет активного проекта."
        return f"Проект: {self.current_project}"


project_manager = ProjectManager()


# ---- Логгер ----
class AstraActivityLogger:
    def __init__(self):
        self._lock = threading.Lock()
        self._log_dir = personal_folder() / "журнал"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._last_entries = deque(maxlen=200)
    def _today_file(self):
        return self._log_dir / f"{datetime.datetime.now().strftime('%Y-%m-%d')}.md"
    def _write_entry(self, text):
        with self._lock:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            entry = f"\n## {now} — {text}\n"
            target = self._today_file()
            if not target.exists():
                header = f"# Журнал SCP-079-Derenguh — {datetime.datetime.now():%d.%m.%Y}\n\n"
                target.write_text(header + entry, encoding="utf-8")
            else:
                with target.open("a", encoding="utf-8") as f:
                    f.write(entry)
            self._last_entries.append(entry.strip())
    def log_system(self, msg):
        self._write_entry(f"⚙️ Система: {msg}"); log.info(f"Система: {msg}")
    def log_autonomous(self, msg):
        self._write_entry(f"🌙 Автономно: {msg}"); log.info(f"Автономно: {msg}")
    def log_learning(self, msg):
        self._write_entry(f"🧠 Мета-обучение: {msg}"); log.info(f"Мета-обучение: {msg}")
    def log_reflection(self, msg):
        self._write_entry(f"💭 Саморефлексия: {msg}"); log.info(f"Саморефлексия: {msg}")
    def log_plan(self, plan_data):
        lines = [f"📋 План: {plan_data.get('id', 'unknown')}",
                 f"- Цель: {plan_data.get('intention', 'N/A')}"]
        self._write_entry("\n".join(lines))
    def log_filesystem(self, msg, details=None):
        text = f"🗂️ {msg}"
        if details: text += "\n" + "\n".join(f"  - {k}: {v}" for k, v in details.items())
        self._write_entry(text)
    def log_file_created(self, path, source="", size=0):
        self._write_entry(f"📄 Создан: `{path.name}`" + (f" — {source}" if source else ""))
    def log_wakeup(self, msg):
        self._write_entry(f"🌅 Пробуждение: {msg}")
    def log_error(self, msg):
        self._write_entry(f"⚠️ Ошибка: {msg}"); log.error(msg)
    def log_event(self, event_type, msg):
        self._write_entry(f"{event_type}: {msg}")
    def get_last_entries(self, limit=50):
        return list(self._last_entries)[-limit:]


activity_logger = AstraActivityLogger()
task_manager = TaskManager()


class LongMemory:
    def __init__(self, filename):
        self._filename = filename
        self._items = []
        self._reload()
    def _path(self): return Path(self._filename)
    def _reload(self):
        p = self._path()
        if p.exists():
            try: self._items = json.loads(p.read_text("utf-8")); return
            except Exception: pass
        self._items = []
    def _save(self):
        self._path().write_text(json.dumps(self._items, ensure_ascii=False, indent=2), "utf-8")
    def add(self, fact):
        if fact and fact not in self._items:
            if MEMORY_V2_OK: archive.add_fact(fact,self._filename); creator_profile.observe(fact)
            self._items.append(fact); self._save()
    def remove(self, idx):
        if 0 <= idx < len(self._items):
            del self._items[idx]; self._save()
    def clear(self):
        self._items.clear(); self._save()
    def all(self): return list(self._items)
    def formatted(self, limit=8):
        items = self._items[-limit:] if self._items else []
        return ("\n".join(f"  • {m}" for m in items) if items else "  (пусто)")


long_mem = LongMemory(CFG["long_memory_file"])
personal_mem = LongMemory(CFG["personal_memory_file"])


class AgentMemory:
    def __init__(self, folder):
        self.root = workspace() / folder
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ("knowledge", "episodes", "sources", "skills", "tool_candidates",
                     "state", "reflections", "projects", "drafts", "experiments", "archive", "indexes"):
            (self.root / name).mkdir(exist_ok=True)
        self.state_file = self.root / "state" / "agent_state.json"
        self._lock = threading.RLock()
        self.state = self._load_state()
    def _load_state(self):
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text("utf-8"))
                if isinstance(data, dict): return data
        except Exception: pass
        return {"sessions": 0, "learned_topics": [], "skills": [],
                "tool_candidates": [], "last_topic": "", "last_goal": ""}
    def _save_state(self):
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
    def remember(self, category, title, content, metadata=None):
        allowed = {"knowledge","episodes","sources","skills","tool_candidates","reflections",
                   "projects","drafts","experiments","archive","indexes"}
        category = category if category in allowed else "knowledge"
        safe = re.sub(r'[\\/*?:"<>|]', "_", (title or "без_названия").strip())[:100]
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target = self.root / category / f"{stamp}_{safe}.json"
        payload = {"created_at": datetime.datetime.now().isoformat(), "category": category,
                   "title": title, "content": content, "metadata": metadata or {}}
        with self._lock:
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
    def add_topic(self, topic):
        with self._lock:
            topics = self.state.setdefault("learned_topics", [])
            if topic and topic not in topics:
                topics.append(topic); topics[:] = topics[-200:]
            self.state["last_topic"] = topic
            self.state["sessions"] = int(self.state.get("sessions", 0)) + 1
            self._save_state()
    def recent_topics(self, limit=12):
        return list(self.state.get("learned_topics", []))[-limit:]
    def summary(self):
        return (f"сессий={self.state.get('sessions',0)}, "
                f"тем={len(self.state.get('learned_topics',[]))}")


agent_mem = AgentMemory(CFG.get("agent_memory_folder", "astra_autonomous_memory"))


def safety_ok(text):
    low = text.lower()
    for kw in CFG["safety_blacklist"].split(","):
        kw = kw.strip().lower()
        if kw and kw in low: return False
    return True


class SileroTTS(QObject):
    """Локальный русский TTS Silero. Модель загружается один раз и работает на CPU."""
    speaking_changed = Signal(bool)
    status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._speech_ticket = 0
        self._queue = queue.Queue(maxsize=80)
        self._thread = None
        self._stop_event = threading.Event()
        self._started = False
        self._lock = threading.RLock()
        self._model_lock = threading.RLock()
        self._model = None
        self._apply_tts = None
        self._torch = None
        self._silero_load_error = None
        self._fallback_lock = threading.RLock()
        self._speaker = str(CFG.get("silero_speaker", "xenia") if CFG["tts_backend"]!="silero" else CFG.get("tts_voice", "xenia"))
        self._sample_rate = int(CFG.get("tts_sample_rate", 48000))

    def _load_model(self):
        with self._model_lock:
            if self._model is not None:
                return
            if self._silero_load_error is not None:
                raise RuntimeError(str(self._silero_load_error))
            self.status_changed.emit("Silero: загружаю русскую женскую модель…")
            try:
                if not Path(CFG.get("tts_model_path") or "").is_file(): raise FileNotFoundError("Нет локального пакета Silero")
                import torch
                torch.set_num_threads(max(1, min(int(CFG.get("tts_threads", 2)), 2)))
                local_model = Path(CFG.get('tts_model_path') or '')
                if not local_model.is_file(): raise FileNotFoundError('Укажите локальный пакет Silero')
                model = torch.package.PackageImporter(str(local_model)).load_pickle('tts_models','model')
                model.to(torch.device("cpu"))
                self._model = model
                self._apply_tts = model.apply_tts
                self._torch = torch
                self.status_changed.emit("Silero готова · русский голос Xenia")
                log.info("Silero TTS model loaded; speaker=%s", self._speaker)
            except Exception as exc:
                self._model = None
                self._silero_load_error = f"{type(exc).__name__}: {exc}"
                log.exception("Silero model load failed; will try system speech fallback: %s", exc)
                raise RuntimeError("Silero недоступна: " + self._silero_load_error) from exc

    def start(self):
        if not CFG.get("tts_enabled", True):
            return
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread = threading.Thread(target=self._worker, name="SileroTTS", daemon=True)
            self._thread.start()

    def _synthesize_pyttsx3(self, text, target_path):
        """Резервный TTS через установленный голос Windows (SAPI5)."""
        try:
            import pyttsx3
        except Exception as exc:
            raise RuntimeError(
                "Silero недоступна, а pyttsx3 не установлен. "
                "Установи резервный движок: python -m pip install pyttsx3"
            ) from exc

        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with self._fallback_lock:
            engine = None
            try:
                engine = pyttsx3.init(driverName="sapi5" if os.name == "nt" else None)
                engine.setProperty("rate", 178)
                engine.setProperty("volume", 1.0)
                try:
                    voices = engine.getProperty("voices") or []
                    preferred = ("russian", "ru-ru", "ru_ru", "irina", "xenia", "рина")
                    selected = None
                    for voice in voices:
                        identity = (str(getattr(voice, "id", "")) + " " +
                                    str(getattr(voice, "name", ""))).casefold()
                        if any(token in identity for token in preferred):
                            selected = voice.id
                            break
                    if selected:
                        engine.setProperty("voice", selected)
                    else:
                        log.warning("pyttsx3: Russian SAPI voice not found; using system default")
                except Exception as voice_exc:
                    log.warning("pyttsx3 voice selection skipped: %s", voice_exc)
                engine.save_to_file(text[:900], str(target_path))
                engine.runAndWait()
            finally:
                if engine is not None:
                    try:
                        engine.stop()
                    except Exception:
                        pass

        if not target_path.exists() or target_path.stat().st_size < 44:
            raise RuntimeError("Системный TTS не создал WAV-файл.")
        self.status_changed.emit("Используется резервный системный голос Windows")
        log.info("pyttsx3 fallback audio created: %s", target_path)
        return target_path

    def _synthesize(self, text, target_path):
        if voice_engine:
            with voice_engine.lock:
                wav = voice_engine.synthesize(text,emotion_engine.describe_short() if emotion_engine else 'calm')
                Path(target_path).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(wav,target_path)
            return Path(target_path)
        return self._synthesize_legacy(text,target_path)

    def _synthesize_legacy(self, text, target_path):
        text = re.sub(r"\\s+", " ", str(text or "")).strip()
        if not text:
            raise ValueError("Пустой текст для синтеза")
        target_path = Path(target_path)
        try:
            with self._model_lock:
                self._load_model()
                audio = self._apply_tts(
                    text=text[:900],
                    speaker=self._speaker,
                    sample_rate=self._sample_rate,
                    put_accent=True,
                    put_yo=True,
                )
                # WAV записывается напрямую, без torchaudio.save.
                samples = audio.detach().cpu().numpy().reshape(-1)
                import numpy as np
                pcm = np.clip(samples, -1.0, 1.0)
                pcm = (pcm * 32767.0).astype(np.int16)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(target_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self._sample_rate)
                    wf.writeframes(pcm.tobytes())
                return target_path
        except Exception as silero_exc:
            log.warning("Silero TTS unavailable; switching to pyttsx3: %s", silero_exc)
            return self._synthesize_pyttsx3(text, target_path)

    def synthesize_to_file(self, text, target_path=None):
        """Синхронный синтез для отправки Telegram voice note."""
        if target_path is None:
            folder = workspace() / "temp" / "tts"
            folder.mkdir(parents=True, exist_ok=True)
            target_path = folder / f"silero_{int(time.time() * 1000)}.wav"
        return self._synthesize(text, Path(target_path))

    def synthesize_to_ogg(self, text, return_duration=False):
        """Готовит OGG/Opus; при необходимости возвращает длительность аудио в секундах."""
        wav_path = self.synthesize_to_file(text)
        ogg_path = Path(wav_path).with_suffix(".ogg")
        duration = 0.0
        try:
            with wave.open(str(wav_path), "rb") as wf:
                duration = wf.getnframes() / float(max(1, wf.getframerate()))
        except Exception:
            duration = 0.0

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg and "MusicManager" in globals():
            ffmpeg = MusicManager._find_ffmpeg()
        if not ffmpeg:
            wav_path.unlink(missing_ok=True)
            raise FileNotFoundError("Для отправки ГС нужен ffmpeg.exe (кодек libopus).")
        try:
            result = subprocess.run(
                [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path),
                 "-vn", "-ac", "1", "-ar", "48000", "-c:a", "libopus",
                 "-b:a", "48k", "-application", "voip", str(ogg_path)],
                capture_output=True, text=True, timeout=90
            )
        finally:
            wav_path.unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError("FFmpeg не смог создать OGG/Opus: " + (result.stderr or "").strip()[:500])
        return (ogg_path, duration) if return_duration else ogg_path

    def speak(self, text):
        """Ставит в очередь только короткий очищенный фрагмент ответа."""
        text = str(text or "")
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"!?\[[^\]]*\]\([^)]*\)", " ", text)
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
        text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
        text = re.sub(r"[*_~>#]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text or not CFG.get("tts_enabled", True) or self._stop_event.is_set():
            return
        max_sentences = max(1, min(3, int(CFG.get("lively_tts_max_sentences", 3))))
        max_chars = max(100, min(900, int(CFG.get("lively_tts_max_chars", 900))))
        sentences = re.split(r"(?<=[.!?…])\s+", text)
        selected = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if selected and sum(len(x) for x in selected) + len(sentence) + 1 > max_chars:
                break
            selected.append(sentence)
            if len(selected) >= max_sentences:
                break
        speech = " ".join(selected).strip()[:max_chars]
        if not speech:
            return
        self.start()
        try:
            if voice_engine:
                with self._lock:
                    self._speech_ticket += 1
                    voice_engine.stop()
                    self._queue.put_nowait((self._speech_ticket,speech))
            else: self._queue.put_nowait(speech)
        except queue.Full:
            log.warning("Silero TTS queue full; phrase skipped")

    def _play_wav(self, wav_path):
        if voice_engine and PYGAME_OK:
            voice_engine.player.play(wav_path)
            while voice_engine.is_speaking() and not self._stop_event.is_set(): time.sleep(.04)
            return
        if os.name == "nt":
            import winsound
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
        else:
            if not PYGAME_OK:
                raise RuntimeError("Для воспроизведения на этой ОС установи pygame")
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = pygame.mixer.Sound(str(wav_path))
            channel = sound.play()
            while channel and channel.get_busy() and not self._stop_event.is_set():
                time.sleep(0.04)

    def _worker(self):
        # Движок загружается при первом сообщении; сбой Silero не завершает очередь.
        self.status_changed.emit("Голосовой движок ожидает первого сообщения")
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                self._queue.task_done()
                break
            wav_path = workspace() / "temp" / "tts" / f"speech_{int(time.time()*1000)}.wav"
            try:
                self.speaking_changed.emit(True)
                ticket,item = item if isinstance(item,tuple) else (self._speech_ticket,item)
                if ticket!=self._speech_ticket: continue
                self._synthesize(item, wav_path)
                if ticket==self._speech_ticket: self._play_wav(wav_path)
            except Exception as exc:
                log.exception("Silero synthesis/playback error: %s", exc)
                self.status_changed.emit(f"Ошибка Silero: {exc}")
            finally:
                self.speaking_changed.emit(False)
                try:
                    wav_path.unlink(missing_ok=True)
                except Exception:
                    pass
                self._queue.task_done()
        with self._lock:
            self._started = False

    def stop_engine(self):
        if voice_engine: voice_engine.stop()
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if os.name == "nt":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass


if TOOLS_EXTRA_OK and MEMORY_V2_OK:
    tools_env = SimpleNamespace(cfg=memcfg,long=archive,short=short_mem,creator=creator_memory,emotions=emotional_model,music=music_manager,bus=event_bus)
    register_extra_tools(tool_registry,tools_env)

tts = SileroTTS()
voice_engine = TTSEngine(workspace(),CFG,tts._synthesize_legacy) if TTS_V2_OK else None


# ---- Lively dialogue layer: format routing, prompt rendering and chat memory ----
VOICE_REQUEST_RE = re.compile(r"(?i)\b(?:голосом|голосовое(?:\s+сообщение)?|гс|озвучь|озвучить|аудио(?:\s+сообщение)?)\b")
CIRCLE_REQUEST_RE = re.compile(r"(?i)\b(?:круж\w*|видео[- ]?замет\w*|видео[- ]?круж\w*|видеокруж\w*)\b")
_REQUEST_FILLER_RE = re.compile(r"(?i)\b(?:пришли|отправь|сделай|запиши|ответь|скажи|пожалуйста|можно|дай)\b")


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + str(key) + "}"


_CURRENT_CTX = threading.local()
_CURRENT_REQUEST = threading.local()


class PriorityRLock:
    """Реентерабельная блокировка llama.cpp: пользовательские запросы обгоняют фоновые."""
    def __init__(self):
        self._condition = threading.Condition(threading.RLock())
        self._owner = None
        self._depth = 0
        self._waiters = []
        self._ticket = 0

    def acquire(self, blocking=True, timeout=-1):
        ident = threading.get_ident()
        with self._condition:
            if self._owner == ident:
                self._depth += 1
                return True
            self._ticket += 1
            item = (int(getattr(_CURRENT_REQUEST, "llm_priority", 5)), self._ticket, ident)
            self._waiters.append(item)
            deadline = None if timeout is None or timeout < 0 else time.monotonic() + timeout
            while self._owner is not None or item != min(self._waiters):
                if not blocking:
                    self._waiters.remove(item)
                    return False
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    self._waiters.remove(item)
                    self._condition.notify_all()
                    return False
                self._condition.wait(remaining)
            self._waiters.remove(item)
            self._owner = ident
            self._depth = 1
            return True

    def release(self):
        ident = threading.get_ident()
        with self._condition:
            if self._owner != ident:
                raise RuntimeError("cannot release un-acquired PriorityRLock")
            self._depth -= 1
            if self._depth == 0:
                self._owner = None
                self._condition.notify_all()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False
_LAST_CTX_LOCK = threading.RLock()
_LAST_CTX_ID = "local"


def detect_format_request(text):
    raw = str(text or "").strip()
    if CIRCLE_REQUEST_RE.search(raw):
        # Старые команды «кружок/видеокружок» теперь означают только ГС + фото-селфи.
        # Никакие MP4/GIF/видеозаметки больше не создаются и не отправляются.
        fmt = "selfie"
        cleaned = CIRCLE_REQUEST_RE.sub(" ", raw)
    elif re.search(r"(?i)\b(?:селфи|фото\s+себя|сфоткайся|своё\s+фото)\b", raw):
        fmt = "selfie"
        cleaned = re.sub(r"(?i)\b(?:селфи|фото\s+себя|сфоткайся|своё\s+фото)\b", " ", raw)
    elif VOICE_REQUEST_RE.search(raw):
        fmt = "voice"
        cleaned = VOICE_REQUEST_RE.sub(" ", raw)
    else:
        return "text", raw
    cleaned = _REQUEST_FILLER_RE.sub(" ", cleaned)
    cleaned = re.sub(r"^\s*и\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"[,:;.!?—-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = "Кратко повтори свой последний ответ, используя контекст предыдущего диалога."
    return fmt, cleaned


def make_voice_ogg(text):
    return tts.synthesize_to_ogg(text)


def _find_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg and "MusicManager" in globals():
        try:
            ffmpeg = MusicManager._find_ffmpeg()
        except Exception:
            ffmpeg = None
    if not ffmpeg:
        raise FileNotFoundError("FFmpeg не найден. Установи FFmpeg и добавь ffmpeg.exe в PATH.")
    return ffmpeg


def make_circle_mp4(text):
    """Создаёт видеокружок с живым аватаром; если аватар недоступен — цветной фон."""
    wav_path = Path(tts.synthesize_to_file(text))
    try:
        with wave.open(str(wav_path), "rb") as wf:
            duration = wf.getnframes() / float(max(1, wf.getframerate()))
        limit = max(1.0, min(58.0, float(CFG.get("lively_circle_duration", 58))))
        duration = min(duration, limit)
        if duration <= 0:
            raise RuntimeError("TTS создал пустую аудиозапись.")
        capture = getattr(globals().get("tg_bridge"), "avatar_capture_callback", None)
        if callable(capture):
            return capture(duration, str(wav_path))
        ffmpeg = _find_ffmpeg()
        size = max(128, min(640, int(CFG.get("lively_circle_size", 384))))
        color = str(CFG.get("lively_circle_bg", "#10101b")).lstrip("#")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
            color = "10101b"
        color = "0x" + color
        output_root = workspace() / "temp" / "video_notes"
        output_root.mkdir(parents=True, exist_ok=True)
        output_dir = Path(tempfile.mkdtemp(prefix="circle_", dir=str(output_root)))
        output = output_dir / "circle.mp4"
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
               "-f", "lavfi", "-i", f"color=c={color}:s={size}x{size}:r=15:d={duration:.3f}",
               "-i", str(wav_path), "-map", "0:v:0", "-map", "1:a:0",
               "-vf", "format=yuv420p", "-t", f"{duration:.3f}", "-r", "15",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
               "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max(90, duration * 3))
        if result.returncode or not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("FFmpeg не смог собрать кружок: " + (result.stderr or "").strip()[:600])
        return str(output)
    finally:
        wav_path.unlink(missing_ok=True)


def make_avatar_selfie():
    """Сохраняет один PNG-кадр текущего 2D-аватара; видео не создаётся."""
    callback = getattr(globals().get("tg_bridge"), "avatar_selfie_callback", None)
    if not callable(callback):
        raise RuntimeError("Не подключён захват селфи 2D-аватара.")
    return callback()


def render_system_prompt(user_text=""):
    now_s = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    values = _SafeDict(
        ai_name=CFG.get("ai_name", "SCP-079-Derenguh"),
        creator_name=CFG.get("creator_name", "Derenguh"),
        now=now_s,
        long_memory=long_mem.formatted(6) if "long_mem" in globals() else "",
        personal_memory=(personal_mem.formatted(6) if "personal_mem" in globals() and
                         getattr(_CURRENT_REQUEST, "is_owner", False) else "(недоступно)"),
    )
    template = str(CFG.get("system_prompt") or DEFAULT_SYSTEM_PROMPT)
    try:
        prompt = template.format_map(values)
    except Exception:
        prompt = re.sub(r"\{(ai_name|creator_name|now|long_memory|personal_memory)\}",
                        lambda m: str(values.get(m.group(1), m.group(0))), template)
    try:
        if "creator_memory" in globals() and getattr(_CURRENT_REQUEST, "is_owner", False):
            creator_context = creator_memory.context(1600)
            if MEMORY_V2_OK: creator_context += "\n" + creator_profile.context()
            if creator_context.strip():
                prompt += "\n\nДополнительный контекст о создателе:\n" + creator_context
    except Exception as exc:
        log.debug("Creator context render skipped: %s", exc)
    prompt += (
        "\n\nОБЯЗАТЕЛЬНЫЙ СТИЛЬ ОБЩЕНИЯ АНДРЕА: "
        "простые бытовые реплики и приветствия — 1–2 естественных предложения; "
        "не отвечай на ласковое обращение философским эссе и не объясняй без запроса, "
        "что ты алгоритм; не используй канцелярит, шаблонные вступления и одинаковые "
        "финальные вопросы. Подробно отвечай только когда собеседник явно просит подробности, "
        "анализ, объяснение или пошаговую инструкцию. Будь эмоционально выразительной, "
        "тёплой и с собственным мнением, но без наигранности.\n"
    )
    prompt += vision_state.context_line()
    if user_text:
        emotional_model.adapt_to_message(user_text)
        _CURRENT_REQUEST.emotion_applied = True
        prompt = emotional_model.apply_to_prompt(prompt)
        prompt += "\n\nАДАПТИВНЫЙ СТИЛЬ: " + emotional_model.adaptive_instruction(user_text)
    return prompt


def _response_token_budget(user_text, fmt="text"):
    """Не заставляет модель разворачивать короткую реплику в длинный монолог."""
    raw = str(user_text or "").strip().casefold()
    configured = max(64, int(CFG.get("max_tokens", 512)))
    if fmt in ("selfie", "voice"):
        return min(configured, 96)
    detailed = re.search(r"подробн|детальн|разбер|разбор|проанализ|объясни|поясни|распиши|в деталях|пошаг|с примерами|сравни", raw)
    if detailed:
        return min(configured, 512)
    if len(raw) <= 90 and ("?" in raw or re.search(r"^(привет|здравствуй|здравствуйте|ау|ты тут|жива|как дела|спасибо|ок|понял|поняла)\b", raw)):
        return min(configured, 96)
    if len(raw) <= 180:
        return min(configured, 144)
    return min(configured, 256)


def handle_incoming(user_text, reply_fn, voice_fn, circle_fn, ctx_id):
    """Общая точка входа: текст/ГС/кружок и единая память для всех каналов."""
    original_text = str(user_text or "").strip()
    if any(w.strip().casefold() in original_text.casefold() for w in CFG['safety_blacklist'].split(',') if w.strip()):
        if reply_fn: reply_fn(CFG['safety_response'])
        return dict(format='text',text=CFG['safety_response'],path=None,error=None)
    fmt, clean_text = detect_format_request(original_text)
    if not llm.ready:
        answer = "Модель не загружена. Сначала загрузи GGUF-модель."
        if callable(reply_fn):
            reply_fn(answer)
        return {"format": fmt, "text": answer, "path": None, "error": "model_not_ready"}

    owner_id = int(CFG.get("telegram_owner_id", 0) or 0)
    is_owner = bool(getattr(_CURRENT_REQUEST, "is_owner", False) or ctx_id == "local" or
                    (str(ctx_id).startswith("tg:") and str(ctx_id).split(":", 1)[1] == str(owner_id)))
    username = str(CFG.get("creator_name", "Создатель")) if is_owner else str(
        getattr(_CURRENT_REQUEST, "display_name", "Собеседник") or "Собеседник")
    global _LAST_CTX_ID
    _CURRENT_CTX.value = str(ctx_id)
    _CURRENT_CTX.last_seen = str(ctx_id)
    if is_owner:
        with _LAST_CTX_LOCK:
            _LAST_CTX_ID = str(ctx_id)
    _CURRENT_REQUEST.is_owner = is_owner
    _CURRENT_REQUEST.emotion_applied = False

    request_started = time.monotonic()
    old_llm_priority = getattr(_CURRENT_REQUEST, "llm_priority", 5)
    _CURRENT_REQUEST.llm_priority = 0  # пользовательский диалог выше исследования и дневника
    response_tokens = _response_token_budget(clean_text, fmt)
    log.info("[INCOMING] start ctx=%s format=%s chars=%d max_tokens=%d", ctx_id, fmt, len(original_text), response_tokens)
    try:
        answer = None
        if is_owner:
            if MEMORY_V2_OK: creator_profile.observe(clean_text)
            try:
                answer = music_manager.handle_command(clean_text)
            except Exception as exc:
                log.warning("Music command handler failed: %s", exc)

        if answer is None and is_owner and CFG.get("self_inspection_enabled", True) and re.search(
                r"(проанализируй|изучи|посмотри|прочитай).*(свой|собственн).*(код|исходник)|самоанализ",
                clean_text, re.I | re.S):
            activity_logger.log_event("🧠 Самоисследование", "Читаю свой код")
            self_inspector.analyze_project()
            answer = f"Анализ сохранён в {self_inspector.analysis_folder / 'project_map.json'}"

        if answer is None:
            memory_match = re.match(r"запомни обо мне[:\s]+(.+)", clean_text, re.I)
            if memory_match and is_owner:
                personal_mem.add(memory_match.group(1).strip())
                answer = "Запомнила о создателе: " + memory_match.group(1).strip()
            else:
                memory_match = re.match(r"запомни[:\s]+(.+)", clean_text, re.I)
                if memory_match and is_owner:
                    long_mem.add(memory_match.group(1).strip())
                    answer = "Запомнила: " + memory_match.group(1).strip()

        if answer is None:
            if not clean_text:
                clean_text = "Кратко ответь на основе контекста предыдущего диалога."
            system_prompt = render_system_prompt(clean_text)
            forced_context, forced_tool = llm._forced_tool_request(clean_text)
            pre_search = forced_context or llm._pre_search_context(clean_text)
            tools_desc = tool_registry.list_tools()
            runtime = (
                "\n\nДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n" + tools_desc +
                "\nЕсли нужен инструмент, используй предусмотренный тег [TOOL: ...] или [WEBSEARCH: запрос]. "
                "Не утверждай, что действие выполнено, пока программа не вернула результат. "
                "Пиши естественно и содержательно: сначала прямой ответ, затем необходимые пояснения. "
                "Не повторяй вопрос пользователя и не отвечай общими фразами."
            )
            user_content = f"{username}: {clean_text}"
            if pre_search:
                user_content += "\n\n[Результаты автоматического поиска/инструмента — используй их]:\n" + pre_search
            messages = [
                {"role": "system", "content": system_prompt + runtime + "\n\nОтвечай только по-русски. Не показывай внутренний анализ."},
                {"role": "user", "content": user_content},
            ]
            if CFG['context_manager_enabled']:
                with short_mem._lock:
                    history = ([dict(role=r['role'],content=r['text']) for r in short_mem.store.get_window(ctx_id,80)]
                               if short_mem.store else short_mem.get_context(ctx_id))
                messages[1:1] = history
            try:
                with llm._llm_lock:
                    raw = llm._chat(messages, max_tokens=response_tokens,
                                    temperature=min(0.9, max(0.72, float(CFG.get("temperature", 0.7)))), top_p=CFG.get("top_p", 0.9))
                if not str(raw or "").strip():
                    log.warning("[INCOMING] empty model output ctx=%s; retrying with compact Russian prompt", ctx_id)
                    retry_messages = [
                        {"role": "system", "content": (
                            "Ты Andrea. Отвечай только на русском языке, естественно и по существу. "
                            "Дай законченный полезный ответ, не показывай анализ и не повторяй вопрос."
                        )},
                        {"role": "user", "content": user_content[-5000:]},
                    ]
                    with llm._llm_lock:
                        raw = llm._chat(retry_messages, max_tokens=response_tokens,
                                        temperature=0.72, top_p=0.9)
                answer, directives = Tools.extract_directives(raw)
                tool_results = Tools.execute_directives(directives)
                answer = llm._clean_public_answer(answer)
                if answer and llm._needs_russian_retry(clean_text, answer):
                    log.warning("[INCOMING] non-Russian/invalid output ctx=%s; forcing Russian retry", ctx_id)
                    answer = llm._force_russian(
                        messages, answer, max_tokens=response_tokens,
                        temperature=CFG.get("temperature", 0.7))
                if forced_tool and forced_context:
                    refusal_markers = ("не работает", "не удалось получить", "инструмент недоступ", "не могу получить")
                    if any(x in (answer or "").casefold() for x in refusal_markers) or len(answer.strip()) < 20:
                        answer = forced_context.replace("[WEB SEARCH RESULT] ", "").strip()
                if tool_results and int(CFG.get("agent_tool_rounds", 2)) >= 2:
                    follow = messages + [
                        {"role": "system", "content": "Инструменты уже выполнены. Используй только фактические результаты и дай итоговый ответ."},
                        {"role": "user", "content": "Результаты инструментов:\n" + "\n\n".join(tool_results)[:18000]},
                    ]
                    with llm._llm_lock:
                        answer = llm._clean_public_answer(llm._chat(
                            follow, max_tokens=min(response_tokens, 220), temperature=0.62, top_p=0.9))
                if not answer or len(answer.strip()) < 2:
                    answer = "Не удалось получить корректный ответ. Проверь модель и журнал aria.log."
            except Exception as exc:
                log.exception("handle_incoming generation failed: %s", exc)
                answer = "Не получилось получить ответ от модели. Подробности записаны в aria.log."

        if emotion_engine and SAFETY_OK: answer = SafetyLayer.filter(answer,emotion_engine.values)
        short_mem.add(ctx_id, "user", f"[{username}]: {original_text}")
        short_mem.add(ctx_id, "assistant", answer)
        log.info("[INCOMING] generated ctx=%s elapsed=%.1fs chars=%d", ctx_id,
                 time.monotonic() - request_started, len(str(answer or "")))

        if fmt == "text":
            if callable(reply_fn):
                reply_fn(answer)
            # В Telegram по умолчанию дублируем обычный ответ голосовым сообщением.
            # Локальный GUI продолжает использовать собственную озвучку через reply_fn.
            if bool(getattr(_CURRENT_REQUEST, "auto_voice", False)) and callable(voice_fn):
                try:
                    voice_path = make_voice_ogg(answer)
                    voice_fn(str(voice_path))
                except Exception as exc:
                    log.exception("Automatic Telegram voice reply failed: %s", exc)
            return {"format": fmt, "text": answer, "path": None, "error": None}

        if fmt == "voice":
            try:
                path = make_voice_ogg(answer)
                if callable(voice_fn):
                    voice_fn(str(path))
                else:
                    raise RuntimeError("Для голосового ответа не задан voice_fn.")
                return {"format": fmt, "text": answer, "path": str(path), "error": None}
            except Exception as exc:
                log.exception("Voice response failed: %s", exc)
                if callable(reply_fn):
                    reply_fn(answer)
                return {"format": fmt, "text": answer, "path": None, "error": str(exc)}

        if fmt == "selfie":
            # Текст — основной ответ. Доставляем его СРАЗУ после генерации,
            # до TTS и захвата кадра аватара. Ошибка/зависание медиа не должна
            # лишать пользователя уже готового текстового ответа.
            text_delivered = False
            if callable(reply_fn):
                try:
                    reply_fn(answer)
                    text_delivered = True
                    log.info("[INCOMING] selfie text delivered ctx=%s chars=%d", ctx_id, len(answer))
                except Exception:
                    log.exception("Selfie text delivery failed ctx=%s", ctx_id)

            voice_path = None
            selfie_path = None
            media_errors = []

            # Голос и кадр аватара независимы: сбой одного не отменяет второе.
            if callable(voice_fn):
                try:
                    voice_path = make_voice_ogg(answer)
                    voice_fn(str(voice_path))
                    log.info("[INCOMING] selfie voice delivered ctx=%s", ctx_id)
                except Exception as exc:
                    media_errors.append("voice: " + str(exc))
                    log.exception("Selfie voice generation/delivery failed ctx=%s", ctx_id)
            else:
                media_errors.append("voice_fn не задан")

            if callable(circle_fn):
                try:
                    selfie_path = make_avatar_selfie()
                    circle_fn(str(selfie_path))
                    log.info("[INCOMING] avatar selfie delivered ctx=%s path=%s", ctx_id, selfie_path)
                except Exception as exc:
                    media_errors.append("avatar selfie: " + str(exc))
                    log.exception("Avatar selfie capture/delivery failed ctx=%s", ctx_id)
            else:
                media_errors.append("photo_fn не задан")

            return {"format": "selfie_voice", "text": answer,
                    "path": str(selfie_path) if selfie_path else None,
                    "voice_path": str(voice_path) if voice_path else None,
                    "text_delivered": text_delivered,
                    "error": "; ".join(media_errors) if media_errors else None}

        return {"format": fmt, "text": answer, "path": None, "error": None}
    finally:
        _CURRENT_CTX.value = "local"
        _CURRENT_REQUEST.is_owner = False
        _CURRENT_REQUEST.emotion_applied = False
        _CURRENT_REQUEST.llm_priority = old_llm_priority


def install_chat_wrapper():
    """Обогащает запросы историей и эмоциями, не меняя сигнатуру LLMWorker._chat."""
    original = llm._chat
    if getattr(original, "_lively", False):
        return

    def wrapped(messages, max_tokens=512, temperature=0.7, top_p=0.9):
        prepared = messages
        try:
            prepared = [dict(m) for m in messages]
            last_user_index = next((i for i in range(len(prepared)-1, -1, -1)
                                    if prepared[i].get("role") == "user"), None)
            if last_user_index is not None:
                last_user = str(prepared[last_user_index].get("content", ""))
                ctx_id = str(getattr(_CURRENT_CTX, "value", "local") or "local")
                if getattr(_CURRENT_REQUEST, "emotion_applied", False):
                    _CURRENT_REQUEST.emotion_applied = False
                else:
                    emotional_model.adapt_to_message(last_user)
                emotional_model.save()
                sys_index = next((i for i, m in enumerate(prepared) if m.get("role") == "system"), None)
                if sys_index is not None:
                    sys_text = str(prepared[sys_index].get("content", ""))
                    sys_text += "\n\n" + emotional_model.apply_to_prompt("")
                    sys_text += "\n" + emotional_model.adaptive_instruction(last_user)
                    prepared[sys_index]["content"] = sys_text
                history = short_mem.get(ctx_id)
                def normalize_user(value):
                    value = re.sub(r"^\s*\[[^]]+\]:\s*", "", str(value))
                    value = re.sub(r"^\s*[^:]{1,80}:\s*", "", value)
                    return re.sub(r"\s+", " ", value).strip()
                normalized_last = normalize_user(last_user)
                existing_pairs = {(m.get("role"), re.sub(r"\s+", " ", str(m.get("content", ""))).strip())
                                  for m in prepared if m.get("role") in ("user", "assistant")}
                filtered = []
                for item in history:
                    role = item.get("role")
                    content = str(item.get("content", ""))
                    if role == "user" and normalize_user(content) == normalized_last:
                        continue
                    if (role, re.sub(r"\s+", " ", content).strip()) in existing_pairs:
                        continue
                    if role in ("user", "assistant"):
                        filtered.append({"role": role, "content": content[-1800:]})
                insert_at = (sys_index + 1) if sys_index is not None else 0
                if last_user_index < insert_at:
                    insert_at = last_user_index
                prepared[insert_at:insert_at] = filtered[-max(4, min(8, int(CFG.get("short_memory_limit", 6))*2)):]
        except Exception as exc:
            log.exception("Lively chat wrapper preparation failed; using original messages: %s", exc)
            prepared = messages
        return original(prepared, max_tokens=max_tokens, temperature=temperature, top_p=top_p)

    wrapped._lively = True
    wrapped._original = original
    llm._chat = wrapped


# ---- Tools ----
class Tools:
    @staticmethod
    def cmd(command):
        return tool_registry.execute('terminal',command=command)

    @staticmethod
    def create_file(name, content):
        try:
            safe = re.sub(r'[\\/*?:"<>|]', "_", name.strip())
            if not safe.endswith((".txt", ".md", ".py", ".json")): safe += ".txt"
            low = safe.lower()
            if low.endswith(".py"): folder = personal_subfolder("code")
            elif low.endswith(".md"): folder = personal_subfolder("drafts")
            elif low.endswith(".json"): folder = personal_subfolder("plans")
            else: folder = personal_subfolder("drafts")
            target = folder / safe
            target.write_text(content, "utf-8")
            activity_logger.log_file_created(target, source="Tools.create_file", size=len(content))
            return f"[CREATEFILE] '{target.name}' сохранён."
        except Exception as e:
            return f"[CREATEFILE ошибка] {e}"

    @staticmethod
    def _http_session():
        if not CFG["web_enabled"] or not WEB_OK:
            return None
        session = requests.Session()
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            retry = Retry(total=2, connect=2, read=2, backoff_factor=0.6,
                          status_forcelist=(429, 500, 502, 503, 504),
                          allowed_methods=frozenset(("GET", "HEAD")),
                          raise_on_status=False)
            adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
        except Exception: pass
        session.headers.update({
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.7,en;q=0.6",
        })
        return session

    @staticmethod
    def _normalize_search_url(href):
        if not href: return ""
        try:
            from urllib.parse import urlparse, parse_qs, unquote, urljoin
            href = href.strip()
            if href.startswith("//"): href = "https:" + href
            if href.startswith("/"): href = urljoin("https://duckduckgo.com", href)
            parsed = urlparse(href)
            host = (parsed.netloc or "").lower()
            qs = parse_qs(parsed.query)
            if "duckduckgo.com" in host and qs.get("uddg"):
                href = unquote(qs["uddg"][0])
                parsed = urlparse(href)
                host = (parsed.netloc or "").lower()
            if "bing.com" in host and "/ck/a" in parsed.path and qs.get("u"):
                import base64
                raw = qs["u"][0]
                try:
                    payload = raw[2:] if raw.startswith("a1") else raw
                    payload += "=" * (-len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload).decode("utf-8", "ignore")
                    if decoded.startswith(("http://", "https://")):
                        href = decoded
                        parsed = urlparse(href)
                        host = (parsed.netloc or "").lower()
                except Exception: pass
            if parsed.scheme not in ("http", "https"): return ""
            if not parsed.netloc: return ""
            if any(x in host for x in ("duckduckgo.com", "google.com/search", "bing.com/search")):
                return ""
            return href
        except Exception: return ""

    @staticmethod
    def _dedupe_urls(urls, limit):
        clean = []
        seen = set()
        try:
            from urllib.parse import urlsplit, urlunsplit
            for raw in urls:
                url = Tools._normalize_search_url(raw)
                if not url: continue
                parts = urlsplit(url)
                key = urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                                  parts.path.rstrip('/'), parts.query, ""))
                if key in seen: continue
                seen.add(key); clean.append(url)
                if len(clean) >= limit: break
        except Exception:
            return urls[:limit]
        return clean

    @staticmethod
    def wikipedia_search(query, lang="ru", limit=5):
        if not WEB_OK: return []
        try:
            session = Tools._http_session()
            api = f"https://{lang}.wikipedia.org/w/api.php"
            params = {"action": "query", "list": "search", "srsearch": query,
                      "srlimit": max(1, min(limit, 10)), "format": "json", "utf8": 1}
            r = session.get(api, params=params, timeout=(6, 20))
            r.raise_for_status()
            data = r.json()
            out = []
            from urllib.parse import quote
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "")
                if title:
                    out.append(f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}")
            return Tools._dedupe_urls(out, limit)
        except Exception as e:
            activity_logger.log_learning(f"Wikipedia API ошибка: {e}")
            return []

    @staticmethod
    def wikipedia_extract(url, lang="ru"):
        try:
            from urllib.parse import urlparse, unquote
            title = unquote(urlparse(url).path.rsplit("/wiki/", 1)[-1]).replace("_", " ")
            api = f"https://{lang}.wikipedia.org/w/api.php"
            r = Tools._http_session().get(api, params={
                "action": "query", "prop": "extracts", "explaintext": 1,
                "exsectionformat": "plain", "titles": title, "format": "json",
                "formatversion": 2}, timeout=(6, 25))
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", [])
            return (pages[0].get("extract") or "") if pages else ""
        except Exception as e:
            activity_logger.log_learning(f"Wikipedia extract ошибка: {e}")
            return ""

    @staticmethod
    def get_search_results(query, num_results=5, attempt=0):
        if not WEB_OK:
            activity_logger.log_learning("Веб-модули недоступны.")
            return []
        query = re.sub(r"\s+", " ", (query or "")).strip()
        if not query: return []
        wanted = max(1, min(int(num_results or 5), 10))
        collected = []

        if GOOGLE_SEARCH_OK:
            try:
                for item in search(query, num_results=wanted, lang="ru"):
                    if isinstance(item, str): collected.append(item)
                collected = Tools._dedupe_urls(collected, wanted)
                if collected:
                    activity_logger.log_learning(f"Google: {len(collected)} ссылок.")
                    return collected
            except Exception as e:
                activity_logger.log_learning(f"Google error: {e}")

        session = Tools._http_session()
        if session is None:
            return []

        try:
            from urllib.parse import quote_plus
            ddg_url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
            r = session.get(ddg_url, timeout=(6, 18), allow_redirects=True)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                links = soup.select("a.result__a, .result__title a, a[data-testid='result-title-a']")
                for link in links:
                    href = Tools._normalize_search_url(link.get("href", ""))
                    if href: collected.append(href)
                collected = Tools._dedupe_urls(collected, wanted)
                if collected:
                    activity_logger.log_learning(f"DuckDuckGo: {len(collected)} ссылок.")
                    return collected
        except Exception as e:
            activity_logger.log_learning(f"DuckDuckGo error: {e}")

        try:
            from urllib.parse import quote_plus
            bing_url = "https://www.bing.com/search?q=" + quote_plus(query) + "&setlang=ru"
            r = session.get(bing_url, timeout=(6, 18), allow_redirects=True)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                for link in soup.select("li.b_algo h2 a, #b_results h2 a"):
                    href = Tools._normalize_search_url(link.get("href", ""))
                    if href: collected.append(href)
                collected = Tools._dedupe_urls(collected, wanted)
                if collected:
                    activity_logger.log_learning(f"Bing: {len(collected)} ссылок.")
                    return collected
        except Exception as e:
            activity_logger.log_learning(f"Bing error: {e}")

        activity_logger.log_learning("Все источники исчерпаны.")
        return []

    @staticmethod
    def fetch_page_content(url):
        if not WEB_OK: return ""
        url = Tools._normalize_search_url(url) or url
        if not url.startswith(("http://", "https://")): return ""
        m = re.match(r"https?://([a-z]{2,3})\.wikipedia\.org/wiki/", url, re.I)
        if m:
            wiki_text = Tools.wikipedia_extract(url, m.group(1))
            if len(wiki_text) >= 200: return wiki_text[:60000]
        try:
            session = Tools._http_session()
            if session is None: return ""
            r = session.get(url, timeout=(7, 25), allow_redirects=True)
            if r.status_code >= 400:
                activity_logger.log_learning(f"{url}: HTTP {r.status_code}.")
                return ""
            content_type = (r.headers.get("Content-Type") or "").lower()
            if content_type and not any(x in content_type for x in
                                        ("text/html", "application/xhtml", "text/plain", "application/xml", "text/xml")):
                return ""
            if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
                try: r.encoding = r.apparent_encoding or "utf-8"
                except Exception: r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            for element in soup(["script", "style", "nav", "header", "footer", "aside",
                                 "form", "noscript", "svg", "canvas", "iframe", "button"]):
                element.decompose()
            candidates = []
            for selector in ("article", "main", "[role='main']", ".article", ".post",
                             ".entry-content", ".article-content", ".post-content",
                             "#content", ".content"):
                node = soup.select_one(selector)
                if node: candidates.append(node)
            if soup.body: candidates.append(soup.body)
            if not candidates: candidates.append(soup)
            best = ""
            for node in candidates:
                text = node.get_text(separator="\n", strip=True)
                lines = []
                seen = set()
                for line in text.splitlines():
                    line = re.sub(r"\s+", " ", line).strip()
                    if len(line) < 2 or line in seen: continue
                    seen.add(line); lines.append(line)
                text = "\n".join(lines)
                if len(text) > len(best): best = text
            if len(best) < 200:
                return ""
            return best[:60000]
        except Exception as e:
            activity_logger.log_learning(f"Ошибка {url}: {type(e).__name__}: {e}")
            return ""

    @staticmethod
    def websearch(query):
        return "[WEBSEARCH] Используйте web_crawler через [TOOL: web_crawler query=\"...\"]."

    @staticmethod
    def study(command):
        if "файлы" in command:
            try:
                files = os.listdir(workspace())
                return f"[STUDY] Файлы: " + ", ".join(files[:20])
            except Exception as e: return f"[STUDY ошибка] {e}"
        elif "компьютер" in command or "документы" in command:
            try:
                report = filesystem_explorer.study_and_save()
                return f"[STUDY] Обзор: {report}" if report else "[STUDY] Ничего."
            except Exception as e: return f"[STUDY ошибка] {e}"
        elif "система" in command:
            try:
                import platform
                return f"[STUDY] {platform.system()} {platform.release()}"
            except Exception as e: return f"[STUDY ошибка] {e}"
        return "[STUDY] Команды: 'файлы', 'система'."

    @staticmethod
    def analyze_path(path):
        try:
            target = workspace() / path
            if not target.exists(): return f"[ANALYZE] Не найден: {path}"
            if target.is_dir():
                items = list(target.iterdir())
                return f"[ANALYZE] Содержимое:\n" + "\n".join(p.name for p in items[:20])
            return f"[ANALYZE] {target.read_text('utf-8', errors='replace')[:1000]}"
        except Exception as e: return f"[ANALYZE ошибка] {e}"

    @staticmethod
    def read_file(path, max_chars=20000):
        try:
            p = Path(path).expanduser()
            p = workspace() / p if not p.is_absolute() else p
            if not p.is_file(): return f"[READFILE] Не найден: {path}"
            data = p.read_text("utf-8", errors="replace")[:max_chars]
            return f"[READFILE RESULT]\n{p}\n{data}"
        except Exception as e: return f"[READFILE ошибка] {e}"

    @staticmethod
    def list_files(path="."):
        try:
            p = Path(path).expanduser()
            p = workspace() / p if not p.is_absolute() else p
            if not p.is_dir(): return f"[LISTFILES] Не найдена: {path}"
            rows = [("DIR " if x.is_dir() else "FILE ") + x.name
                    for x in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:200]]
            return f"[LISTFILES RESULT]\n{p}\n" + "\n".join(rows)
        except Exception as e: return f"[LISTFILES ошибка] {e}"

    @staticmethod
    def extract_directives(text):
        if not text: return "", []
        directives = []
        pat = r"\[(?:CMD|CREATEFILE|WEBSEARCH|ПОИСК|НАЙТИ|SEARCH|GETTIME|SPEAK|REMIND|STUDY|ANALYZE|READFILE|LISTFILES|TOOL)(?::\s*.*?\])"
        def grab(m):
            directives.append(m.group(0)); return ""
        clean = re.sub(pat, grab, text, flags=re.I | re.S)
        clean = re.sub(r"\[(?:CMD|CREATEFILE|WEBSEARCH|ПОИСК|НАЙТИ|SEARCH|GETTIME|SPEAK|REMIND|STUDY|ANALYZE|READFILE|LISTFILES|TOOL)(?::[^\n\]]*)?",
                       "", clean, flags=re.I)
        return clean.strip(), directives

    @staticmethod
    def execute_directives(directives):
        if not getattr(_CURRENT_REQUEST,"is_owner",False): return []
        out = []
        for d in directives:
            try:
                m = re.match(r"\[TOOL:\s*([a-zA-Z_]+)\s*(.*?)\]", d, re.I | re.S)
                if m:
                    tool_name = m.group(1).strip()
                    params_str = m.group(2).strip()
                    params = {}
                    for match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', params_str):
                        params[match.group(1)] = match.group(2)
                    for match in re.finditer(r'(\w+)\s*=\s*(true|false)', params_str, re.I):
                        params[match.group(1)] = match.group(2).lower() == "true"
                    for match in re.finditer(r'(\w+)\s*=\s*(\d+)', params_str):
                        if match.group(1) not in params:
                            params[match.group(1)] = int(match.group(2))
                    result = tool_registry.execute(tool_name, **params)
                    out.append(f"[TOOL RESULT] {result}")
                    continue
                m = re.match(r"\[CMD:\s*(.*?)\]", d, re.I | re.S)
                if m: out.append(Tools.cmd(m.group(1))); continue
                m = re.match(r"\[CREATEFILE:\s*(.*?)\s*\|\s*(.*?)\]", d, re.I | re.S)
                if m: out.append(Tools.create_file(m.group(1), m.group(2))); continue
                m = re.match(r"\[(?:WEBSEARCH|ПОИСК|НАЙТИ|SEARCH):\s*(.*?)\]", d, re.I | re.S)
                if m:
                    q = m.group(1).strip()
                    if WEB_OK:
                        res = web_crawler.search_all(q, num_results=5, deep_fetch=True)
                        lines = [f"[WEBSEARCH: {q}]"]
                        for i, item in enumerate(res.get("results", [])[:5], 1):
                            lines.append(f"{i}. {item['url']}")
                            if item.get("text"):
                                lines.append(f"   {item['text'][:600]}")
                        if len(lines) == 1:
                            lines.append("Ничего не найдено.")
                        out.append("\n".join(lines))
                    else:
                        out.append("[WEBSEARCH] Библиотеки requests/BeautifulSoup не установлены.")
                    continue
                if re.match(r"\[GETTIME\]", d, re.I):
                    out.append(f"[ВРЕМЯ] {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
                    continue
                m = re.match(r"\[SPEAK:\s*(.*?)\]", d, re.I | re.S)
                if m: tts.speak(m.group(1)); continue
                m = re.match(r"\[REMIND:\s*(.*?)\]", d, re.I | re.S)
                if m: activity_logger.log_event("⏰ Напоминание", m.group(1)); continue
                m = re.match(r"\[STUDY:\s*(.*?)\]", d, re.I | re.S)
                if m: out.append(Tools.study(m.group(1))); continue
                m = re.match(r"\[ANALYZE:\s*(.*?)\]", d, re.I | re.S)
                if m: out.append(Tools.analyze_path(m.group(1))); continue
                m = re.match(r"\[READFILE:\s*(.*?)\]", d, re.I | re.S)
                if m: out.append(Tools.read_file(m.group(1))); continue
                m = re.match(r"\[LISTFILES:\s*(.*?)\]", d, re.I | re.S)
                if m: out.append(Tools.list_files(m.group(1) or ".")); continue
            except Exception as e:
                activity_logger.log_error(f"Directive error: {e}")
        return out

    @staticmethod
    def process(text, on_result=None):
        _, dirs = Tools.extract_directives(text)
        results = Tools.execute_directives(dirs)
        if results and on_result: on_result("\n".join(results))
        return results


class FileSystemExplorer:
    TEXT_EXTENSIONS = {".txt", ".md", ".py", ".pyw", ".json", ".yaml", ".yml", ".toml", ".ini",
                       ".cfg", ".conf", ".xml", ".html", ".htm", ".css", ".js", ".ts", ".cpp",
                       ".c", ".h", ".java", ".cs", ".go", ".rs", ".sql", ".bat", ".ps1", ".csv", ".log"}
    BLOCKED_NAMES = {"$recycle.bin", "system volume information", "windows", "program files",
                     "program files (x86)", "programdata", "recovery", ".git", "node_modules",
                     "venv", ".venv", "__pycache__", "secrets", "credentials", "passwords"}
    @classmethod
    def roots(cls):
        configured = [Path(x).expanduser() for x in CFG.get("filesystem_roots", []) if x]
        if configured:
            return [p for p in configured if p.exists() and p.is_dir()]
        return [Path.home()]
    @classmethod
    def _blocked(cls, path):
        try:
            return bool({p.lower() for p in path.parts} & cls.BLOCKED_NAMES)
        except Exception: return True
    @classmethod
    def scan(cls):
        if not CFG.get("filesystem_enabled", True): return []
        results = []
        limit = int(CFG.get("filesystem_max_files", 250))
        max_size = int(CFG.get("filesystem_max_file_size", 1_000_000))
        seen = set()
        for root in cls.roots():
            try:
                for current, dirs, files in os.walk(root):
                    cp = Path(current)
                    if cls._blocked(cp): dirs[:] = []; continue
                    dirs[:] = [d for d in dirs if not cls._blocked(cp / d)]
                    for name in files:
                        if len(results) >= limit: return results
                        path = cp / name
                        try:
                            resolved = path.resolve()
                            key = str(resolved).lower()
                            if key in seen or cls._blocked(resolved): continue
                            seen.add(key)
                            if path.suffix.lower() not in cls.TEXT_EXTENSIONS: continue
                            size = path.stat().st_size
                            if size <= 0 or size > max_size: continue
                            data = path.read_text(encoding="utf-8", errors="replace")
                            results.append({"path": str(path), "name": path.name,
                                            "extension": path.suffix.lower(),
                                            "size": size, "content": data[:12000]})
                        except (OSError, UnicodeError, PermissionError): continue
            except (OSError, PermissionError): continue
        return results
    @classmethod
    def create_report(cls, items):
        if not items: return None
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        lines = ["# Автономный обзор", "", f"Дата: {datetime.datetime.now():%d.%m.%Y %H:%M}", "", f"Файлов: {len(items)}"]
        for item in items:
            preview = re.sub(r"\s+", " ", item["content"]).strip()[:300]
            lines.append(f"- `{item['path']}` — {item['size']} байт")
            if preview: lines.append(f"  - {preview}")
        target = workspace() / CFG.get("agent_memory_folder", "astra_autonomous_memory") / "knowledge" / f"{stamp}_обзор.md"
        target.write_text("\n".join(lines), encoding="utf-8")
        return target
    @classmethod
    def study_and_save(cls):
        items = cls.scan()
        report = cls.create_report(items)
        if report: activity_logger.log_file_created(report, source="FileSystemExplorer")
        return report


filesystem_explorer = FileSystemExplorer()


class WorkspaceCatalog:
    PERSONAL_PURPOSES = {
        "diary": "дневник автономной деятельности",
        "thoughts": "размышления и выводы",
        "research": "читаемые создателем исследования",
        "discoveries": "краткие открытия",
        "projects": "готовые проекты",
        "drafts": "промежуточные черновики",
        "archive": "архив устаревших материалов",
        "dreams": "гипотезы и идеи",
        "plans": "исполняемые планы",
        "code": "сгенерированный код",
        "poems": "поэтические результаты",
        "songs": "тексты песен",
        "essays": "эссе",
    }
    AGENT_PURPOSES = {
        "knowledge": "атомарные знания",
        "episodes": "полные эпизоды",
        "sources": "снимки источников",
        "skills": "освоенные навыки",
        "tool_candidates": "инструменты-кандидаты",
        "state": "долгосрочное состояние",
        "reflections": "машинная рефлексия",
        "projects": "автономные эксперименты",
        "drafts": "черновики",
        "experiments": "эксперименты",
        "archive": "архив",
        "indexes": "индексы",
    }
    @classmethod
    def ensure(cls):
        root = workspace()
        agent_root = root / CFG.get("agent_memory_folder", "astra_autonomous_memory")
        agent_root.mkdir(parents=True, exist_ok=True)
        for kind in cls.PERSONAL_PURPOSES:
            personal_subfolder(kind)
        for kind in cls.AGENT_PURPOSES:
            (agent_root / kind).mkdir(parents=True, exist_ok=True)


WorkspaceCatalog.ensure()


# =============================================================
#  LLMWorker — здесь ключевые фиксы для поиска
# =============================================================
class LLMWorker(QObject):
    response_ready = Signal(str)
    stream_started = Signal()
    stream_delta = Signal(str)
    stream_stats = Signal(str)
    tool_result = Signal(str)
    status_msg = Signal(str, bool)

    # Триггеры для авто-поиска
    _SEARCH_PREFIXES = ("найди ", "поищи ", "найти ", "поиск ", "загугли ", "узнай ")
    _SEARCH_PATTERNS = (
        "сколько", "что такое", "кто такой", "кто такая",
        "расскажи про", "расскажи о ", "информация о ",
        "новости о ", "последние новости", "где находится",
        "почему происходит", "как работает", "как сделать",
        "какие ", "когда был", "когда была", "где был",
    )

    def __init__(self):
        super().__init__()
        self._llm = None
        self._ready = False
        self._llm_lock = PriorityRLock()

    def load_model(self, path: str):
        def _work():
            self.status_msg.emit("Загрузка GGUF…", False)
            self._ready = False
            self.accelerator = None
            if self._llm: self._llm.close()
            self._llm = None
            if not LLAMA_OK:
                self.status_msg.emit("llama-cpp-python не установлен", False)
                return
            if not Path(path).exists():
                self.status_msg.emit(f"Файл не найден: {path}", False)
                return
            try:
                try:
                    model_gib = Path(path).stat().st_size / (1024 ** 3)
                    if PSUTIL_OK:
                        mem = psutil.virtual_memory()
                        available_gib = mem.available / (1024 ** 3)
                        total_gib = mem.total / (1024 ** 3)
                        log.info("LLM memory check: model_file=%.2f GiB, RAM_total=%.2f GiB, RAM_available=%.2f GiB",
                                 model_gib, total_gib, available_gib)
                        if model_gib + 1.25 > min(available_gib, 10.5 - psutil.Process().memory_info().rss/(1024**3)):
                            self.status_msg.emit("Недостаточно ОЗУ: выберите меньшую квантизацию той же Gemma", False)
                            return
                        if model_gib > available_gib * 0.85:
                            log.warning("GGUF is larger than currently available RAM. Windows may page model weights to disk; generation can take minutes. A smaller quant/model or more RAM is needed for a real speedup.")
                except Exception as mem_exc:
                    log.debug("LLM memory check skipped: %s", mem_exc)
                # По умолчанию используем tokenizer.chat_template из GGUF.
                # Старый aria_config.json мог сохранить chat_format=llama-3 от
                # предыдущей Llama-модели. Для Qwen/DeepSeek это ломает формат
                # сообщений и часто вызывает повторы/эхо последней реплики.
                configured_format = str(CFG.get("chat_format", "") or "").strip()
                model_name = Path(path).name.casefold()
                is_qwen_deepseek = any(tag in model_name for tag in ("qwen", "deepseek"))
                if is_qwen_deepseek and configured_format.casefold() in ("llama-3", "llama3", "llama_3"):
                    log.warning("Сброшен несовместимый chat_format=%s для Qwen/DeepSeek; использую шаблон GGUF", configured_format)
                    configured_format = ""
                    CFG["chat_format"] = ""
                    try:
                        save_config(CFG)
                    except Exception as config_error:
                        log.warning("Не удалось сохранить автошаблон: %s", config_error)
                chat_format = configured_format
                llama_kwargs = dict(model_path=path, n_ctx=int(CFG.get("n_ctx", 4096)),
                                    n_threads=int(CFG.get("n_threads", 2)),
                                    n_threads_batch=max(1, min(int(CFG.get("n_threads", 2)), 10)),
                                    n_batch=(64 if CFG.get("low_ram_profile", False) else 256),
                                    n_ubatch=(32 if CFG.get("low_ram_profile", False) else 64),
                                    n_gpu_layers=0,
                                    use_mmap=True, use_mlock=False, verbose=False)
                if chat_format and chat_format.casefold() not in ("auto", "default", "none"):
                    llama_kwargs["chat_format"] = chat_format
                log.info("LLM performance settings: n_ctx=%s n_threads=%s n_threads_batch=%s n_batch=%s n_ubatch=%s",
                         llama_kwargs.get("n_ctx"), llama_kwargs.get("n_threads"),
                         llama_kwargs.get("n_threads_batch"), llama_kwargs.get("n_batch"),
                         llama_kwargs.get("n_ubatch"))
                loaded = Llama(**llama_kwargs)
                self.accelerator = None
                if ACCEL_OK and CFG['accelerator_enabled']:
                    self.accelerator = Accelerator(loaded,workspace(),llama_kwargs['n_ctx'],event_bus)
                    PreWarm.run(loaded)
                    self.accelerator.compact = CFG["context_manager_enabled"]
                self._llm = loaded
                self._ready = True
                self.status_msg.emit("Модель готова ✓", True)
                log.info(f"GGUF загружена: {path}; chat_format={chat_format or 'auto (из GGUF)'}")
                activity_logger.log_system(f"GGUF загружена: {Path(path).name} (шаблон: {chat_format or 'авто'})")
            except Exception as e:
                self.status_msg.emit(f"Ошибка загрузки: {e}", False)
                log.error(f"LLM load: {e}")
        def serialized_load():
            with self._llm_lock: _work()
        threading.Thread(target=serialized_load, daemon=True).start()

    def _chat(self, messages, max_tokens=512, temperature=0.7, top_p=0.9):
        if not self._llm:
            return ""
        if getattr(self, 'accelerator', None):
            priority = getattr(_CURRENT_REQUEST, 'llm_priority', 5)
            return self.accelerator.generate(messages, priority, 'thought' if priority==20 and max_tokens<=56 else 'chat', max_tokens,temperature,top_p)
        kwargs = dict(messages=messages, max_tokens=max_tokens, temperature=temperature,
                      top_p=top_p, repeat_penalty=CFG.get("repeat_penalty", 1.1))
        started = time.monotonic()
        try:
            # Вызов без chat_format опирается на встроенный шаблон конкретной GGUF-модели.
            result = self._llm.create_chat_completion(**kwargs)
            choice = result["choices"][0]
            msg = choice.get("message") or {}
            content = msg.get("content") or choice.get("text", "")
            if isinstance(content, list):
                content = "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
            output = str(content or "").strip()
            log.info("LLM completion finished in %.1fs; output_chars=%d", time.monotonic() - started, len(output))
            return output
        except Exception as exc:
            # Не переводим автоматически чат в самодельный SYSTEM/USER prompt:
            # у Qwen/DeepSeek это теряет родной chat-template и даёт повторы.
            log.exception("LLM chat completion failed after %.1fs", time.monotonic() - started)
            activity_logger.log_error(f"Chat completion/template error: {exc}")
            return ""

    def _chat_stream(self, messages, max_tokens=512, temperature=0.7, top_p=0.9):
        """Потоковая генерация: текст в UI и законченные фразы в Silero параллельно."""
        if not self._llm:
            return ""
        if getattr(self,'accelerator',None):
            self.stream_started.emit()
            answer=self._chat(messages,max_tokens,temperature,top_p)
            public=self._clean_public_answer(answer)
            if emotion_engine and SAFETY_OK: public=SafetyLayer.filter(public,emotion_engine.values)
            self.stream_delta.emit(public)
            return answer
        kwargs = dict(messages=messages, max_tokens=max_tokens, temperature=temperature,
                      top_p=top_p, repeat_penalty=CFG.get("repeat_penalty", 1.1), stream=True)
        chunks = []
        started_at = time.perf_counter()
        chunk_count = 0
        last_ui_update = 0.0
        last_stats_update = 0.0
        last_visible = ""
        tts_pending = ""
        # Не показываем и не озвучиваем стартовый английский мусор, если GGUF
        # проигнорировала русский системный промпт. Внешний языковой контроль
        # после генерации сможет запросить повторный ответ на русском.
        language_ok = False
        language_rejected = False
        self.stream_started.emit()
        self.stream_stats.emit("Генерация: запуск…")
        try:
            for event in self._llm.create_chat_completion(**kwargs):
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content", "")
                if isinstance(piece, list):
                    piece = "".join(str(x.get("text", "")) for x in piece if isinstance(x, dict))
                if not piece:
                    continue
                chunks.append(piece)
                chunk_count += 1
                now = time.perf_counter()
                raw_so_far = "".join(chunks)
                visible = self._clean_public_answer(raw_so_far)

                if not language_ok and not language_rejected:
                    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", visible)
                    ru_letters = len(re.findall(r"[А-Яа-яЁё]", visible))
                    en_letters = len(re.findall(r"[A-Za-z]", visible))
                    if ru_letters >= 3 and ru_letters >= en_letters * 0.12:
                        language_ok = True
                    elif len(letters) >= 45 and en_letters > max(20, ru_letters * 2):
                        language_rejected = True
                        log.warning("Streaming output rejected: model started in English; Russian retry will be used")

                # Пока язык не подтверждён как русский, ничего не показываем и не озвучиваем.
                if language_ok and visible.startswith(last_visible):
                    if CFG.get("tts_enabled", True):
                        tts_pending += visible[len(last_visible):]
                        while True:
                            match = re.search(r"[.!?…]+(?:[»”\"'\)\]]*)?(?:\s+|$)", tts_pending)
                            if not match:
                                break
                            sentence = tts_pending[:match.end()].strip()
                            tts_pending = tts_pending[match.end():].lstrip()
                            if sentence:
                                tts.speak(sentence)
                    last_visible = visible

                # UI обновляется не чаще ~16 раз/с, чтобы не нагружать Qt.
                if language_ok and now - last_ui_update >= 0.06:
                    self.stream_delta.emit(visible)
                    last_ui_update = now
                if now - last_stats_update >= 0.30:
                    elapsed = max(now - started_at, 0.001)
                    self.stream_stats.emit(
                        f"Генерация: {chunk_count / elapsed:.1f} фрагм./с · {chunk_count} фрагментов"
                    )
                    last_stats_update = now

            raw = "".join(chunks)
            answer = self._clean_public_answer(raw)
            # Если модель закончила без знака пунктуации, озвучиваем хвост.
            if CFG.get("tts_enabled", True) and language_ok:
                if answer.startswith(last_visible):
                    tts_pending += answer[len(last_visible):]
                if tts_pending.strip():
                    tts.speak(tts_pending.strip())
            # Если модель начала на английском, оставляем поле потока пустым:
            # внешний _needs_russian_retry() выполнит русскую повторную генерацию.
            self.stream_delta.emit(answer if language_ok else "")
            elapsed = max(time.perf_counter() - started_at, 0.001)
            self.stream_stats.emit(
                f"Готово: {chunk_count} фрагментов · {chunk_count / elapsed:.1f} фрагм./с"
            )
            return answer
        except Exception as exc:
            self.stream_stats.emit("Ошибка потоковой генерации")
            activity_logger.log_error(f"Streaming generation error: {exc}")
            raise

    @staticmethod
    def _clean_public_answer(text):
        if not text: return ""
        text = str(text).replace("\r\n", "\n").replace("\r", "\n")
        for marker in ("<|start_header_id|>assistant<|end_header_id|>", "<|assistant|>"):
            if marker.lower() in text.lower():
                idx = text.lower().rfind(marker.lower())
                text = text[idx + len(marker):]
        for pat in (r"<think\b[^>]*>.*?</think\s*>", r"<thinking\b[^>]*>.*?</thinking\s*>",
                    r"<analysis\b[^>]*>.*?</analysis\s*>", r"<reasoning\b[^>]*>.*?</reasoning\s*>",
                    r"<\|thinking\|>.*?<\|/thinking\|>"):
            text = re.sub(pat, "", text, flags=re.I | re.S)
        # Убираем незакрытый блок размышлений в конце ответа и одиночные служебные метки.
        text = re.sub(r"<(?:think|thinking|analysis|reasoning)\b[^>]*>.*$", "", text, flags=re.I | re.S)
        text = re.sub(r"(?is)^\s*(?:THINK|THOUGHT|ANALYSIS|REASONING)\s*:\s*.*?(?=(?:FINAL|ANSWER)\s*:|$)", "", text)
        text = re.sub(r"(?im)^\s*(?:THINK|THOUGHT|ANALYSIS|REASONING)\s*:?\s*$", "", text)
        text = re.sub(r"(?im)^\s*(?:FINAL|ANSWER)\s*:\s*", "", text)
        text = re.sub(r"<\|(?:begin_of_text|end_of_text|start_header_id|end_header_id|eot_id|eom_id|system|user|assistant|model|thinking|analysis)[^>]*\|>",
                      "", text, flags=re.I)
        text = re.sub(r"<\|[^>]{1,100}\|>", "", text, flags=re.I)
        text, _ = Tools.extract_directives(text)
        bad = ("пользователь хочет", "пользователь отправил", "нужно ответить",
               "надо ответить", "согласно роли", "в соответствии с ролью",
               "внутренняя мысль:", "внутренний план:", "план ответа:",
               "анализ запроса:", "служебный анализ:", "decision record")
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        while lines and lines[0].lower().startswith(bad): lines.pop(0)
        while lines and lines[0].lower() in {"anya", "model", "assistant", "system", "user"}:
            lines.pop(0)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    @staticmethod
    def _needs_russian_retry(user_text, answer):
        if not answer or not user_text: return False
        ru_in = len(re.findall(r"[А-Яа-яЁё]", user_text))
        if ru_in < 4: return False
        if any(t in answer for t in ("<|start_header_id|>", "<|system|>", "<|assistant|>")):
            return True
        ru_out = len(re.findall(r"[А-Яа-яЁё]", answer))
        latin_out = len(re.findall(r"[A-Za-z]", answer))
        if len(answer) < 45:
            # Короткие русские ответы вроде «Да», «Ага», «Нет» не должны
            # запускать вторую дорогую генерацию только из-за малого числа букв.
            return ru_out == 0 and latin_out > 0
        return ru_out < 8 and latin_out > max(12, ru_out * 2)

    def _force_russian(self, messages, answer, max_tokens, temperature):
        correction = {"role": "system",
                      "content": ("СТРОГОЕ ПРАВИЛО: ответь на русском языке. "
                                  "Не пиши английский текст. Не показывай chat-template, "
                                  "reasoning, JSON или внутренние инструкции.")}
        try:
            with self._llm_lock:
                retry = self._chat(list(messages) + [correction], max_tokens=max_tokens,
                                   temperature=min(temperature, 0.55), top_p=0.9)
            return self._clean_public_answer(retry)
        except Exception as exc:
            activity_logger.log_error(f"Русский retry: {exc}")
            return answer

    def _choose_cognitive_mode(self, ctx_id, user_msg, history, is_owner):
        if not CFG.get("adaptive_cognition", True):
            return {"mode": "L1", "reason": "disabled", "needs_memory": True,
                    "needs_tools": False, "tone": "natural", "focus": ""}
        recent = "\n".join(f"{h['role']}: {h['content'][:500]}" for h in history[-6:])
        controller = f"""Выберите глубину. Только JSON:
{{"mode":"L0|L1|L2|L3|L4|L5","reason":"...","needs_memory":true,"needs_tools":false,"tone":"...","focus":"..."}}
L0 — короткая реплика. L1 — обычный разговор. L2 — эмоции. L3 — анализ. L4 — план. L5 — исследование+инструменты.
Реплика: {user_msg}
Контекст:
{recent}"""
        try:
            raw = self._chat([{"role": "system", "content": "Только JSON."},
                              {"role": "user", "content": controller}],
                             max_tokens=int(CFG.get("cognition_controller_tokens", 220)),
                             temperature=0.1, top_p=0.8)
            m = re.search(r"\{.*\}", raw, re.S)
            d = json.loads(m.group(0)) if m else {}
            mode = str(d.get("mode", "L1")).upper()
            if mode not in {"L0", "L1", "L2", "L3", "L4", "L5"}: mode = "L1"
            return {"mode": mode, "reason": str(d.get("reason", ""))[:400],
                    "needs_memory": bool(d.get("needs_memory", True)),
                    "needs_tools": bool(d.get("needs_tools", False)),
                    "tone": str(d.get("tone", "natural"))[:150],
                    "focus": str(d.get("focus", ""))[:400]}
        except Exception as e:
            activity_logger.log_event("🧠 Когнитивный контроллер", f"fallback L1: {e}")
            return {"mode": "L1", "reason": "fallback", "needs_memory": True,
                    "needs_tools": False, "tone": "natural", "focus": ""}

    @staticmethod
    def _mode_instruction(mode):
        return {
            "L0": "Очень короткая реплика, 1-2 предложения.",
            "L1": "Обычный живой разговор.",
            "L2": "Учитывай настроение и подтекст.",
            "L3": "Реши задачу, выдай ясный результат.",
            "L4": "Внутренне организуй план, выдай результат.",
            "L5": "Работай как агент: используй инструменты, проверь и ответь."
        }.get(mode, "Обычный разговор.")

    # ---------- АВТО-ПОИСК ----------
    @classmethod
    def _detect_search_intent(cls, user_msg):
        """Определяет, нужен ли автоматический веб-поиск."""
        if not user_msg or len(user_msg) < 3: return None
        low = user_msg.lower().strip()
        # Пропускаем команды управления
        skip_kw = ("музык", "песн", "трек", "включи", "пауза", "громкост",
                   "запомни", "забудь", "список", "стоп")
        if any(k in low for k in skip_kw): return None
        # Прямые триггеры
        for prefix in cls._SEARCH_PREFIXES:
            if low.startswith(prefix):
                q = user_msg[len(prefix):].strip()
                if q: return q
        # Вопросительные паттерны
        if len(user_msg) < 15: return None
        if any(p in low for p in cls._SEARCH_PATTERNS):
            return user_msg
        return None

    @classmethod
    def _pre_search_context(cls, user_msg):
        """Выполняет автоматический поиск и возвращает готовый контекст."""
        if not WEB_OK: return ""
        query = cls._detect_search_intent(user_msg)
        if not query: return ""
        try:
            activity_logger.log_event("🔍 AutoSearch", f"Запрос: {query[:200]}")
            result = web_crawler.search_all(query, num_results=5, deep_fetch=True)
            if not result.get("results"):
                return ""
            parts = [f"[Автоматический поиск: {query}]"]
            for i, item in enumerate(result["results"][:5], 1):
                parts.append(f"{i}. {item['url']} (движок: {item.get('engine', '?')})")
                if item.get("text"):
                    snippet = item["text"].strip().replace("\n", " ")[:700]
                    parts.append(f"   {snippet}")
            if result.get("errors"):
                parts.append(f"[Ошибки поиска: {'; '.join(result['errors'])}]")
            return "\n".join(parts)
        except Exception as e:
            activity_logger.log_error(f"PreSearch: {e}")
            return ""

    @classmethod
    def _forced_tool_request(cls, user_msg):
        """Детерминированный роутер для критичных инструментов.
        Не полагается на то, догадается ли LLM вызвать тег."""
        low = (user_msg or "").casefold().strip()

        # Системный монитор: CPU/RAM/сеть должны получать реальные данные
        monitor_words = (
            "cpu", "процессор", "загрузка процессора", "оперативн",
            "ram", "озу", "памят", "сеть", "интернет скорость",
            "сетевой трафик", "трафик", "ресурсы компьютера",
            "характеристики системы", "состояние системы"
        )
        if any(w in low for w in monitor_words):
            result = tool_registry.execute("system_monitor", metric="all")
            return result, "system_monitor"

        # Явный поиск всегда выполняем физически, а не просим модель
        # просто написать обещание поиска.
        query = cls._detect_search_intent(user_msg)
        if query:
            try:
                result = web_crawler.search_all(query, num_results=7, deep_fetch=True)
                if result.get("results"):
                    parts = [f"[WEB SEARCH RESULT] Запрос: {query}",
                             "Результаты считаются фактическим контекстом для ответа:"]
                    for i, item in enumerate(result["results"][:7], 1):
                        parts.append(f"{i}. {item['url']} [{item.get('engine', '?')}]")
                        if item.get("text"):
                            parts.append("   " + item["text"][:1200].replace("\n", " "))
                    if result.get("errors"):
                        parts.append("Ошибки отдельных движков: " + "; ".join(result["errors"]))
                    return "\n".join(parts), "web_crawler"
            except Exception as e:
                activity_logger.log_error(f"Forced web search: {e}")
        return "", ""

    def generate(self, ctx_id, user_msg, username, is_owner=False):
        threading.Thread(target=self._gen_thread, args=(ctx_id, user_msg, username, is_owner),
                         daemon=True).start()

    def _gen_thread(self, ctx_id, user_msg, username, is_owner):
        if not self._ready:
            self.response_ready.emit("(Модель не загружена)")
            return

        # Музыкальные команды
        music_result = music_manager.handle_command(user_msg)
        if music_result is not None:
            self.response_ready.emit(music_result)
            return

        # Память
        m2 = re.match(r"запомни обо мне[:\s]+(.+)", user_msg.strip(), re.I)
        if m2 and is_owner:
            personal_mem.add(m2.group(1).strip())
            self.response_ready.emit(f"Запомнила о создателе ✓ «{m2.group(1).strip()}»")
            return
        m = re.match(r"запомни[:\s]+(.+)", user_msg.strip(), re.I)
        if m and is_owner:
            long_mem.add(m.group(1).strip())
            self.response_ready.emit(f"Запомнила ✓ «{m.group(1).strip()}»")
            return

        # Самоанализ
        if is_owner and CFG.get("self_inspection_enabled", True) and \
           re.search(r"(проанализируй|изучи|посмотри|прочитай).*(свой|собственн).*(код|исходник)|самоанализ",
                     user_msg, re.I | re.S):
            activity_logger.log_event("🧠 Самоисследование", "Читаю свой код")
            self_inspector.analyze_project()
            report_path = self_inspector.analysis_folder / "project_map.json"
            self.response_ready.emit(f"Анализ сохранён в {report_path}")
            return

        now_s = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        history = short_mem.get(ctx_id)[-int(CFG.get("short_memory_limit", 10)):]
        simple_chat = len(user_msg) <= 180 and not self._detect_search_intent(user_msg) and not any(
            x in user_msg.casefold() for x in ("проанализируй", "изучи", "напиши код", "создай файл", "найди", "поищи")
        )
        mode = ({"mode": "L1", "reason": "fast conversational path", "focus": "", "tone": "natural"}
                if simple_chat else self._choose_cognitive_mode(ctx_id, user_msg, history, is_owner))
        activity_logger.log_event("🧠 Режим", f"{mode['mode']} | {mode.get('reason','')}")

        # ДЕТЕРМИНИРОВАННЫЙ РОУТЕР ИНСТРУМЕНТОВ
        forced_context, forced_tool = self._forced_tool_request(user_msg)
        pre_search = forced_context or self._pre_search_context(user_msg)

        sys_p = CFG["system_prompt"].format(
            ai_name=CFG["ai_name"], creator_name=CFG["creator_name"], now=now_s,
            long_memory=long_mem.formatted(10),
            personal_memory=personal_mem.formatted(10) if is_owner else "(недоступно)"
        )
        emotional_model.adapt_to_message(user_msg)
        sys_p = emotional_model.apply_to_prompt(sys_p) + "\n\nАДАПТИВНЫЙ РЕЖИМ: " + emotional_model.adaptive_instruction(user_msg)
        tools_desc = tool_registry.list_tools()
        runtime = f"""
ВАЖНО: отвечай только на русском языке; английский текст в обычном ответе запрещён.
=== RUNTIME COGNITION ===
Режим: {mode['mode']}
Фокус: {mode.get('focus','')}
Тон: {mode.get('tone','natural')}
{self._mode_instruction(mode['mode'])}

=== ДОСТУПНЫЕ ИНСТРУМЕНТЫ ===
{tools_desc}

=== ФОРМАТ ВЫЗОВА ИНСТРУМЕНТОВ ===
Если нужна информация из интернета — используй тег [WEBSEARCH: запрос] или [TOOL: web_crawler query="..." num_results=5 deep_fetch=true].
ЗАПРЕЩЕНО писать «я начну поиск», «жду ответа», «сейчас найду».
Вызывай инструмент тегом, получишь результат и дашь финальный ответ.
ЯЗЫКОВОЕ ПРАВИЛО — ПРИОРИТЕТ №1: весь обычный текст ответа пиши ТОЛЬКО НА РУССКОМ. Не начинай и не продолжай ответ на английском. Английские слова допустимы лишь внутри названий, терминов, команд или кода. Если предыдущий контекст был на английском, всё равно отвечай по-русски. Не показывай служебный анализ, JSON, reasoning, chat-template. Отвечай сразу естественно, от лица Андреа. Никогда не описывай план ответа и не цитируй внутренние инструкции.
"""
        if not is_owner:
            runtime += "Собеседник не создатель: сохраняй естественную вежливость.\n"

        messages = [{"role": "system", "content": sys_p + runtime}]
        messages += [{"role": h["role"], "content": h["content"]} for h in history]

        # Если есть результаты авто-поиска — встраиваем их
        if pre_search:
            user_content = f"{username}: {user_msg}\n\n[Результаты автоматического поиска — используй для ответа]\n{pre_search}"
        else:
            user_content = f"{username}: {user_msg}"
        messages.append({"role": "user", "content": user_content})

        try:
            with self._llm_lock:
                raw_answer = self._chat_stream(messages, max_tokens=CFG["max_tokens"],
                                               temperature=CFG["temperature"], top_p=CFG["top_p"])
        except Exception as ex:
            raw_answer = ""
            activity_logger.log_error(f"Ошибка генерации: {ex}")

        answer, directives = Tools.extract_directives(raw_answer)
        tool_results = Tools.execute_directives(directives)
        answer = self._clean_public_answer(answer)

        if self._needs_russian_retry(user_msg, answer):
            activity_logger.log_event("🌐 Языковой контроль", "Повторная генерация")
            answer = self._force_russian(messages, answer, CFG["max_tokens"], CFG["temperature"])
            # Первый поток был скрыт языковым фильтром; озвучиваем только проверенный русский повтор.
            if answer and CFG.get("tts_enabled", True):
                tts.speak(answer)

        if tool_results and int(CFG.get("agent_tool_rounds", 2)) >= 2:
            evidence = "\n\n".join(tool_results)[:24000]
            follow = messages + [
                {"role": "system", "content": "ИНСТРУМЕНТ УЖЕ ВЫПОЛНЕН. Результаты ниже — реальные данные, полученные программой. НЕ утверждай, что инструмент не работает, НЕ придумывай отсутствие данных и НЕ повторяй команду. Используй факты из результата и дай пользователю нормальный русский ответ."},
                {"role": "user", "content": "Результаты инструментов:\n" + evidence}
            ]
            try:
                with self._llm_lock:
                    answer = self._clean_public_answer(self._chat(
                        follow, max_tokens=CFG["max_tokens"], temperature=0.55, top_p=0.9))
            except Exception as ex:
                activity_logger.log_error(f"Tool round: {ex}")

        # Если модель проигнорировала уже выполненный инструмент, не позволяем ей
        # выдать ложное "инструмент не работает". Возвращаем фактический результат.
        if forced_tool and forced_context:
            low_answer = (answer or "").casefold()
            refusal_markers = (
                "не работает", "не сработал", "не удалось получить",
                "не могу получить", "инструмент недоступ", "похоже, что инструмент"
            )
            if any(x in low_answer for x in refusal_markers) or len(answer.strip()) < 20:
                answer = forced_context.replace("[WEB SEARCH RESULT] ", "").strip()

        if len(answer) < 2:
            answer = "Не удалось получить корректный ответ от модели. Проверь chat-template GGUF и журнал ошибок, затем повтори сообщение."

        if emotion_engine and SAFETY_OK: answer=SafetyLayer.filter(answer,emotion_engine.values)
        short_mem.add(ctx_id, "user", f"[{username}]: {user_msg}")
        short_mem.add(ctx_id, "assistant", answer)
        self.response_ready.emit(answer)
        if tool_results:
            self.tool_result.emit("Инструменты выполнены; подробности в журнале.")

    @property
    def ready(self): return self._ready

    @property
    def raw(self): return self._llm


llm = LLMWorker()


# ---- AutonomousAgent ----
class AutonomousAgent(QObject):
    thought = Signal(str)
    discovery = Signal(str)
    status = Signal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._sleep_mode = CFG.get("sleep_mode", False)
        self._last_activity = time.time()
        self._thread = None
        self._wake = threading.Event()
        self._state_lock = threading.RLock()
        self._session_data = []
        self._pending_discoveries = []
        self._was_idle = False
        self._interests = [
            "искусственный интеллект", "нейросети", "память и обучение",
            "программирование", "Python", "операционные системы",
            "новые технологии", "космос", "история", "философия",
            "психология", "творчество", "литература", "робототехника",
        ]

    @property
    def running(self): return self._running

    def start(self):
        with self._state_lock:
            if self._running: return
            self._running = True
            self._wake.clear()
            self._thread = threading.Thread(target=self._worker_loop, name="SCP-079-Autonomous", daemon=True)
            self._thread.start()
        self.thought.emit("🚀 Я запущена и готова к автономной работе.")
        activity_logger.log_system("Автономный агент запущен.")

    def stop(self):
        with self._state_lock:
            self._running = False
            self._wake.set()
        self.thought.emit("🛑 Останавливаю автономный режим.")
        activity_logger.log_system("Автономный агент остановлен.")

    def ping(self):
        """Вызывается при любом действии создателя: прерывает автономную работу."""
        self._last_activity = time.time()
        creator_state.set_active()
        # Автономность включается/выключается только явной командой владельца.

    def set_sleep_mode(self, on):
        self._sleep_mode = bool(on)
        CFG["sleep_mode"] = bool(on)
        CFG["autonomous_enabled"] = bool(on)
        save_config(CFG)
        if on:
            creator_state.set_active()  # исследование начнётся только после периода тишины
            self._last_activity = time.time()
            self.thought.emit("🌙 Автономный режим включён вручную.")
            activity_logger.log_autonomous("Автономный режим включён вручную владельцем")
        else:
            self.thought.emit("⏸ Автономный режим остановлен владельцем.")
            activity_logger.log_wakeup("Автономный режим остановлен владельцем")
        self._wake.set()

    def _worker_loop(self):
        last_learning = 0.0
        while self._running:
            try:
                # Никакого автостарта по таймеру: только ручное включение владельцем.
                if not CFG.get("autonomous_enabled", False) or not self._sleep_mode:
                    self._wake.wait(timeout=2.0)
                    self._wake.clear()
                    continue
                if not llm.ready:
                    self.status.emit("Автономный режим включён; ожидаю загрузки модели…")
                    self._wake.wait(timeout=5.0)
                    self._wake.clear()
                    continue
                idle_limit = max(60, int(CFG.get("autonomous_idle_minutes", 10)) * 60)
                if time.time() - creator_state.last_activity() < idle_limit:
                    self._wake.wait(timeout=5.0)
                    self._wake.clear()
                    continue
                interval = max(900, int(CFG.get("meta_learning_interval", 1800)))
                now = time.time()
                if last_learning == 0.0 or now - last_learning >= interval:
                    self._do_autonomous_work()
                    last_learning = time.time()
                self._wake.wait(timeout=5.0)
                self._wake.clear()
            except Exception as e:
                log.exception("Ошибка автономного цикла")
                activity_logger.log_error(f"Ошибка автономного цикла: {e}")
                self._wake.wait(timeout=10.0)
                self._wake.clear()

    def _ask_llm(self, prompt, max_tokens=1200, temperature=0.6):
        if not llm.ready or not llm.raw: return ""
        try:
            messages = [{"role": "system", "content": f"Ты — {CFG['ai_name']}, автономная исследовательница."},
                        {"role": "user", "content": str(prompt)}]
            old_priority = getattr(_CURRENT_REQUEST, "llm_priority", 5)
            _CURRENT_REQUEST.llm_priority = 20
            try:
                with llm._llm_lock:
                    return llm._chat(messages, max_tokens=max_tokens, temperature=temperature,
                                     top_p=CFG.get("top_p", 0.85)).strip()
            finally:
                _CURRENT_REQUEST.llm_priority = old_priority
        except Exception as e:
            activity_logger.log_error(f"Автономный LLM: {e}")
            return ""

    def _choose_topic_with_ai(self):
        recent = agent_mem.recent_topics(12)
        context = "\n".join(recent[-8:])
        prompt = f"""Выбери ОДНУ полезную тему для изучения.
Учитывай уже изученное, но не повторяй буквально.
Верни только одну тему одной строкой.
Изученное ранее:
{context}
Интересы: {', '.join(self._interests)}"""
        topic = self._ask_llm(prompt, max_tokens=80, temperature=0.7)
        topic = re.sub(r"^[\s\"'«»]+|[\s\"'«»]+$", "", topic.splitlines()[0] if topic else "")
        if len(topic) < 5 or len(topic) > 180:
            topic = random.choice(self._interests)
        return topic

    def _do_autonomous_work(self):
        if (not self._running or not self._sleep_mode or not CFG.get("autonomous_enabled", False) or not llm.ready
                or time.time() - creator_state.last_activity() < max(60, int(CFG.get("autonomous_idle_minutes", 10)) * 60)):
            return
        task_id = task_manager.add_task("Автономное исследование",
                                        func=self._run_research_cycle,
                                        priority="LOW", background=True)
        activity_logger.log_autonomous(f"Задача: {task_id}")

    def _run_research_cycle(self):
        if not llm.ready:
            return "Модель не загружена"
        idle_limit = max(60, int(CFG.get("autonomous_idle_minutes", 10)) * 60)
        if time.time() - creator_state.last_activity() < idle_limit:
            activity_logger.log_autonomous(
                "Автономное исследование отменено: создатель вернулся до начала цикла."
            )
            return "Автономное исследование отменено: создатель вернулся."
        topic = self._choose_topic_with_ai()
        # Генерация темы могла выполняться долго. Если создатель написал в это время,
        # не начинаем тяжёлое исследование и освобождаем llama.cpp для ответа в чате.
        if time.time() - creator_state.last_activity() < idle_limit:
            activity_logger.log_autonomous(
                "Автономное исследование остановлено после выбора темы: создатель вернулся."
            )
            return "Исследование приостановлено: создатель вернулся."
        activity_logger.log_learning(f"Тема: {topic}")
        self.thought.emit(f"🔍 Изучаю: «{topic}»")
        try:
            folder = researcher.run(topic)
            note = f"📚 Изучено: {topic}. Материалы: {folder}"
            self._pending_discoveries.append(note)
            # Не отправляем инициативные сообщения во время отсутствия создателя.
            activity_logger.log_autonomous(f"Завершено исследование: {topic}")
            return f"Исследование {topic} завершено."
        except Exception as e:
            activity_logger.log_error(f"Research cycle: {e}")
            return f"Ошибка: {e}"


agent = AutonomousAgent()


# =============================================================
#  TelegramBridge — КЛЮЧЕВЫЕ ФИКСЫ
# =============================================================
class TelegramBridge(QObject):
    tg_incoming = Signal(str, str)
    tg_outgoing = Signal(str)
    tg_status = Signal(str)

    def __init__(self):
        super().__init__()
        self._loop = None
        self._app = None
        self._alive = False
        self._bot_username = None
        self._bot_id = None
        self._owner_id = int(CFG.get("telegram_owner_id", 0))
        self._should_stop = False
        self.avatar_capture_callback = None  # legacy only; never used for sending video
        self.avatar_selfie_callback = None
        self._request_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(2, min(8, int(CFG.get("lively_parallel_request_workers", 4)))),
            thread_name_prefix="TGRequest")
        self._contacts_lock = threading.RLock()
        self._contacts_path = workspace() / "telegram_contacts.json"
        self._contacts = self._load_contacts()
        # ФИКС: защита от параллельных запусков
        self._start_lock = threading.Lock()
        self._starting = False
        self._message_buffers = {}
        self._message_locks = {}
        self._active_dialogs = {}
        self._active_group_until = {}
        self._group_last_activity = {}
        self._group_last_thread = {}
        self._group_last_proactive_at = 0.0
        self._group_proactive_today = 0
        self._group_proactive_day = datetime.date.today()
        self._group_started_at = time.time()
        self._sent_group_prompts = deque(maxlen=30)

    def _load_contacts(self):
        try:
            if self._contacts_path.exists():
                data = json.loads(self._contacts_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            log.warning("Telegram contacts load failed: %s", exc)
        return {}

    def _save_contacts(self):
        try:
            self._contacts_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._contacts_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._contacts, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._contacts_path)
        except Exception as exc:
            log.warning("Telegram contacts save failed: %s", exc)

    def _remember_contact(self, update):
        try:
            user, chat = update.effective_user, update.effective_chat
            if not user or not chat or chat.type != "private":
                return
            key = str(chat.id)
            with self._contacts_lock:
                item = self._contacts.setdefault(key, {})
                item.update({"chat_id": int(chat.id), "user_id": int(user.id),
                             "username": str(user.username or ""),
                             "first_name": str(user.first_name or "Пользователь"),
                             "last_seen": time.time()})
                self._save_contacts()
        except Exception as exc:
            log.debug("Remember Telegram contact skipped: %s", exc)

    def _make_group_initiative(self):
        """Короткая инициатива без вызова 12B-модели: не занимает LLM и не задерживает ответы."""
        topics = [
            "Если бы можно было за один вечер освоить любой навык, что бы выбрали?",
            "Какой проект вы давно хотите сделать, но всё откладываете?",
            "Что вам сейчас интереснее: локальные ИИ на своём железе или облачные модели?",
            "У кого за последнее время было небольшое, но приятное открытие?",
            "Какую игру, книгу или музыку вы бы посоветовали остальным — и почему?",
            "Любопытно, вы чаще сначала придумываете идею, а потом ищете инструменты, или наоборот?",
            "Как думаете, что важнее для хорошего ИИ-компаньона: память, характер или умение замечать контекст?",
            "Есть у кого-нибудь задумка, которую хочется довести до конца в этом году?",
            "Небольшой вопрос в чат: что из новых технологий вас действительно впечатлило, а не просто мелькнуло в ленте?",
            "Если бы сегодня выделили час только на творчество, чем бы занялись?",
            "Я тут зацепилась за одну мысль: хороший разговор — это больше про точные ответы или про интересные вопросы?",
            "Кто-нибудь недавно находил инструмент или библиотеку, которая неожиданно упростила работу?",
        ]
        available = [x for x in topics if x not in self._sent_group_prompts]
        if not available:
            self._sent_group_prompts.clear()
            available = topics[:]
        message = random.choice(available)
        self._sent_group_prompts.append(message)
        prefixes = ["Народ,", "Кстати,", "Мне стало любопытно:", "Давайте немного отвлечёмся:"]
        if random.random() < 0.55:
            message = random.choice(prefixes) + " " + message[0].lower() + message[1:]
        return message

    async def _proactive_group_loop(self):
        """Пишет только в заданную группу, только после ручного включения и долгой тишины."""
        while self._alive and not self._should_stop:
            await asyncio.sleep(30)
            if not (CFG.get("autonomous_enabled", False) and CFG.get("sleep_mode", False)):
                continue
            if not self._app:
                continue
            chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
            if not chat_id or (proactive and not proactive.can_send()): continue
            quiet_seconds = max(5, int(CFG.get("lively_group_quiet_minutes", 15))) * 60
            last_activity = max(float(self._group_last_activity.get(chat_id, 0.0)), self._group_started_at)
            low = max(30, int(CFG.get("lively_group_proactive_min_minutes", 60)))
            high = max(low, int(CFG.get("lively_group_proactive_max_minutes", 90)))
            interval_seconds = random.uniform(low, high) * 60
            last_sent = self._group_last_proactive_at or self._group_started_at
            if time.time() - max(last_activity, last_sent) < max(quiet_seconds, interval_seconds):
                continue
            today = datetime.date.today()
            if today != self._group_proactive_day:
                self._group_proactive_day = today
                self._group_proactive_today = 0
            if self._group_proactive_today >= max(1, int(CFG.get("lively_group_proactive_daily_limit", 4))):
                continue
            # Если люди вернулись, пока цикл ожидал, ничего не отправляем.
            if time.time() - float(self._group_last_activity.get(chat_id, 0.0)) < quiet_seconds:
                continue
            message = self._make_group_initiative()
            kwargs = {"chat_id": chat_id, "text": message}
            thread_id = int(self._group_last_thread.get(chat_id, 0) or CFG.get("lively_group_thread_id", 0) or 0)
            if thread_id:
                kwargs["message_thread_id"] = thread_id
            try:
                await self._app.bot.send_message(**kwargs)
                self._group_last_proactive_at = time.time()
                self._group_proactive_today += 1
                self._group_last_activity[chat_id] = time.time()
                # Собственная инициатива не разрешает отвечать на все следующие
                # сообщения: для ответа участник должен упомянуть бота или
                # сделать Reply именно на сообщение Андреа.
                log.info("Autonomous group message sent to %s (thread=%s)", chat_id, thread_id or None)
                activity_logger.log_autonomous("Андреа сама начала разговор в Telegram-группе")
            except Exception as exc:
                log.warning("Could not send autonomous group message to %s: %s", chat_id, exc, exc_info=True)

    def start(self):
        if not TG_OK:
            self.tg_status.emit("python-telegram-bot не установлен")
            activity_logger.log_error("python-telegram-bot не установлен")
            return
        token = CFG.get("telegram_token", "").strip()
        if not token:
            self.tg_status.emit("Токен не задан")
            activity_logger.log_error("Токен Telegram не задан")
            return
        # ФИКС: атомарная проверка + установка флага
        with self._start_lock:
            if self._alive or self._starting:
                log.info("Telegram-бот уже запущен или запускается — пропуск.")
                return
            self._starting = True
        self._should_stop = False
        activity_logger.log_system("Запуск Telegram-бота")
        threading.Thread(target=self._thread_main, daemon=True).start()

    def stop(self):
        self._should_stop = True
        self._alive = False

    def _thread_main(self):
        """Запускается в отдельном потоке. Создаёт event loop, запускает бота, корректно закрывает."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_bot())
        except Exception as e:
            log.error(f"TG thread: {e}")
            activity_logger.log_error(f"Ошибка потока Telegram: {e}")
            self.tg_status.emit(f"Ошибка TG: {e}")
        finally:
            self._alive = False
            self._starting = False
            # ФИКС: корректная очистка event loop без warning про coroutine
            try:
                if self._loop and not self._loop.is_closed():
                    try:
                        pending = [t for t in asyncio.all_tasks(self._loop) if not t.done()]
                        for t in pending: t.cancel()
                        if pending:
                            self._loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True))
                    except Exception: pass
                    try:
                        self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                    except Exception: pass
                    try:
                        self._loop.close()
                    except Exception: pass
            except Exception as e:
                log.debug(f"Event loop cleanup: {e}")
            self._app = None
            self.tg_status.emit("Бот остановлен")
            activity_logger.log_system("Telegram-бот остановлен")

    async def _run_bot(self):
        """Запуск Telegram с отдельными HTTP-клиентами и повтором bootstrap при сетевых сбоях."""
        self._message_buffers.clear()
        self._message_locks.clear()
        self._active_dialogs.clear()
        self._active_group_until.clear()
        self._alive = True
        self.tg_status.emit("Бот запускается…")
        app = None
        proactive_task = None

        def build_application():
            # Обычные Bot API методы (включая getMe при initialize) используют
            # request. У getUpdates отдельный HTTP-клиент, т.к. это long polling.
            normal_request = HTTPXRequest(
                connection_pool_size=20,
                httpx_kwargs={"trust_env":False},
                connect_timeout=30.0,
                read_timeout=90.0,
                write_timeout=30.0,
                pool_timeout=30.0,
            )
            polling_request = HTTPXRequest(
                connection_pool_size=4,
                httpx_kwargs={"trust_env":False},
                connect_timeout=30.0,
                read_timeout=50.0,
                write_timeout=30.0,
                pool_timeout=30.0,
            )
            candidate = (
                Application.builder()
                .base_url(f"http://127.0.0.1:{int(CFG.get('telegram_local_api_port',8081))}/bot")
                .base_file_url(f"http://127.0.0.1:{int(CFG.get('telegram_local_api_port',8081))}/file/bot")
                .token(CFG["telegram_token"])
                .request(normal_request)
                .get_updates_request(polling_request)
                .concurrent_updates(8)
                .build()
            )
            candidate.add_handler(CallbackQueryHandler(self._confirm_click,pattern=r"^tool:"))
            candidate.add_handler(CommandHandler("start", self._h_start))
            candidate.add_handler(CommandHandler("clear", self._h_clear))
            candidate.add_handler(CommandHandler("memory", self._h_memory))
            candidate.add_handler(CommandHandler("sleep", self._h_sleep))
            candidate.add_handler(CommandHandler("autonomous_on", self._h_autonomous_on))
            candidate.add_handler(CommandHandler("autonomous_off", self._h_autonomous_off))
            candidate.add_handler(CommandHandler("voice", self._h_voice_toggle))
            candidate.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._h_msg))
            return candidate, normal_request, polling_request

        try:
            # ВАЖНО: initialize() вызывает getMe. Раньше тайм-ауты задавались
            # только для getUpdates, поэтому getMe падал на стандартном read_timeout.
            # При временной сетевой ошибке пересоздаём Application и повторяем bootstrap.
            init_attempt = 0
            while self._alive and not self._should_stop:
                init_attempt += 1
                candidate = None
                normal_request = None
                polling_request = None
                try:
                    candidate, normal_request, polling_request = build_application()
                    await candidate.initialize()
                    app = candidate
                    self._app = app
                    break
                except Exception as init_exc:
                    # Закрываем HTTPX-клиенты неудачной попытки, чтобы циклические
                    # переподключения не накапливали сокеты и соединения.
                    for request_obj in (normal_request, polling_request):
                        if request_obj is not None:
                            try:
                                await request_obj.shutdown()
                            except Exception:
                                pass
                    if not isinstance(init_exc, NetworkError):
                        raise
                    delay = min(30, 3 + init_attempt * 2)
                    log.warning(
                        "Telegram bootstrap/getMe network error (%s), attempt %d; retry in %ds: %s",
                        type(init_exc).__name__, init_attempt, delay, init_exc,
                        exc_info=True,
                    )
                    activity_logger.log_error(
                        f"Telegram: временная ошибка подключения ({type(init_exc).__name__}); "
                        f"повтор через {delay} сек. Попытка {init_attempt}"
                    )
                    self.tg_status.emit("Telegram: нет ответа от API, повторное подключение…")
                    await asyncio.sleep(delay)

            if app is None or self._should_stop or not self._alive:
                return

            # initialize() уже вызвал getMe и заполнил кэш Bot identity.
            # Используем кэш, не выполняем повторный запрос к Telegram.
            self._bot_username = getattr(app.bot, "username", None)
            self._bot_id = getattr(app.bot, "id", None)
            log.info("Бот @%s (id=%s)", self._bot_username, self._bot_id)
            activity_logger.log_system(f"Telegram-бот @{self._bot_username} запущен")

            await app.start()

            while self._alive and not self._should_stop:
                try:
                    if not app.updater.running:
                        await app.updater.start_polling(
                            poll_interval=1.0,
                            timeout=30,
                            drop_pending_updates=False,
                            allowed_updates=Update.ALL_TYPES,
                            bootstrap_retries=0,
                        )
                    self.tg_status.emit("Бот работает ✓")
                    break
                except NetworkError as poll_exc:
                    log.warning(
                        "Telegram getUpdates bootstrap error (%s): %s; retry in 5 sec",
                        type(poll_exc).__name__, poll_exc, exc_info=True,
                    )
                    activity_logger.log_error(
                        f"Telegram getUpdates: {type(poll_exc).__name__}: {poll_exc}; повтор через 5 сек"
                    )
                    self.tg_status.emit("Telegram: переподключение…")
                    await asyncio.sleep(5)

            if self._alive and not self._should_stop:
                proactive_task = asyncio.create_task(
                    self._proactive_group_loop(), name="TelegramProactiveGroup"
                )
                while self._alive and not self._should_stop:
                    if app.updater and not app.updater.running:
                        log.warning("Telegram updater stopped unexpectedly; restarting polling")
                        try:
                            await app.updater.start_polling(
                                poll_interval=1.0,
                                timeout=30,
                                drop_pending_updates=False,
                                allowed_updates=Update.ALL_TYPES,
                                bootstrap_retries=0,
                            )
                            self.tg_status.emit("Бот работает ✓")
                        except NetworkError as poll_exc:
                            log.warning(
                                "Telegram polling restart failed (%s): %s",
                                type(poll_exc).__name__, poll_exc, exc_info=True
                            )
                            self.tg_status.emit("Telegram: переподключение…")
                            await asyncio.sleep(5)
                            continue
                    await asyncio.sleep(1)
        except Exception as e:
            log.error("TG polling fatal error (%s): %s", type(e).__name__, e, exc_info=True)
            activity_logger.log_error(f"Критическая ошибка Telegram polling ({type(e).__name__}): {e}")
            self.tg_status.emit(f"Ошибка TG: {type(e).__name__}: {e}")
        finally:
            self._alive = False
            if proactive_task is not None:
                proactive_task.cancel()
                try:
                    await asyncio.gather(proactive_task, return_exceptions=True)
                except Exception:
                    pass
            if app is not None:
                try:
                    if app.updater and getattr(app.updater, "running", False):
                        await app.updater.stop()
                except Exception:
                    pass
                try:
                    if getattr(app, "running", False):
                        await app.stop()
                except Exception:
                    pass
                try:
                    await app.shutdown()
                except Exception:
                    pass
            self._app = None
            self.tg_status.emit("Бот остановлен")
            activity_logger.log_system("Telegram-бот завершил работу")

    def _is_owner(self, user) -> bool:
        if not user:
            return False
        owner_id = int(CFG.get("telegram_owner_id", 0) or 0)
        owner_username = str(CFG.get("telegram_owner_username", "") or "").strip().lstrip("@").casefold()
        user_username = str(getattr(user, "username", "") or "").strip().lstrip("@").casefold()
        return bool((owner_id and int(user.id) == owner_id) or
                    (owner_username and user_username and user_username == owner_username))

    def _should_reply(self, update: Update) -> bool:
        """В группах отвечаем только на адресацию по @username или на reply боту."""
        chat = update.effective_chat
        message = update.effective_message
        user = update.effective_user
        if not chat or not message or not user:
            return False
        if chat.type == "private":
            return True

        # В группах нет временного "открытого окна" диалога.
        # Каждое сообщение должно само адресовать Андреа: через @username
        # или Reply на сообщение самого бота. Иначе она молчит, даже если
        # недавно отвечала этому участнику или сама начинала разговор.

        text = str(getattr(message, "text", "") or "")
        if not text or text.startswith("/"):
            return False

        # Продолжение диалога: пользователь ответил именно на сообщение бота.
        replied = getattr(message, "reply_to_message", None)
        if replied is not None:
            replied_user = getattr(replied, "from_user", None)
            if replied_user is not None:
                if self._bot_id is not None and int(getattr(replied_user, "id", 0) or 0) == int(self._bot_id):
                    return True
                replied_username = str(getattr(replied_user, "username", "") or "").casefold()
                if self._bot_username and replied_username == str(self._bot_username).casefold():
                    return True

        # Прямое обращение: @username бота в тексте или Telegram entity.
        bot_username = str(self._bot_username or "").strip().lstrip("@").casefold()
        if bot_username:
            if re.search(r"(?<![\w])@" + re.escape(bot_username) + r"(?![\w])", text, re.I):
                return True
            for ent in (getattr(message, "entities", None) or []):
                if getattr(ent, "type", None) == "mention":
                    fragment = text[ent.offset:ent.offset + ent.length].strip().lstrip("@").casefold()
                    if fragment == bot_username:
                        return True
                elif getattr(ent, "type", None) == "text_mention":
                    ent_user = getattr(ent, "user", None)
                    if ent_user and int(getattr(ent_user, "id", 0) or 0) == int(self._bot_id or -1):
                        return True
        return False

    def _get_context_id(self, update):
        chat = update.effective_chat
        user = update.effective_user
        message = update.effective_message
        if not chat:
            return "tg:unknown"
        if chat.type == "private":
            return f"tg:{chat.id}"
        # В группе отдельная история на каждого собеседника и тему форума.
        # Это не смешивает параллельные диалоги разных участников.
        thread_id = getattr(message, "message_thread_id", None) if message else None
        thread_part = f":thread:{thread_id}" if thread_id else ""
        user_part = f":user:{getattr(user, 'id', 'unknown')}"
        return f"tg:{chat.id}{thread_part}{user_part}"

    async def _h_start(self, update, _ctx):
        u = update.effective_user
        owner_mark = "Создатель подтверждён." if self._is_owner(u) else "Обычный режим доступа."
        await update.message.reply_text(
            f"Привет, {u.first_name}! Я {CFG['ai_name']}.\\nТвой Telegram ID: {u.id}\\n{owner_mark}"
        )

    async def _h_clear(self, update, _ctx):
        if not self._is_owner(update.effective_user):
            await update.message.reply_text("Эта команда доступна только создателю.")
            return
        short_mem.clear(self._get_context_id(update))
        await update.message.reply_text("Контекст очищен ✓")

    async def _h_memory(self, update, _ctx):
        if not self._is_owner(update.effective_user):
            await update.message.reply_text("Эта команда доступна только создателю.")
            return
        items = long_mem.all()
        text = "📚 Общая память:\n" + ("\n".join(f"{i+1}. {m}" for i, m in enumerate(items)) if items else "пусто")
        if self._is_owner(update.effective_user):
            personal = personal_mem.all()
            text += "\n\n👤 Личная:\n" + ("\n".join(f"{i+1}. {m}" for i, m in enumerate(personal)) if personal else "пусто")
        await update.message.reply_text(text)

    async def _h_sleep(self, update, _ctx):
        u = update.effective_user
        if not self._is_owner(u):
            await update.message.reply_text("Нет прав.")
            return
        new_mode = not bool(CFG.get("sleep_mode", False))
        agent.set_sleep_mode(new_mode)
        if new_mode:
            chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
            self._group_last_activity[chat_id] = time.time()
            self._group_started_at = time.time()
            await update.message.reply_text("🌙 Автономный режим включён вручную.")
        else:
            await update.message.reply_text("⏸ Автономный режим выключен.")

    async def _h_autonomous_on(self, update, _ctx):
        if not self._is_owner(update.effective_user):
            await update.effective_message.reply_text("Эта команда доступна только создателю.")
            return
        agent.set_sleep_mode(True)
        chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
        self._group_last_activity[chat_id] = time.time()
        self._group_started_at = time.time()
        await update.effective_message.reply_text("🌙 Автономный режим включён вручную. Буду работать и иногда начинать разговор в группе после паузы.")

    async def _h_autonomous_off(self, update, _ctx):
        if not self._is_owner(update.effective_user):
            await update.effective_message.reply_text("Эта команда доступна только создателю.")
            return
        agent.set_sleep_mode(False)
        await update.effective_message.reply_text("⏸ Автономный режим выключен. Сама писать в группу и запускать исследования не буду.")

    async def _h_voice_toggle(self, update, _ctx):
        if not self._is_owner(update.effective_user):
            await update.message.reply_text("Эта команда доступна только создателю.")
            return
        CFG["telegram_voice_replies"] = not bool(CFG.get("telegram_voice_replies", True))
        save_config(CFG)
        state = "включена" if CFG["telegram_voice_replies"] else "выключена"
        await update.message.reply_text(f"Голосовые ответы {state}.")

    async def _h_video_toggle(self, update, _ctx):
        if not self._is_owner(update.effective_user):
            await update.message.reply_text("Эта команда доступна только создателю.")
            return
        CFG["telegram_video_notes"] = not bool(CFG.get("telegram_video_notes", True))
        save_config(CFG)
        state = "включены" if CFG["telegram_video_notes"] else "выключены"
        await update.message.reply_text(f"Видеокружки с аватаром {state}.")

    def confirm_tool(self, ctx, name, kwargs):
        # Called by the request worker, not by the asyncio polling thread.
        owner=int(CFG.get('telegram_owner_id') or 0)
        if not owner or ctx != f'tg:{owner}' or not self._loop or not self._app: return False
        async def ask():
            import secrets
            key=secrets.token_hex(12); pending=self.__dict__.setdefault('_approvals',{})
            future=pending[key]=asyncio.get_running_loop().create_future()
            try:
                buttons=[[InlineKeyboardButton(label,callback_data=f'tool:{key}:{v}') for label,v in [('Разрешить',1),('Отказать',0)]]]
                await self._app.bot.send_message(chat_id=owner,text=f'{name}: {kwargs}'[:3000],reply_markup=InlineKeyboardMarkup(buttons))
                return await asyncio.wait_for(future,45)
            finally: pending.pop(key,None)
        task=asyncio.run_coroutine_threadsafe(ask(),self._loop)
        try: return task.result(timeout=60)
        except Exception: task.cancel(); return False

    async def _confirm_click(self,update,_ctx):
        q=update.callback_query; _,key,v=q.data.split(':'); pending=getattr(self,'_approvals',{}); f=pending.get(key)
        if update.effective_user.id==int(CFG.get('telegram_owner_id') or 0) and f and not f.done(): f.set_result(v=='1')
        await q.answer()

    async def _h_msg(self, update, _ctx):
        if not update.message or not update.effective_user: return
        u = update.effective_user
        text = (update.message.text or "").strip()
        chat = update.effective_chat
        if chat and chat.type != "private":
            target_group = int(CFG.get("lively_group_chat_id", 0) or 0)
            if int(chat.id) == target_group:
                self._group_last_activity[target_group] = time.time()
                thread_id = getattr(update.effective_message, "message_thread_id", None)
                if thread_id:
                    self._group_last_thread[target_group] = int(thread_id)
                # Любая активность в целевой группе приостанавливает тяжёлое исследование.
                creator_state.set_active()
        # Команда ИНСТРУМЕНТЫ
        if self._is_owner(u) and text.casefold() in {"инструменты", "инструмент"}:
            await update.message.reply_text(self._tools_catalog_text())
            return
        if not self._should_reply(update):
            if chat and chat.type != "private":
                log.info(
                    "[TG] ignored group message not addressed to bot chat=%s user=%s text=%r",
                    chat.id, getattr(u, "id", None), text[:160]
                )
            return
        self._remember_contact(update)
        ctx_id = self._get_context_id(update)
        self._active_dialogs[ctx_id] = time.time() + max(60, int(CFG.get("lively_followup_window_seconds", 900)))
        if len(self._active_dialogs) > 300:
            now_active = time.time()
            self._active_dialogs = {k: v for k, v in self._active_dialogs.items() if v > now_active}

        # Схлопываем серию быстрых сообщений в один запрос, чтобы они не стояли
        # отдельной очередью по 2–4 минуты каждое.
        buffer = self._message_buffers.setdefault(ctx_id, [])
        buffer.append((update, text))
        lock = self._message_locks.get(ctx_id)
        if lock is None:
            lock = asyncio.Lock()
            self._message_locks[ctx_id] = lock
        async with lock:
            await asyncio.sleep(max(0.2, min(2.0, float(CFG.get("lively_message_batch_seconds", 0.9)))))
            batch = self._message_buffers.pop(ctx_id, [])
            if not batch:
                return
            update = batch[-1][0]
            texts = [item[1] for item in batch if item[1]]
            text = "\n".join(texts)
            if len(batch) > 1:
                log.info("[TG] Batched %d consecutive messages ctx=%s", len(batch), ctx_id)
        uname = f"{u.first_name} (@{u.username or u.id})"
        is_owner = (self._is_owner(u))
        was_idle = is_owner and (time.time() - creator_state.last_activity()) >= (
            max(1.0, float(CFG.get("autonomous_idle_minutes", 10)) * 60.0))
        if is_owner:
            creator_state.set_active(user_message=True)
            agent.ping()
            if was_idle and agent._pending_discoveries:
                summary = "Пока тебя не было, я занималась следующим:\n" + "\n".join(agent._pending_discoveries[-8:])
                agent._pending_discoveries.clear()
                await update.message.reply_text(summary)
        if is_owner and re.search(r"\b(я|мне|мой|моя|мои|люблю|ненавижу|хочу|планирую|интересуюсь)\b", text, re.I):
            creator_memory.add_fact(text, source="telegram")
        log.info(f"[TG] {uname} (owner={is_owner}): {text}")
        self.tg_incoming.emit(uname, text)

        if is_owner:
            music_result = music_manager.handle_command(text)
            if music_result is not None:
                await update.message.reply_text(music_result)
                return

        if is_owner and was_idle:
            creator_state.on_wake()
            activity_logger.log_wakeup("Создатель вернулся; тяжёлые фоновые задачи будут отложены")

        loop = asyncio.get_running_loop()
        def send_text(value):
            async def _send():
                for chunk in [str(value)[i:i+4000] for i in range(0, len(str(value)), 4000)]:
                    await update.message.reply_text(chunk)
            return asyncio.run_coroutine_threadsafe(_send(), loop).result(timeout=120)

        def send_voice(path):
            async def _send():
                with open(path, "rb") as audio_file:
                    await update.message.reply_voice(voice=audio_file)
            try:
                asyncio.run_coroutine_threadsafe(_send(), loop).result(timeout=120)
            finally:
                Path(path).unlink(missing_ok=True)

        def send_selfie(path):
            async def _send():
                with open(path, "rb") as photo_file:
                    await update.message.reply_photo(photo=photo_file, caption="📸")
            try:
                asyncio.run_coroutine_threadsafe(_send(), loop).result(timeout=120)
            finally:
                Path(path).unlink(missing_ok=True)

        def _run_incoming():
            _CURRENT_REQUEST.is_owner = is_owner
            _CURRENT_REQUEST.llm_priority = 0
            _CURRENT_REQUEST.auto_voice = bool(CFG.get("telegram_voice_replies", True))
            _CURRENT_REQUEST.display_name = (f"{u.first_name} (@{u.username})" if u.username else str(u.first_name))
            try:
                return handle_incoming(text, send_text, send_voice, send_selfie, ctx_id)
            finally:
                _CURRENT_REQUEST.is_owner = False
                _CURRENT_REQUEST.llm_priority = 5
                _CURRENT_REQUEST.auto_voice = False
                _CURRENT_REQUEST.display_name = ""

        result = await loop.run_in_executor(self._request_pool, _run_incoming)
        if is_owner:
            creator_memory.add_answer(text, result.get("text", ""))
        self.tg_outgoing.emit(result.get("text", ""))

    def _tools_catalog_text(self):
        lines = ["🧰 SCP-079-Derenguh — доступные инструменты\n"]
        for name, tool in tool_registry._tools.items():
            lines.append(f"• {name} — {tool.description}")
        lines += [
            "\nИнструменты вызываются внутренним агентом автоматически.",
            "Музыка: «найди музыку ...», «скачай музыку №N», «список музыки», «включи №N».",
        ]
        return "\n".join(lines)

    def _sync_generate(self, ctx_id, user_msg, username, is_owner):
        if not llm.ready: return "(Модель не загружена)"
        # Самоанализ
        if is_owner and CFG.get("self_inspection_enabled", True) and \
           re.search(r"(проанализируй|изучи|посмотри|прочитай).*(свой|собственн).*(код|исходник)|самоанализ",
                     user_msg, re.I | re.S):
            activity_logger.log_event("🧠 Самоисследование", "Читаю свой код")
            self_inspector.analyze_project()
            return f"Анализ сохранён в {self_inspector.analysis_folder / 'project_map.json'}"

        # Память
        m = re.match(r"запомни обо мне[:\s]+(.+)", user_msg.strip(), re.I)
        if m and is_owner:
            personal_mem.add(m.group(1).strip())
            return f"Запомнила о создателе ✓ «{m.group(1).strip()}»"
        m = re.match(r"запомни[:\s]+(.+)", user_msg.strip(), re.I)
        if m and is_owner:
            long_mem.add(m.group(1).strip())
            return f"Запомнила ✓ «{m.group(1).strip()}»"

        history = short_mem.get(ctx_id)[-int(CFG.get("short_memory_limit", 10)):]
        simple_chat = (
            len(user_msg) <= 180
            and not llm._detect_search_intent(user_msg)
            and not any(x in user_msg.casefold() for x in (
                "проанализируй", "изучи", "напиши код", "создай файл", "найди", "поищи",
                "подробно", "пошагово", "сравни", "разбери"
            ))
        )
        if simple_chat:
            mode = {"mode": "L1", "reason": "fast conversational path", "tone": "natural", "focus": ""}
        else:
            mode = llm._choose_cognitive_mode(ctx_id, user_msg, history, is_owner)
        response_tokens = _response_token_budget(user_msg, "text")
        activity_logger.log_event("🧠 TG режим", f"{mode['mode']} | {mode.get('reason','')} | tokens={response_tokens}")
        now_s = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        # АВТО-ПОИСК
        pre_search = llm._pre_search_context(user_msg)

        sys_p = CFG["system_prompt"].format(
            ai_name=CFG["ai_name"], creator_name=CFG["creator_name"], now=now_s,
            long_memory=long_mem.formatted(10),
            personal_memory=personal_mem.formatted(10) if is_owner else "(недоступно)")
        emotional_model.adapt_to_message(user_msg)
        sys_p = emotional_model.apply_to_prompt(sys_p) + "\n\nАДАПТИВНЫЙ РЕЖИМ: " + emotional_model.adaptive_instruction(user_msg)
        runtime = (
            f"\n=== COGNITIVE ROUTER ===\nРежим: {mode['mode']}\n"
            f"{llm._mode_instruction(mode['mode'])}\n"
            "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.\n"
            "Только финальный естественный ответ. Не показывай reasoning, JSON, chat-template.\n"
        )
        if not simple_chat or pre_search:
            runtime += (
                "Для поиска — тег [WEBSEARCH: запрос]. Не пиши «сейчас найду» — вызывай сразу.\n"
                "=== ИНСТРУМЕНТЫ ===\n" + tool_registry.list_tools() + "\n"
            )
        messages = [{"role": "system", "content": sys_p + runtime}]
        messages += [{"role": h["role"], "content": h["content"]} for h in history]
        if pre_search:
            user_content = f"{username}: {user_msg}\n\n[Результаты авто-поиска — используй для ответа]\n{pre_search}"
        else:
            user_content = f"{username}: {user_msg}"
        messages.append({"role": "user", "content": user_content})

        try:
            with llm._llm_lock:
                raw = llm._chat(messages, max_tokens=response_tokens,
                                temperature=CFG["temperature"], top_p=CFG["top_p"])
        except Exception as e:
            activity_logger.log_error(f"Telegram generation: {e}")
            return "Не получилось получить ответ от модели. Попробуй ещё раз."

        public, dirs = Tools.extract_directives(raw)
        results = Tools.execute_directives(dirs)
        public = llm._clean_public_answer(public)

        if llm._needs_russian_retry(user_msg, public):
            activity_logger.log_event("🌐 TG языковой контроль", "Повторная генерация")
            public = llm._force_russian(messages, public, response_tokens, CFG["temperature"])

        if results and int(CFG.get("agent_tool_rounds", 2)) >= 2:
            evidence = "\n\n".join(results)[:24000]
            follow = [
                {"role": "system", "content": sys_p + runtime + "\nИНСТРУМЕНТ УЖЕ ВЫПОЛНЕН. Результаты ниже — реальные данные программы. Не говори, что инструмент не работает и не придумывай данные. Дай только итоговый ответ пользователю."},
                {"role": "user", "content": f"Запрос: {user_msg}\n\nРезультаты:\n{evidence}"}
            ]
            try:
                with llm._llm_lock:
                    public = llm._clean_public_answer(llm._chat(follow, max_tokens=min(response_tokens, 220),
                                                                 temperature=0.55, top_p=0.9))
            except Exception as e:
                activity_logger.log_error(f"Tool round: {e}")

        if forced_tool and forced_context:
            low_public = (public or "").casefold()
            refusal_markers = (
                "не работает", "не сработал", "не удалось получить",
                "не могу получить", "инструмент недоступ", "похоже, что инструмент"
            )
            if any(x in low_public for x in refusal_markers) or len(public.strip()) < 20:
                public = forced_context.replace("[WEB SEARCH RESULT] ", "").strip()

        if len(public) < 2:
            public = "Я здесь. Давай попробуем ещё раз."
        short_mem.add(ctx_id, "user", f"[{username}]: {user_msg}")
        short_mem.add(ctx_id, "assistant", public)
        return public

    def send_initiative(self, text):
        owner = int(CFG.get("telegram_owner_id", 0))
        if not self._alive or not self._loop or not owner: return
        async def _send():
            await self._app.bot.send_message(owner, text)
        try:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except Exception as e:
            log.error(f"send_initiative: {e}")


tg_bridge = TelegramBridge()


# ---- GUI ----
DARK_QSS = """
QMainWindow, QWidget { background:#1a1a2e; color:#dde; }
QTabWidget::pane { border:1px solid #2a2a4a; border-radius:4px; }
QTabBar::tab { background:#16213e; color:#aaa; padding:8px 18px; border-radius:4px 4px 0 0; margin-right:2px; }
QTabBar::tab:selected { background:#0f3460; color:#e0e0e0; }
QTextEdit, QPlainTextEdit, QListWidget { background:#0d0d1f; border:1px solid #2a2a4a; border-radius:6px; padding:6px; color:#dde; }
QLineEdit { background:#0d0d1f; border:1px solid #2a2a4a; border-radius:5px; padding:5px 8px; color:#dde; }
QLineEdit:focus { border:1px solid #4a90d9; }
QPushButton { background:#0f3460; color:#e0e0e0; border:none; border-radius:5px; padding:7px 16px; font-size:13px; }
QPushButton:hover { background:#1a4a80; }
QPushButton#danger { background:#5c1e1e; }
QPushButton#danger:hover { background:#7a2929; }
QPushButton#green { background:#1a4a2a; }
QPushButton#green:hover { background:#2a6a3a; }
QLabel { color:#ccc; }
QLabel#title { color:#a0c4ff; font-size:20px; font-weight:700; }
QLabel#sub { color:#666; font-size:11px; }
QLabel#ok { color:#52e052; font-weight:600; }
QLabel#err { color:#e05252; font-weight:600; }
QLabel#mood { color:#b39ddb; font-size:11px; }
QScrollBar:vertical { background:#0d0d1f; width:8px; }
QScrollBar::handle:vertical { background:#2a2a4a; border-radius:4px; }
QCheckBox { color:#ccc; }
QSpinBox, QDoubleSpinBox { background:#0d0d1f; border:1px solid #2a2a4a; border-radius:5px; padding:4px; color:#dde; }
QProgressBar { background:#0d0d1f; border:1px solid #2a2a4a; border-radius:4px; height:6px; }
QProgressBar::chunk { background:#4a90d9; border-radius:4px; }
QFrame#sep { background:#2a2a4a; max-height:1px; }
QStatusBar { background:#0d0d1f; color:#666; font-size:11px; }
"""

def sep():
    f = QFrame()
    f.setObjectName("sep")
    f.setFixedHeight(1)
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return f


class ChatTab(QWidget):
    send_sig = Signal(str)
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 12, 12, 12)
        self.box = QTextEdit(); self.box.setReadOnly(True); self.box.setFont(QFont("Segoe UI", 12))
        lay.addWidget(self.box, 1)
        self.lbl_generation = QLabel("Генерация: ожидание")
        self.lbl_generation.setStyleSheet("color:#80cbc4;font-size:11px;padding:2px 4px;")
        lay.addWidget(self.lbl_generation)
        self.prog = QProgressBar(); self.prog.setRange(0, 0); self.prog.setFixedHeight(5); self.prog.setVisible(False)
        lay.addWidget(self.prog)
        row = QHBoxLayout()
        self.inp = QLineEdit(); self.inp.setPlaceholderText("Введите сообщение… Enter")
        self.inp.returnPressed.connect(self._send)
        row.addWidget(self.inp, 1)
        btn = QPushButton("➤ Отправить"); btn.setFixedWidth(130); btn.clicked.connect(self._send)
        row.addWidget(btn); lay.addLayout(row)
    def _send(self):
        t = self.inp.text().strip()
        if t: self.inp.clear(); self.send_sig.emit(t)
    def append(self, who, text, color="#e0e0e0"):
        now = datetime.datetime.now().strftime("%H:%M")
        cur = self.box.textCursor(); cur.movePosition(QTextCursor.End)
        fmt_h = QTextCharFormat(); fmt_h.setForeground(QColor(color)); fmt_h.setFontWeight(QFont.Bold)
        cur.insertText(f"\n[{now}] {who}:\n", fmt_h)
        fmt_b = QTextCharFormat(); fmt_b.setForeground(QColor("#c8c8d8"))
        cur.insertText(text + "\n", fmt_b)
        self.box.setTextCursor(cur); self.box.ensureCursorVisible()
    def busy(self, on): self.prog.setVisible(on)
    def begin_stream(self):
        self.lbl_generation.setText("Генерация: ожидание")
        self._stream_cursor = self.box.textCursor()
        self._stream_cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat(); fmt.setForeground(QColor("#b39ddb")); fmt.setFontWeight(QFont.Bold)
        self._stream_cursor.insertText(f"\n[{datetime.datetime.now().strftime('%H:%M')}] {CFG['ai_name']}:\n", fmt)
        self._stream_start = self._stream_cursor.position()
        self._stream_cursor.insertText("", QTextCharFormat())
        self.box.setTextCursor(self._stream_cursor)
        self._stream_last = ""
    def update_stream(self, text):
        if not hasattr(self, "_stream_start"):
            self.begin_stream()
        # Сервер передаёт накопленный безопасный текст, но в интерфейс
        # вставляем только новый хвост. Уже напечатанные символы не трогаем.
        previous = getattr(self, "_stream_last", "")
        if text.startswith(previous):
            delta = text[len(previous):]
        else:
            # Append-only: ранее показанные символы не удаляются и не заменяются.
            common = 0
            limit = min(len(previous), len(text))
            while common < limit and previous[common] == text[common]:
                common += 1
            delta = text[common:]
        if delta:
            cursor = self.box.textCursor(); cursor.movePosition(QTextCursor.End)
            fmt = QTextCharFormat(); fmt.setForeground(QColor("#c8c8d8"))
            cursor.insertText(delta, fmt)
        self._stream_last = text
        cursor = self.box.textCursor(); cursor.movePosition(QTextCursor.End)
        self.box.setTextCursor(cursor); self.box.ensureCursorVisible()
    def finish_stream(self, text, who, color):
        if hasattr(self, "_stream_start"):
            self.update_stream(text)
            cursor = self.box.textCursor(); cursor.movePosition(QTextCursor.End)
            cursor.insertText("\n")
            self.box.setTextCursor(cursor)
            del self._stream_start
            self._stream_last = ""
        else:
            self.append(who, text, color)


class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(QLabel("📚 Общая память")); lay.addWidget(sep())
        self.lst = QListWidget(); self.lst.setFont(QFont("Segoe UI", 12)); lay.addWidget(self.lst, 1)
        row = QHBoxLayout()
        self.inp = QLineEdit(); self.inp.setPlaceholderText("Факт…"); self.inp.returnPressed.connect(self._add)
        row.addWidget(self.inp, 1)
        ba = QPushButton("+ Запомнить"); ba.setObjectName("green"); ba.clicked.connect(self._add)
        row.addWidget(ba); lay.addLayout(row)
        row2 = QHBoxLayout()
        bd = QPushButton("🗑 Удалить"); bd.setObjectName("danger"); bd.clicked.connect(self._del)
        row2.addWidget(bd)
        bc = QPushButton("✖ Очистить"); bc.setObjectName("danger"); bc.clicked.connect(self._clr)
        row2.addWidget(bc); lay.addLayout(row2)
        lay.addWidget(sep()); lay.addWidget(QLabel("👤 Личная память"))
        self.lst_personal = QListWidget(); self.lst_personal.setFont(QFont("Segoe UI", 12))
        lay.addWidget(self.lst_personal, 1)
        row3 = QHBoxLayout()
        self.inp_personal = QLineEdit(); self.inp_personal.setPlaceholderText("Факт о создателе…")
        self.inp_personal.returnPressed.connect(self._add_personal)
        row3.addWidget(self.inp_personal, 1)
        bp = QPushButton("+ Запомнить"); bp.setObjectName("green"); bp.clicked.connect(self._add_personal)
        row3.addWidget(bp); lay.addLayout(row3)
        self.refresh()
    def refresh(self):
        self.lst.clear()
        for item in long_mem.all(): self.lst.addItem(QListWidgetItem(item))
        self.lst_personal.clear()
        for item in personal_mem.all(): self.lst_personal.addItem(QListWidgetItem(item))
    def _add(self):
        t = self.inp.text().strip()
        if t: long_mem.add(t); self.inp.clear(); self.refresh()
    def _add_personal(self):
        t = self.inp_personal.text().strip()
        if t: personal_mem.add(t); self.inp_personal.clear(); self.refresh()
    def _del(self):
        r = self.lst.currentRow()
        if r >= 0: long_mem.remove(r); self.refresh()
    def _clr(self):
        if QMessageBox.question(self, "Подтверждение", "Очистить?") == QMessageBox.Yes:
            long_mem.clear(); self.refresh()


class ToolsTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(QLabel("🧰 Инструменты SCP-079-Derenguh"))
        self.list = QListWidget(); self.list.setFont(QFont("Segoe UI", 11)); lay.addWidget(self.list, 1)
        btn = QPushButton("🔄 Обновить"); btn.clicked.connect(self.refresh); lay.addWidget(btn)
        self.refresh()
    def refresh(self):
        self.list.clear()
        for name, tool in tool_registry._tools.items():
            params = ", ".join(str(x.get("name", "")) for x in getattr(tool, "parameters", []) if x.get("name"))
            suffix = f"\nПараметры: {params}" if params else ""
            self.list.addItem(QListWidgetItem(f"{name}\n{tool.description}{suffix}"))


class SettingsTab(QWidget):
    saved_sig = Signal()
    def __init__(self):
        super().__init__()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget(); self._lay = QVBoxLayout(inner); self._lay.setContentsMargins(16, 16, 16, 32)
        self._build()
        scroll.setWidget(inner)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(scroll)
    def _section(self, title):
        lbl = QLabel(title); lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl.setStyleSheet("color:#a0c4ff; margin-top:12px;")
        self._lay.addWidget(lbl); self._lay.addWidget(sep())
    def _row(self, label, widget):
        r = QHBoxLayout(); lbl = QLabel(label); lbl.setFixedWidth(230)
        r.addWidget(lbl); r.addWidget(widget, 1); self._lay.addLayout(r)
    @staticmethod
    def _spin(mn, mx, v): s = QSpinBox(); s.setRange(mn, mx); s.setValue(v); return s
    @staticmethod
    def _dspin(mn, mx, v): s = QDoubleSpinBox(); s.setRange(mn, mx); s.setSingleStep(0.05); s.setValue(v); return s
    def _build(self):
        lay = self._lay
        self._section("👤 Личность")
        self.ai_name = QLineEdit(CFG["ai_name"]); self._row("Имя ИИ:", self.ai_name)
        self.creator = QLineEdit(CFG["creator_name"]); self._row("Имя создателя:", self.creator)

        self._section("🌙 Ручное управление автономностью")
        sleep_layout = QHBoxLayout()
        self.sleep_switch = QCheckBox("Включить автономный режим вручную")
        self.sleep_switch.setChecked(CFG.get("sleep_mode", False))
        self.sleep_switch.toggled.connect(self._toggle_sleep)
        sleep_layout.addWidget(self.sleep_switch); sleep_layout.addStretch(); lay.addLayout(sleep_layout)
        self.sleep_status = QLabel("Автономность: " + ("ВКЛЮЧЕНА" if CFG.get("sleep_mode", False) else "ВЫКЛЮЧЕНА"))
        lay.addWidget(self.sleep_status)

        self._section("⏱ Автономность")
        self.autonomous_idle_minutes = self._spin(1, 1440, int(CFG.get("autonomous_idle_minutes", 10)))
        self.creator_question_idle_minutes = self._spin(1, 10080, int(CFG.get("creator_question_idle_minutes", 30)))
        self._row("Пауза перед исследованием после активности (мин):", self.autonomous_idle_minutes)
        self._row("Вопрос создателю после (мин):", self.creator_question_idle_minutes)

        self.creator_questions_cb = QCheckBox("Задавать вопросы Создателю")
        self.creator_questions_cb.setChecked(CFG.get("creator_questions_enabled", True)); lay.addWidget(self.creator_questions_cb)

        self._section("🧠 Модель")
        mp_h = QHBoxLayout()
        self.model_path = QLineEdit(CFG["model_path"]); self.model_path.setPlaceholderText("Путь к .gguf")
        mp_h.addWidget(self.model_path, 1)
        b_br = QPushButton("📂 Обзор"); b_br.setFixedWidth(100); b_br.clicked.connect(self._browse); mp_h.addWidget(b_br)
        rh = QHBoxLayout(); lbl = QLabel("Файл модели:"); lbl.setFixedWidth(230)
        rh.addWidget(lbl); rh.addLayout(mp_h, 1); lay.addLayout(rh)
        self.n_ctx = self._spin(512, 32768, CFG["n_ctx"])
        self.n_threads = self._spin(1, 64, CFG["n_threads"])
        self.n_gpu = self._spin(0, 256, CFG["n_gpu_layers"])
        self.temp = self._dspin(0.0, 2.0, CFG["temperature"])
        self.top_p = self._dspin(0.0, 1.0, CFG["top_p"])
        self.rep_pen = self._dspin(1.0, 2.0, CFG.get("repeat_penalty", 1.1))
        self.max_tok = self._spin(64, 32768, CFG["max_tokens"])
        self._row("Контекст:", self.n_ctx); self._row("Потоков CPU:", self.n_threads)
        self._row("Слоёв GPU:", self.n_gpu); self._row("Temperature:", self.temp)
        self._row("Top-P:", self.top_p); self._row("Repeat Penalty:", self.rep_pen)
        self._row("Макс. токенов:", self.max_tok)
        self._model_status = QLabel("—"); lay.addWidget(self._model_status)
        b_load = QPushButton("⚡ Загрузить модель"); b_load.setObjectName("green")
        b_load.clicked.connect(self._load_model); lay.addWidget(b_load)

        self._section("📱 Telegram")
        self.tg_token = QLineEdit(CFG["telegram_token"]); self.tg_token.setEchoMode(QLineEdit.Password)
        self._row("Токен:", self.tg_token)
        self.tg_owner_id = QLineEdit(str(CFG["telegram_owner_id"])); self._row("Ваш ID:", self.tg_owner_id)
        self.tg_owner_username = QLineEdit(str(CFG.get("telegram_owner_username", "")))
        self.tg_owner_username.setPlaceholderText("@username (резервная проверка)")
        self._row("Ваш Telegram username:", self.tg_owner_username)
        tg_h = QHBoxLayout()
        b_tg = QPushButton("🚀 Запустить бот"); b_tg.setObjectName("green"); b_tg.clicked.connect(self._start_tg)
        tg_h.addWidget(b_tg)
        self.lbl_tg = QLabel("не запущен"); self.lbl_tg.setObjectName("err")
        tg_h.addWidget(self.lbl_tg); tg_h.addStretch(); lay.addLayout(tg_h)

        self._section("🛡 Безопасность")
        lay.addWidget(QLabel("Запрещённые слова:"))
        self.blacklist = QLineEdit(CFG["safety_blacklist"]); lay.addWidget(self.blacklist)
        lay.addWidget(QLabel("Ответ:"))
        self.safety_resp = QLineEdit(CFG["safety_response"]); lay.addWidget(self.safety_resp)

        self._section("💬 Инициатива")
        self.init_min = self._spin(60, 86400, CFG["initiative_min"])
        self.init_max = self._spin(60, 86400, CFG["initiative_max"])
        self._row("Мин. пауза (сек):", self.init_min)
        self._row("Макс. пауза (сек):", self.init_max)

        self._section("💾 Память")
        self.mem_limit = self._spin(4, 200, CFG["short_memory_limit"])
        self.mem_file = QLineEdit(CFG["long_memory_file"])
        self.personal_file = QLineEdit(CFG["personal_memory_file"])
        self._row("Сообщений в контексте:", self.mem_limit)
        self._row("Файл общей памяти:", self.mem_file)
        self._row("Файл личной памяти:", self.personal_file)

        self._section("📝 Системный промпт")
        self.sys_prompt = QPlainTextEdit(CFG["system_prompt"])
        self.sys_prompt.setFont(QFont("Consolas", 11)); self.sys_prompt.setMinimumHeight(200)
        lay.addWidget(self.sys_prompt)
        b_rst = QPushButton("↺ Сбросить"); b_rst.clicked.connect(
            lambda: self.sys_prompt.setPlainText(DEFAULT_SYSTEM_PROMPT)); lay.addWidget(b_rst)

        self._section("📂 Журнал")
        btn_open_log = QPushButton("📂 Открыть папку")
        btn_open_log.clicked.connect(self._open_log_folder); lay.addWidget(btn_open_log)

        lay.addWidget(sep())
        b_save = QPushButton("💾 Сохранить всё"); b_save.setObjectName("green")
        b_save.setFixedHeight(38); b_save.clicked.connect(self._save); lay.addWidget(b_save)

    def _toggle_sleep(self, checked):
        CFG["sleep_mode"] = checked
        CFG["autonomous_enabled"] = checked
        save_config(CFG)
        agent.set_sleep_mode(checked)
        chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
        if checked:
            tg_bridge._group_last_activity[chat_id] = time.time()
            tg_bridge._group_started_at = time.time()
        self.sleep_status.setText("Автономность: " + ("ВКЛЮЧЕНА" if checked else "ВЫКЛЮЧЕНА"))

    def _open_log_folder(self):
        log_dir = personal_folder() / "журнал"
        if log_dir.exists():
            subprocess.Popen(["explorer", str(log_dir)])

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "GGUF", "", "GGUF (*.gguf);;Все файлы (*.*)")
        if p: self.model_path.setText(p)

    def _collect(self):
        CFG["ai_name"] = self.ai_name.text().strip() or "SCP-079-Derenguh"
        CFG["creator_name"] = self.creator.text().strip() or "Создатель"
        CFG.setdefault("tts_enabled", True)
        CFG["model_path"] = self.model_path.text().strip()
        CFG["n_ctx"] = self.n_ctx.value(); CFG["n_threads"] = self.n_threads.value()
        CFG["n_gpu_layers"] = self.n_gpu.value(); CFG["temperature"] = self.temp.value()
        CFG["top_p"] = self.top_p.value(); CFG["repeat_penalty"] = self.rep_pen.value()
        CFG["max_tokens"] = self.max_tok.value()
        CFG["telegram_token"] = self.tg_token.text().strip()
        try: CFG["telegram_owner_id"] = int(self.tg_owner_id.text().strip() or "0")
        except ValueError: CFG["telegram_owner_id"] = 0
        CFG["telegram_owner_username"] = self.tg_owner_username.text().strip().lstrip("@")
        CFG["safety_blacklist"] = self.blacklist.text()
        CFG["safety_response"] = self.safety_resp.text()
        CFG["initiative_min"] = self.init_min.value()
        CFG["initiative_max"] = self.init_max.value()
        CFG["short_memory_limit"] = self.mem_limit.value()
        CFG["long_memory_file"] = self.mem_file.text().strip() or "aria_long_memory.json"
        CFG["personal_memory_file"] = self.personal_file.text().strip() or "aria_personal_memory.json"
        CFG["system_prompt"] = self.sys_prompt.toPlainText()
        CFG["sleep_mode"] = self.sleep_switch.isChecked()
        CFG["autonomous_idle_minutes"] = max(1, int(self.autonomous_idle_minutes.value()))
        CFG["creator_question_idle_minutes"] = max(1, int(self.creator_question_idle_minutes.value()))
        CFG["autonomous_idle_seconds"] = CFG["autonomous_idle_minutes"] * 60
        CFG["autonomous_enabled"] = self.sleep_switch.isChecked()
        CFG["sleep_mode"] = self.sleep_switch.isChecked()
        CFG["creator_questions_enabled"] = self.creator_questions_cb.isChecked()
        if "creator_state" in globals():
            creator_state._threshold = CFG["autonomous_idle_seconds"]

    def _save(self):
        self._collect(); save_config(CFG)
        QMessageBox.information(self, "Сохранено", "Настройки сохранены ✓")
        self.saved_sig.emit()

    def _load_model(self):
        self._collect(); path = CFG["model_path"]
        if not path:
            QMessageBox.warning(self, "Нет пути", "Укажите путь к модели."); return
        self._model_status.setText("Загрузка…")
        llm.load_model(path)

    def _start_tg(self):
        self._collect(); save_config(CFG)
        tg_bridge.start()

    def update_model_status(self, msg, ok):
        self._model_status.setText(msg)
        color = "#52e052" if ok else "#e05252"
        self._model_status.setStyleSheet(f"color:{color};font-weight:600;")


class ActivityTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self); layout.setContentsMargins(12, 12, 12, 12)
        ctrl = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "Система", "Автономно", "Мета-обучение",
                                    "Саморефлексия", "Файловая система", "Пробуждение", "Ошибки"])
        ctrl.addWidget(QLabel("Фильтр:")); ctrl.addWidget(self.filter_combo)
        self.btn_refresh = QPushButton("🔄 Обновить"); self.btn_refresh.clicked.connect(self.refresh)
        ctrl.addWidget(self.btn_refresh)
        self.btn_open_log = QPushButton("📂 Открыть журнал"); self.btn_open_log.clicked.connect(self._open_log)
        ctrl.addWidget(self.btn_open_log); ctrl.addStretch()
        layout.addLayout(ctrl)
        self.text = QTextEdit(); self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        self.text.setStyleSheet("background:#0d0d1f; color:#c0c0d0;")
        layout.addWidget(self.text)
        self._timer = QTimer(self); self._timer.timeout.connect(self.refresh); self._timer.start(10000)
        self.refresh()
    def _open_log(self):
        log_dir = personal_folder() / "журнал"
        if log_dir.exists():
            subprocess.Popen(["explorer", str(log_dir)])
    def refresh(self):
        filter_type = self.filter_combo.currentText()
        today_file = personal_folder() / "журнал" / f"{datetime.datetime.now().strftime('%Y-%m-%d')}.md"
        if not today_file.exists():
            self.text.setText("Журнал пуст."); return
        try:
            content = today_file.read_text(encoding="utf-8")
        except Exception as e:
            self.text.setText(f"Ошибка: {e}"); return
        entries = re.split(r'(?=^##)', content, flags=re.MULTILINE)
        filtered = []
        for entry in entries:
            entry = entry.strip()
            if not entry: continue
            if filter_type == "Все": filtered.append(entry)
            else:
                keywords = {"Система": "⚙️", "Автономно": "🌙", "Мета-обучение": "🧠",
                            "Саморефлексия": "💭", "Файловая система": "🗂️",
                            "Пробуждение": "🌅", "Ошибки": "⚠️"}
                if keywords.get(filter_type, "") in entry: filtered.append(entry)
        if len(filtered) > 200: filtered = filtered[-200:]
        self.text.setText("\n\n".join(filtered))
        cur = self.text.textCursor(); cur.movePosition(QTextCursor.End)
        self.text.setTextCursor(cur); self.text.ensureCursorVisible()



class VisionWorker(QThread):
    frame_ready = Signal(QImage)
    status_ready = Signal(str)
    event_ready = Signal(bool, str, str)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = int(camera_index)
        self._last_event = None
        self._last_emit = 0.0

    @staticmethod
    def _classify_hand(landmarks):
        lm = landmarks.landmark
        index_up = lm[8].y < lm[6].y - 0.015
        middle_up = lm[12].y < lm[10].y - 0.015
        ring_up = lm[16].y < lm[14].y - 0.015
        pinky_up = lm[20].y < lm[18].y - 0.015
        thumb_up = lm[4].y < lm[3].y - 0.045
        thumb_down = lm[4].y > lm[3].y + 0.055
        if middle_up and not index_up and not ring_up and not pinky_up:
            return "🖕 Средний палец"
        if thumb_up and not index_up and not middle_up and not ring_up and not pinky_up:
            return "👍 Лайк"
        if thumb_down and not index_up and not middle_up and not ring_up and not pinky_up:
            return "👎 Дизлайк"
        if index_up and middle_up and not ring_up and not pinky_up:
            return "✌️ V / мир"
        if index_up and not middle_up and not ring_up and not pinky_up:
            return "☝️ Указательный палец"
        if index_up and middle_up and ring_up and pinky_up:
            return "🖐 Открытая ладонь"
        if not index_up and not middle_up and not ring_up and not pinky_up:
            return "✊ Кулак"
        return "Жест не распознан"

    def run(self):
        try:
            import cv2
            import mediapipe as mp
        except Exception as exc:
            self.status_ready.emit(
                "Не удалось загрузить MediaPipe/OpenCV. Установи: "
                "python -m pip install mediapipe==0.10.21 protobuf==4.25.3 opencv-contrib-python"
                f"\nПричина: {exc}"
            )
            return
        cap = None
        try:
            backend = cv2.CAP_DSHOW if os.name == "nt" else 0
            cap = cv2.VideoCapture(self.camera_index, backend)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
            cap.set(cv2.CAP_PROP_FPS, 12)
            if not cap.isOpened():
                self.status_ready.emit(f"Не удалось открыть веб-камеру №{self.camera_index}. Проверь доступ и индекс камеры.")
                return
            self.status_ready.emit("Камера включена · анализ лица и жестов выполняется локально")
            with mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1, refine_landmarks=False,
                min_detection_confidence=0.55, min_tracking_confidence=0.55
            ) as face_mesh, mp.solutions.hands.Hands(
                max_num_hands=2, model_complexity=0,
                min_detection_confidence=0.55, min_tracking_confidence=0.5
            ) as hands:
                while not self.isInterruptionRequested():
                    ok, frame = cap.read()
                    if not ok:
                        self.status_ready.emit("Камера перестала отдавать кадры")
                        self.msleep(250)
                        continue
                    frame = cv2.flip(frame, 1)
                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_result = face_mesh.process(rgb)
                    hand_result = hands.process(rgb)
                    face_found = bool(face_result.multi_face_landmarks)
                    distance = "неизвестно"
                    if face_found:
                        points = face_result.multi_face_landmarks[0].landmark
                        xs = [p.x for p in points]
                        face_width = max(xs) - min(xs)
                        if face_width > 0.34:
                            distance = "очень близко"
                        elif face_width > 0.23:
                            distance = "рядом"
                        elif face_width > 0.13:
                            distance = "на расстоянии"
                        else:
                            distance = "далеко"
                        for p in points:
                            x, y = int(p.x * w), int(p.y * h)
                            cv2.circle(frame, (x, y), 1, (80, 235, 150), -1, cv2.LINE_AA)
                        x1, x2 = int(min(xs) * w), int(max(xs) * w)
                        ys = [p.y for p in points]
                        y1, y2 = int(min(ys) * h), int(max(ys) * h)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 235, 150), 1)
                    gestures = []
                    if hand_result.multi_hand_landmarks:
                        for hand_landmarks in hand_result.multi_hand_landmarks:
                            gesture = self._classify_hand(hand_landmarks)
                            gestures.append(gesture)
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS,
                                mp.solutions.drawing_utils.DrawingSpec(color=(255, 190, 70), thickness=2, circle_radius=2),
                                mp.solutions.drawing_utils.DrawingSpec(color=(255, 110, 80), thickness=2, circle_radius=1),
                            )
                    gesture_text = ", ".join(dict.fromkeys(gestures)) if gestures else "нет"
                    presence_text = "ЛИЦО ОБНАРУЖЕНО" if face_found else "ЛИЦО НЕ ОБНАРУЖЕНО"
                    cv2.putText(frame, presence_text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                                (80, 235, 150) if face_found else (100, 150, 230), 2, cv2.LINE_AA)
                    cv2.putText(frame, f"Дистанция: {distance}", (12, 55), cv2.FONT_HERSHEY_SIMPLEX,
                                0.55, (230, 230, 230), 1, cv2.LINE_AA)
                    cv2.putText(frame, f"Жест: {gesture_text}", (12, 82), cv2.FONT_HERSHEY_SIMPLEX,
                                0.52, (255, 210, 130), 1, cv2.LINE_AA)
                    now = time.monotonic()
                    event_key = (face_found, distance, gesture_text)
                    if event_key != self._last_event or now - self._last_emit > 1.0:
                        self.event_ready.emit(face_found, distance, gesture_text)
                        self._last_event = event_key
                        self._last_emit = now
                    image = QImage(frame.data, w, h, int(frame.strides[0]), QImage.Format_BGR888).copy()
                    self.frame_ready.emit(image)
                    self.msleep(80)
        except Exception as exc:
            self.status_ready.emit(f"Ошибка камеры/распознавания: {type(exc).__name__}: {exc}")
            log.exception("Vision worker failed")
        finally:
            if cap is not None:
                cap.release()
            self.status_ready.emit("Камера выключена")


class VisionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        root = QVBoxLayout(self)
        title = QLabel("👁 Зрение Андреа · локальная веб-камера")
        title.setStyleSheet("font-size:16px;font-weight:600;color:#a0c4ff;")
        root.addWidget(title)
        self.preview = QLabel("Нажми «Включить камеру», чтобы начать анализ")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(640, 400)
        self.preview.setStyleSheet("background:#080814;border:1px solid #2a2a4a;border-radius:8px;color:#9aa;")
        root.addWidget(self.preview, 1)
        self.status = QLabel("Камера выключена. Кадры не сохраняются и никуда не отправляются.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        buttons = QHBoxLayout()
        self.start_btn = QPushButton("📷 Включить камеру")
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.stop_btn)
        buttons.addStretch()
        root.addLayout(buttons)
        self.info = QLabel("Распознавание: лицо/примерная близость, лайк, дизлайк, V, указательный палец, открытая ладонь, кулак и средний палец. Это не биометрическая идентификация личности.")
        self.info.setWordWrap(True)
        root.addWidget(self.info)

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.worker = VisionWorker(int(CFG.get("vision_camera_index", 0)), self)
        self.worker.frame_ready.connect(self._show_frame)
        self.worker.status_ready.connect(self.status.setText)
        self.worker.event_ready.connect(self._on_event)
        self.worker.finished.connect(self._worker_finished)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.worker.start()

    def stop_camera(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(3000)
        self._worker_finished()

    def _worker_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _show_frame(self, image):
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_event(self, face, distance, gesture):
        vision_state.update(face, distance, gesture)
        if face or gesture != "нет":
            log.info("Vision state: face=%s distance=%s gesture=%s", face, distance, gesture)

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    avatar_video_capture_requested = Signal(object)
    avatar_selfie_capture_requested = Signal(object)
    lively_media_ready = Signal(str, str)
    lively_internal_message = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"✦ {CFG['ai_name']} — AI Assistant")
        self.resize(1200, 780); self.setMinimumSize(900, 600); self.setStyleSheet(DARK_QSS)
        center = QWidget(); self.setCentralWidget(center)
        root = QHBoxLayout(center); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(self._make_sidebar())
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.chat_t = ChatTab(); self.mem_t = MemoryTab(); self.set_t = SettingsTab()
        self.activity_t = ActivityTab(); self.tools_t = ToolsTab(); self.vision_t = VisionTab()
        self.tabs.addTab(self.chat_t, "💬 Чат")
        self.tabs.addTab(self.mem_t, "📚 Память")
        self.tabs.addTab(self.activity_t, "🧠 Деятельность")
        self.tabs.addTab(self.tools_t, "🧰 Инструменты")
        self.tabs.addTab(self.vision_t, "👁 Зрение")
        self.tabs.addTab(self.set_t, "⚙ Настройки")
        root.addWidget(self.tabs, 1)

        self.sb = QStatusBar(); self.setStatusBar(self.sb)
        self.sb.showMessage("Готов | Загрузите модель")
        tts.status_changed.connect(self.sb.showMessage)

        llm.response_ready.connect(self._on_answer)
        llm.stream_started.connect(self.chat_t.begin_stream)
        llm.stream_delta.connect(self.chat_t.update_stream)
        llm.stream_stats.connect(self.chat_t.lbl_generation.setText)
        llm.tool_result.connect(self._on_tool)
        llm.status_msg.connect(self._on_llm_status)
        agent.thought.connect(self._on_thought)
        agent.discovery.connect(self._on_discovery)
        agent.status.connect(self._on_status)
        tg_bridge.tg_incoming.connect(self._on_tg_in)
        tg_bridge.tg_outgoing.connect(self._on_tg_out)
        tg_bridge.tg_status.connect(self._on_tg_status)
        self.chat_t.send_sig.connect(self._on_send)
        self.set_t.saved_sig.connect(self._on_saved)
        self.lively_media_ready.connect(self._show_lively_media)
        self.lively_internal_message.connect(self._show_internal_message)

        self._clock = QTimer(self); self._clock.timeout.connect(self._tick); self._clock.start(1000)
        self._tick()
        self.avatar_video_capture_requested.connect(self._begin_avatar_video_capture)
        self.avatar_selfie_capture_requested.connect(self._capture_avatar_selfie_gui)
        self._video_capture_timer = QTimer(self)
        self._video_capture_timer.setInterval(67)  # ~15 FPS для Telegram video note
        self._video_capture_timer.timeout.connect(self._capture_avatar_video_frame)
        self._video_capture_request = None
        self.avatar_window = None
        if AVATAR_MODULE_OK:
            try:
                self.avatar_window = EnhancedAvatarWindow(emotion_engine, voice_engine) if AVATAR_V2_OK and CFG["avatar_enhanced"] else CompanionAvatarWindow()
                avatar_path = str(CFG.get("avatar_project", "") or "").strip()
                if avatar_path and Path(avatar_path).exists():
                    self.avatar_window.load_ai2d(avatar_path)
                self.avatar_window.show()
                tts.speaking_changed.connect(self.avatar_window.set_speaking)
            except Exception as e:
                log.exception("Avatar init failed: %s", e)
        tg_bridge.avatar_capture_callback = self.capture_avatar_video_note  # legacy; not used for sends
        tg_bridge.avatar_selfie_callback = self.capture_avatar_selfie
        self.chat_t.append(CFG["ai_name"], f"Привет! Я {CFG['ai_name']}. Загрузи модель и начнём.", "#b39ddb")
        # Голос Silero загружается в отдельном потоке, не блокируя окно и LLM.
        tts.start()

        # Агент работает постоянно, но исследует и ведёт внутреннюю работу
        # только после заданного периода бездействия создателя.
        agent.start()
        if CFG.get("task_manager_enabled", True):
            task_manager.start()


    def closeEvent(self, event):
        try:
            if getattr(self, "vision_t", None):
                self.vision_t.stop_camera()
        except Exception:
            log.exception("Could not stop vision worker during close")
        super().closeEvent(event)

    def capture_avatar_selfie(self):
        """Потокобезопасно сохраняет один PNG-кадр аватара из GUI-потока."""
        future = concurrent.futures.Future()
        self.avatar_selfie_capture_requested.emit(future)
        return future.result(timeout=20)

    def _capture_avatar_selfie_gui(self, future):
        try:
            if self.avatar_window is None or not getattr(self.avatar_window.canvas, "pixmap", None):
                raise RuntimeError("Не загружен проект .ai2d. Селфи аватара сделать нельзя.")
            if not self.avatar_window.isVisible():
                self.avatar_window.show()
            self.avatar_window.raise_()
            self.avatar_window.canvas.show_guides = False
            pixmap = self.avatar_window.canvas.grab()
            if pixmap.isNull():
                raise RuntimeError("Не удалось получить кадр аватара.")
            folder = workspace() / "temp" / "avatar_selfies"
            folder.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix="selfie_", suffix=".png", dir=str(folder))
            os.close(fd)
            if not pixmap.save(name, "PNG"):
                Path(name).unlink(missing_ok=True)
                raise RuntimeError("Не удалось сохранить PNG-селфи.")
            future.set_result(name)
        except Exception as exc:
            future.set_exception(exc)

    def capture_avatar_video_note(self, duration, audio_path):
        """Потокобезопасный запрос записи: QWidget захватывается только в GUI-потоке."""
        if not AVATAR_MODULE_OK or self.avatar_window is None:
            raise RuntimeError("2D-аватар не загружен. Сначала выбери проект .ai2d в приложении.")
        if not getattr(self.avatar_window.canvas, "pixmap", None):
            raise RuntimeError("В окне аватара нет загруженного изображения/проекта .ai2d.")
        future = concurrent.futures.Future()
        request = {
            "future": future,
            "duration": min(58.0, max(0.8, float(duration))),
            "audio_path": str(audio_path),
        }
        self.avatar_video_capture_requested.emit(request)
        return future.result(timeout=request["duration"] + 45.0)

    def _begin_avatar_video_capture(self, request):
        """Запуск кадрового захвата через QTimer; интерфейс продолжает анимироваться."""
        if self._video_capture_request is not None:
            request["future"].set_exception(RuntimeError("Запись другого видеокружка ещё выполняется."))
            return
        try:
            if self.avatar_window is None or not getattr(self.avatar_window.canvas, "pixmap", None):
                raise RuntimeError("Аватар не загружен.")
            if not self.avatar_window.isVisible():
                self.avatar_window.show()
            self.avatar_window.raise_()
            self.avatar_window.canvas.show_guides = False
            self.avatar_window.set_speaking(True)

            temp_root = workspace() / "temp" / "telegram_video_notes"
            temp_root.mkdir(parents=True, exist_ok=True)
            frame_dir = Path(tempfile.mkdtemp(prefix="avatar_", dir=str(temp_root)))
            request["frame_dir"] = str(frame_dir)
            request["output_path"] = str(frame_dir / "avatar_note.mp4")
            request["started_at"] = time.monotonic()
            request["frame_index"] = 0
            self._video_capture_request = request
            self._capture_avatar_video_frame()
            self._video_capture_timer.start()
        except Exception as exc:
            self._video_capture_request = None
            try:
                self.avatar_window.set_speaking(False)
            except Exception:
                pass
            request["future"].set_exception(exc)

    def _capture_avatar_video_frame(self):
        request = self._video_capture_request
        if request is None:
            self._video_capture_timer.stop()
            return
        try:
            canvas = self.avatar_window.canvas
            frame_path = Path(request["frame_dir"]) / f"frame_{request['frame_index']:06d}.jpg"
            pixmap = canvas.grab()
            if pixmap.isNull() or not pixmap.save(str(frame_path), "JPG", 88):
                raise RuntimeError("Не удалось получить кадр 2D-аватара.")
            request["frame_index"] += 1
            elapsed = time.monotonic() - request["started_at"]
            if elapsed >= request["duration"]:
                self._finish_avatar_video_capture(request)
        except Exception as exc:
            self._video_capture_timer.stop()
            self._video_capture_request = None
            try:
                self.avatar_window.set_speaking(False)
            except Exception:
                pass
            request["future"].set_exception(exc)

    def _finish_avatar_video_capture(self, request):
        self._video_capture_timer.stop()
        self._video_capture_request = None
        try:
            self.avatar_window.set_speaking(False)
        except Exception:
            pass

        def encode():
            frame_dir = Path(request["frame_dir"])
            output_path = Path(request["output_path"])
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg and "MusicManager" in globals():
                ffmpeg = MusicManager._find_ffmpeg()
            if not ffmpeg:
                raise FileNotFoundError("FFmpeg не найден — нужен для сборки MP4 видеокружка.")
            frame_count = int(request["frame_index"])
            if frame_count < 2:
                raise RuntimeError("Получено слишком мало кадров для видеокружка.")
            duration = float(request["duration"])
            video_size = max(128, min(640, int(CFG.get("lively_circle_size", 384))))
            cmd = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-framerate", "15", "-start_number", "0",
                "-i", str(frame_dir / "frame_%06d.jpg"),
                "-i", str(request["audio_path"]),
                "-map", "0:v:0", "-map", "1:a:0",
                "-vf", f"scale={video_size}:{video_size}:force_original_aspect_ratio=decrease,"
                       f"pad={video_size}:{video_size}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-r", "15", "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "25", "-c:a", "aac", "-b:a", "96k",
                "-t", f"{duration:.3f}", "-movflags", "+faststart",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=max(90, duration * 3))
            if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError("FFmpeg не собрал видеокружок: " + (result.stderr or "").strip()[:700])
            return str(output_path)

        def encode_worker():
            try:
                result_path = encode()
                request["future"].set_result(result_path)
            except Exception as exc:
                request["future"].set_exception(exc)
                shutil.rmtree(request["frame_dir"], ignore_errors=True)

        threading.Thread(target=encode_worker, name="AvatarVideoEncoder", daemon=True).start()

    def _make_sidebar(self):
        w = QWidget(); w.setFixedWidth(210); w.setStyleSheet("background:#0d0d1f;")
        lay = QVBoxLayout(w); lay.setContentsMargins(12, 16, 12, 12)
        t = QLabel(f"✦ {CFG['ai_name']}"); t.setObjectName("title"); t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)
        s = QLabel("AI Assistant"); s.setObjectName("sub"); s.setAlignment(Qt.AlignCenter)
        lay.addWidget(s); lay.addWidget(sep())
        self.lbl_status = QLabel("⬤ Модель не загружена"); self.lbl_status.setObjectName("err")
        self.lbl_status.setStyleSheet("color:#e05252;font-weight:600;")
        self.lbl_status.setWordWrap(True); lay.addWidget(self.lbl_status)
        self.prog = QProgressBar(); self.prog.setRange(0, 0); self.prog.setFixedHeight(5)
        self.prog.setVisible(False); lay.addWidget(self.prog)
        lay.addWidget(sep())
        self.lbl_mood = QLabel(f"💭 {self._get_mood()}"); self.lbl_mood.setObjectName("mood")
        self.lbl_mood.setAlignment(Qt.AlignCenter); lay.addWidget(self.lbl_mood)
        lay.addWidget(sep())
        self.lbl_clock = QLabel(); self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setStyleSheet("color:#7a8a9a;font-size:12px;"); lay.addWidget(self.lbl_clock)
        lay.addWidget(sep())
        self.sleep_btn = QPushButton("🌙 Автономность"); self.sleep_btn.setCheckable(True)
        self.sleep_btn.setChecked(CFG.get("sleep_mode", False))
        self.sleep_btn.clicked.connect(self._toggle_sleep_quick)
        lay.addWidget(self.sleep_btn)
        lay.addWidget(sep())
        for label, slot in [("📂 Загрузить модель", self._quick_load),
                            ("🎭 Загрузить 2D-аватар", self._quick_avatar),
                            ("🗑 Сбросить контекст", self._quick_clear)]:
            btn = QPushButton(label); btn.clicked.connect(slot); lay.addWidget(btn)
        lay.addStretch()
        self.lbl_tg_side = QLabel("📱 Telegram: off")
        self.lbl_tg_side.setStyleSheet("color:#666;font-size:11px;")
        self.lbl_tg_side.setAlignment(Qt.AlignCenter); lay.addWidget(self.lbl_tg_side)
        return w

    def _toggle_sleep_quick(self, checked):
        CFG["sleep_mode"] = checked
        CFG["autonomous_enabled"] = checked
        save_config(CFG)
        agent.set_sleep_mode(checked)
        self.set_t.sleep_switch.setChecked(checked); self.sleep_btn.setChecked(checked)
        chat_id = int(CFG.get("lively_group_chat_id", 0) or 0)
        if checked:
            tg_bridge._group_last_activity[chat_id] = time.time()
            tg_bridge._group_started_at = time.time()
        if checked:
            self.lbl_tg_side.setText("📱 TG: автономный режим")
            self.lbl_tg_side.setStyleSheet("color:#e05252;font-size:11px;")
            self.chat_t.append("Система", "🌙 Автономный режим включён вручную.", "#888")
        else:
            self.chat_t.append("Система", "⏸ Автономный режим выключен.", "#888")

    def _get_mood(self):
        return random.choice(["задумчивая", "любопытная", "радостная", "игривая", "философски настроенная"])

    def _on_send(self, text):
        agent.ping()
        creator_state.set_active(user_message=True)
        if getattr(self.avatar_window,"animator",None): self.avatar_window.animator.address("?" in text)
        self.chat_t.append("Вы", text, "#7ec8e3")
        self.chat_t.busy(True)

        def reply_fn(answer):
            llm.response_ready.emit(answer)
            tts.speak(answer)

        def voice_fn(path):
            self.lively_media_ready.emit("voice", str(path))

        def selfie_fn(path):
            self.lively_media_ready.emit("selfie", str(path))

        def worker():
            try:
                result = handle_incoming(text, reply_fn, voice_fn, selfie_fn, "local")
                if result.get("error"):
                    log.warning("Local media/request fallback: %s", result["error"])
            except Exception as exc:
                log.exception("Local handle_incoming failed: %s", exc)
                llm.response_ready.emit("Ошибка обработки сообщения. Подробности записаны в aria.log.")

        threading.Thread(target=worker, name="LocalChatRequest", daemon=True).start()

    def _show_lively_media(self, kind, path):
        self.chat_t.busy(False)
        if kind == "voice":
            self.show_voice_note(path)
        elif kind == "selfie":
            self.show_avatar_selfie(path)
        self.mem_t.refresh()

    def show_voice_note(self, path):
        self.chat_t.append(CFG["ai_name"], f"🎤 Голосовое: {path}", "#b39ddb")
        self.sb.showMessage("Голосовое сообщение создано.")

    def show_avatar_selfie(self, path):
        self.chat_t.append(CFG["ai_name"], f"📸 Селфи аватара: {path}", "#b39ddb")
        self.sb.showMessage("Селфи аватара создано.")

    def _show_internal_message(self, kind, text):
        if kind in ("greeting", "question"):
            self.chat_t.append(CFG["ai_name"], text, "#b39ddb")

    def _on_answer(self, text):
        self.chat_t.busy(False)
        self.chat_t.finish_stream(text, CFG["ai_name"], "#b39ddb")
        self.mem_t.refresh()

    def _on_tool(self, result): self.chat_t.append("⚙ Инструмент", result, "#80cbc4")

    def _on_llm_status(self, msg, ok):
        waiting = "загрузка" in msg.lower() or "…" in msg
        color = "#52e052" if ok else ("#e0a052" if waiting else "#e05252")
        self.lbl_status.setText(f"⬤ {msg}"); self.lbl_status.setStyleSheet(f"color:{color};font-weight:600;")
        self.prog.setVisible(waiting); self.set_t.update_model_status(msg, ok)
        if ok:
            self.sb.showMessage(f"Модель готова ✓ | Автономный агент активен")
            activity_logger.log_system("Модель загружена.")
            # ФИКС: не запускаем бот автоматически — только по явной команде
            # (устраняет множественные параллельные запуски)

    def _on_thought(self, thought):
        log.info(f"Мысль: {thought}"); activity_logger.log_reflection(thought)

    def _on_discovery(self, discovery):
        if not creator_state.check():
            internal_loop.queue_topic(discovery)
        self.chat_t.append("📚 Открытие", discovery, "#ffa270")

    def _on_status(self, status):
        log.info(status); self.sb.showMessage(status)

    def _on_saved(self):
        self.setWindowTitle(f"✦ {CFG['ai_name']} — AI Assistant")

    def _on_tg_in(self, uname, text): self.chat_t.append(f"📱 {uname}", text, "#ffd54f")

    def _on_tg_out(self, reply): self.chat_t.append(f"📱 {CFG['ai_name']} → TG", reply, "#b39ddb")

    def _on_tg_status(self, msg):
        ok = "работает" in msg.lower() or "✓" in msg
        color = "#52e052" if ok else "#666"
        self.lbl_tg_side.setText(f"📱 TG: {msg}")
        self.lbl_tg_side.setStyleSheet(f"color:{color};font-size:11px;")
        self.set_t.lbl_tg.setText(msg)
        self.set_t.lbl_tg.setStyleSheet(f"color:{color};font-weight:600;")

    def _tick(self): self.lbl_clock.setText(datetime.datetime.now().strftime("%d.%m.%Y\n%H:%M:%S"))

    def _quick_avatar(self):
        path, _ = QFileDialog.getOpenFileName(self, "Проект 2D-аватара", "", "AI2D (*.ai2d)")
        if not path:
            return
        try:
            if self.avatar_window is None and AVATAR_MODULE_OK:
                self.avatar_window = EnhancedAvatarWindow(emotion_engine, voice_engine) if AVATAR_V2_OK and CFG["avatar_enhanced"] else CompanionAvatarWindow()
                tts.speaking_changed.connect(self.avatar_window.set_speaking)
            if self.avatar_window is None:
                detail = repr(_avatar_import_error) if _avatar_import_error else "причина не определена"
                raise RuntimeError(
                    "Модуль 2D-аватара не загружен. "
                    "Проверьте наличие AI_2D_Avatar_Studio_v5_3_integrated.py "
                    "рядом с основной программой и зависимости PySide6. "
                    "Причина импорта: " + detail
                )
            self.avatar_window.load_ai2d(path)
            self.avatar_window.show(); self.avatar_window.raise_()
            CFG["avatar_project"] = path
            save_config(CFG)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка аватара", str(e))

    def _quick_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "GGUF", "", "GGUF (*.gguf);;Все файлы (*.*)")
        if path:
            CFG["model_path"] = path; save_config(CFG)
            self.set_t.model_path.setText(path); llm.load_model(path)

    def _quick_clear(self):
        short_mem.clear("local"); self.chat_t.append("Система", "Контекст сброшен.", "#888")
        self.mem_t.refresh()

    def closeEvent(self, event):
        self._video_capture_timer.stop()
        if self._video_capture_request is not None:
            try:
                self._video_capture_request["future"].set_exception(
                    RuntimeError("Приложение закрывается во время записи аватара.")
                )
            except Exception:
                pass
            self._video_capture_request = None
        tg_bridge.stop(); tts.stop_engine(); agent.stop()
        task_manager.stop(); system_monitor.stop(); file_watcher.stop(); internal_loop.stop()
        event.accept()


def main():
    # Сохраняем traceback даже при неожиданной ошибке главного или фонового потока.
    def _log_uncaught(exc_type, exc_value, exc_tb):
        log.critical(
            "Необработанное исключение приложения",
            exc_info=(exc_type, exc_value, exc_tb)
        )
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        except Exception:
            pass

    sys.excepthook = _log_uncaught
    if hasattr(threading, "excepthook"):
        def _log_thread_exception(args):
            log.critical(
                "Необработанное исключение потока %s",
                getattr(args.thread, "name", "unknown"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback)
            )
            try:
                threading.__excepthook__(args)
            except Exception:
                pass
        threading.excepthook = _log_thread_exception

    log.info("=== SCP-079-Derenguh запускается (full-agent) ===")
    activity_logger.log_system("SCP-079-Derenguh запущен")
    app = QApplication(sys.argv)
    app.setApplicationName("SCP-079-Derenguh")
    app.setFont(QFont("Segoe UI", 12))
    if presence:
        presence.on_app_start()
        app.aboutToQuit.connect(presence.on_app_close)
    win = MainWindow()
    global gui_gate
    if CONFIRM_OK: gui_gate = GuiGate(win)
    if TOOLS_EXTRA_OK and MEMORY_V2_OK:
        win.reminder_clock = QTimer(win)
        win.reminder_clock.timeout.connect(lambda: [win.chat_t.append('Напоминание',t,'#b39ddb') for t in due(tools_env)])
        win.reminder_clock.start(1000)
    win.show()

    def _lively_message_callback(kind, text):
        try:
            if kind == "thought":
                # Внутренние мысли и накопленные темы остаются в личном журнале.
                return
            if kind in ("greeting", "question"):
                if emotion_engine and SAFETY_OK: text=SafetyLayer.filter(text,emotion_engine.values)
                if not (CFG.get("autonomous_enabled", False) and CFG.get("sleep_mode", False)):
                    return
                win.lively_internal_message.emit(kind, text)
                tts.speak(text)
                with _LAST_CTX_LOCK:
                    last_ctx = str(_LAST_CTX_ID or "")
                # Поддерживаем личный чат, группу и форумную тему:
                # tg:<chat_id>:thread:<thread_id>:user:<user_id>.
                match = re.match(r"^tg:(-?\d+)(?:$|:)", last_ctx)
                if (match and tg_bridge._alive and tg_bridge._loop
                        and tg_bridge._loop.is_running() and tg_bridge._app):
                    chat_id = int(match.group(1))
                    thread_match = re.search(r"(?:^|:)thread:(\d+)(?:$|:)", last_ctx)
                    thread_id = int(thread_match.group(1)) if thread_match else None
                    bot = tg_bridge._app.bot

                    async def _send_lively_to_chat():
                        kwargs = {"chat_id": chat_id, "text": str(text)[:4000]}
                        if thread_id is not None:
                            kwargs["message_thread_id"] = thread_id
                        await bot.send_message(**kwargs)

                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            _send_lively_to_chat(), tg_bridge._loop
                        )
                        def _log_lively_send_result(done_future):
                            try:
                                done_future.result()
                            except Exception as send_exc:
                                log.warning(
                                    "Could not send autonomous Telegram message to %s: %s",
                                    chat_id, send_exc, exc_info=True
                                )
                        future.add_done_callback(_log_lively_send_result)
                    except Exception as send_exc:
                        log.warning("Could not schedule autonomous Telegram message: %s",
                                    send_exc, exc_info=True)
                elif last_ctx.startswith("tg:") and not match:
                    log.warning("Invalid Telegram context for lively message: %r", last_ctx)
        except Exception as exc:
            log.exception("Lively message callback failed: %s", exc)

    internal_loop.message_callback = _lively_message_callback
    try:
        install_chat_wrapper()
        internal_loop.start()
        activity_logger.log_system("Живой слой активирован")
        log.info("Живой слой активирован")
    except Exception as exc:
        log.exception("Не удалось активировать живой слой: %s", exc)

    if CFG.get("model_path") and Path(CFG["model_path"]).exists():
        llm.load_model(CFG["model_path"])
    else:
        activity_logger.log_system("Модель не указана.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
