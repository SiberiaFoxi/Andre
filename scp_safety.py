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
