#!/usr/bin/env python3
"""Quick non-interactive test for voice reminder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notification.cooldown import CooldownStore, CooldownTracker
from notification.voice_notifier import send_voice_reminder

def main():
    print("Testing voice reminder...")
    store = CooldownStore(Path("/tmp/test_cooldown.json"))
    tracker = CooldownTracker(cycles_after_reminder=0, store=store)

    message = "Repeated task detected but the task is not repeatable."
    success = send_voice_reminder(message, tracker)

    if success:
        print("\n✓ Voice reminder sent successfully!")
        print("  (If you didn't hear it, check your audio settings)")
    else:
        print("\n✗ Voice reminder failed")

if __name__ == "__main__":
    main()
