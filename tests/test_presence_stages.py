from datetime import datetime

import pytest

from scp_autonomy import ProactiveScheduler
from scp_emotion_engine import EmotionEngine
from scp_event_bus import EventBus
from scp_presence import PresenceTracker
from scp_storage import save


@pytest.mark.parametrize(
    "hours,kind", [(5, "4h"), (10, "8h"), (24, "24h"), (48, "48h"), (72, "72h")]
)
def test_stages(tmp_path, hours, kind):
    now = datetime(2026, 1, 15, 12).timestamp()
    save(tmp_path / "presence.json", {"last_user_message_at": now - hours * 3600})
    bus = EventBus()
    emotions = EmotionEngine(tmp_path, bus)
    before = emotions.describe_for_prompt()
    p = PresenceTracker(tmp_path, bus, lambda: now)
    p.tick()
    scheduler = ProactiveScheduler(
        dict(
            proactive_enabled=True,
            proactive_quiet_hours="23:00-08:00",
            proactive_min_gap_minutes=240,
            proactive_daily_limit=4,
        ),
        p,
    )
    assert scheduler.maybe_send()[0] == kind
    assert scheduler.maybe_send() is None
    p.on_user_message()
    assert p.bucket() == "none" and emotions.describe_for_prompt() != before
