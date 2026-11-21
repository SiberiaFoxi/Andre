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
