"""Acceleration adapter for the single v4 llama.cpp instance (caller owns PriorityRLock)."""

import hashlib
import json
import re
import time
from collections import OrderedDict
from pathlib import Path

from scp_context_manager import ContextManager
from scp_diagnostics import event

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
    def __init__(self, model, root, n_ctx, bus=None, settings=None):
        self.settings = dict(settings or {})
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
        seconds = 30 if kind=='thought' else 60 if priority>=20 else self.settings.get('user_timeout_seconds',0)
        self.deadline = time.monotonic()+seconds if seconds else float('inf')
        started=time.monotonic()
        event('llm','request',kind=kind,timeout_seconds=seconds,messages=len(messages))
        try:
            return self._generate(messages,priority,kind,max_tokens,temperature,top_p,on_chunk)
        except Exception as exc:
            timed_out=time.monotonic()>=self.deadline
            event('llm','failed',reason='timeout' if timed_out else type(exc).__name__,elapsed_s=round(time.monotonic()-started,2))
            self.model.reset()
            if timed_out: raise TimeoutError(f'Лимит генерации {seconds} с. Увеличьте его в настройках ускорения или установите 0.') from exc
            raise
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
        if not self.settings.get('adaptive_tokens',True): n=max_tokens
        prompt = self.context.prepare(
            messages,
            n,
            self.summarize if self.compact and self.settings.get("model_summaries",False) else None,
            lambda s: len(self.prefix.tokens(self.model, s)),
        )
        key = hashlib.sha256(repr((prompt, n, temperature, top_p)).encode()).digest()
        if self.settings.get("answer_cache",True) and key in self.cache:
            event("llm","cache_hit")
            self.cache.move_to_end(key)
            text = self.cache[key]
            self.perf.record(0, start, start, True)
            if self.bus:
                self.bus.emit("cache_hit")
            if on_chunk:
                on_chunk(text)
            return Answer(text, True)
        ids = self.prefix.tokens(self.model, prompt)
        event("llm","prefill_start",prompt_tokens=len(ids),max_tokens=n,n_ctx=self.n_ctx)
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
            stopping_criteria=StoppingCriteriaList([EarlyStop(self.model)] if self.settings.get("early_stop",True) else []),
        ):
            text = chunk["choices"][0]["text"]
            if not parts:
                first = time.monotonic()
                event("llm","first_chunk",elapsed_s=round(first-start,2))
            parts.append(text)
            if on_chunk:
                on_chunk(text)
        text = "".join(parts).strip()
        if time.monotonic() >= self.deadline:
            raise TimeoutError("Истекло время генерации")
        if self.settings.get("answer_cache",True) and text and not re.search(
            r"\[(?:TOOL|CMD|CREATEFILE|WEBSEARCH|REMIND|SPEAK):", text, re.I
        ):
            self.cache.put(key, text)
        self.perf.record(
            len(self.model.tokenize(text.encode(), add_bos=False)), start, first, False
        )
        event("llm","complete",elapsed_s=round(time.monotonic()-start,2),output_chars=len(text))
        return Answer(text)
