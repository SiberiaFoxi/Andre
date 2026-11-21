"""Token-budgeted Gemma turns. WARM summaries are keyed by content on disk."""

from scp_diagnostics import measured

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

    @measured('context_manager')
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
