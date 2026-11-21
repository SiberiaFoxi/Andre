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


def test_slow_cpu_prefill_and_timeout_recovery(tmp_path, monkeypatch):
    import pytest
    import scp_accelerator as module
    now = [0.0]
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setitem(sys.modules, 'llama_cpp', SimpleNamespace(StoppingCriteriaList=list))

    class Slow(FakeGGUF):
        resets = 0
        def __call__(self, ids, **kw):
            now[0] += 121
            if now[0] >= accel.deadline: raise RuntimeError('llama_decode returned 2')
            return iter([{'choices':[{'text':'Привет!'}]}])
        def reset(self): self.resets += 1

    model = Slow(); accel = Accelerator(model,tmp_path,3072,settings={'answer_cache':False})
    msgs = [{'role':'user','content':'Привет'}]
    assert accel.generate(msgs) == 'Привет!'
    accel.settings['user_timeout_seconds'] = 120
    with pytest.raises(TimeoutError,match='120'): accel.generate(msgs)
    assert model.resets == 1
    accel.settings['user_timeout_seconds'] = 0
    assert accel.generate(msgs) == 'Привет!'


def test_switches_reach_backend(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'llama_cpp', SimpleNamespace(StoppingCriteriaList=list))
    calls = []
    class Recorder(FakeGGUF):
        def __call__(self, ids, **kw):
            calls.append(kw)
            return iter([{'choices':[{'text':'Да.'}]}])
    accel = Accelerator(Recorder(),tmp_path,3072,settings={'adaptive_tokens':False,'early_stop':False,'answer_cache':False})
    for _ in range(2): assert not accel.generate([{'role':'user','content':'Привет'}],max_tokens=210).cached
    assert len(calls)==2
    assert all(c['max_tokens']==210 and not c['stopping_criteria'] for c in calls)
