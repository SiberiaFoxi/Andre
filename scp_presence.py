"""Присутствие между сеансами."""

import time
from threading import RLock

from scp_storage import locked, read, save

__all__ = ["PresenceTracker"]


class PresenceTracker:
    def __init__(self, root, bus, clock=time.time):
        self.lock = RLock()
        self.path = root / "presence.json"
        self.bus = bus
        self.clock = clock
        self.data = dict(
            last_seen_at=0,
            last_user_message_at=0,
            last_app_start_at=0,
            app_start_history=[],
            days_absent=0,
            hours_absent=0,
            absence_bucket="none",
            last_proactive_at=0,
            proactive_history=[],
            last_returned_at=0,
            total_runs=0,
            longest_absence_days=0,
        ) | read(self.path, {})

    @locked
    def tick(self):
        d = self.data
        now = self.clock()
        h = max(0, now - (d["last_user_message_at"] or d["last_seen_at"] or now)) / 3600
        for t in (6, 24, 72):
            if d["hours_absent"] < t <= h:
                self.bus.emit("absence_threshold_crossed", {"hours": t})
        d.update(
            hours_absent=h,
            days_absent=h / 24,
            longest_absence_days=max(d["longest_absence_days"], h / 24),
            absence_bucket=next(
                k
                for t, k in [
                    (72, "three_plus"),
                    (48, "two_days"),
                    (24, "one_day"),
                    (4, "hours"),
                    (0, "none"),
                ]
                if h >= t
            ),
        )
        save(self.path, d)

    def bucket(self):
        return self.data["absence_bucket"]

    @locked
    def on_user_message(self):
        self.tick()
        d = self.data
        now = self.clock()
        if d["hours_absent"] >= 4:
            d["welcome"] = d["days_absent"] >= 2
            self.bus.emit("user_returned", {"after_days": d["days_absent"]})
            d["last_returned_at"] = now
        d.update(last_seen_at=now, last_user_message_at=now)
        self.tick()

    @locked
    def on_app_start(self):
        d = self.data
        now = self.clock()
        d["total_runs"] += 1
        d["last_app_start_at"] = now
        d["last_seen_at"] = d["last_seen_at"] or now
        d["app_start_history"] = (d["app_start_history"] + [now])[-200:]
        self.tick()
        self.bus.emit("app_started")

    @locked
    def on_app_close(self):
        self.bus.emit("app_closed")
        self.tick()
