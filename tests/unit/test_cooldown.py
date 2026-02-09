# Covers: F8
from pathlib import Path

from notification.cooldown import CooldownStore, CooldownTracker


def test_cooldown_cycles(tmp_path: Path):
    store = CooldownStore(tmp_path / "cooldown.json")
    tracker = CooldownTracker(cycles_after_reminder=2, store=store)

    assert tracker.can_remind() is True
    tracker.record_reminder()
    assert tracker.can_remind() is False

    tracker.tick()
    assert tracker.can_remind() is False

    tracker.tick()
    assert tracker.can_remind() is True

