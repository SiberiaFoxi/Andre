from scp_emotion_engine import EmotionEngine
from scp_event_bus import EventBus


def test_events(tmp_path):
    bus = EventBus()
    e = EmotionEngine(tmp_path, bus)
    start = e.values.copy()
    bus.emit("tool_failure")
    assert (
        e.values["frustration"] > start["frustration"]
        and e.values["joy"] < start["joy"]
    )
    before = e.values.copy()
    e.apply_event("user_returned", after_days=3)
    assert (
        e.values["bittersweet"] > 0.5
        and e.values["resentment"] < before["resentment"]
        and e.values["joy"] > before["joy"]
    )
    e.cool(3600)
    assert e.baselines["joy"] < e.values["joy"] < 1
