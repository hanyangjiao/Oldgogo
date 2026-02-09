#!/usr/bin/env python3
"""Test script for voice reminder functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notification.cooldown import CooldownStore, CooldownTracker
from notification.voice_notifier import send_voice_reminder

def test_voice():
    """Test voice reminder with real TTS."""
    print("=" * 70)
    print("VOICE REMINDER TEST")
    print("=" * 70)
    print()

    # Create a temporary cooldown tracker (no cooldown for testing)
    store = CooldownStore(Path("/tmp/test_cooldown.json"))
    tracker = CooldownTracker(cycles_after_reminder=0, store=store)

    # Test messages
    test_messages = [
        "Repeated task detected but the task is not repeatable.",
        "Fall detected! Please check on the person.",
        "Heart rate is too high. Tachycardia detected.",
        "Heart rate is too low. Bradycardia detected.",
    ]

    print("Testing voice reminders...\n")

    for i, message in enumerate(test_messages, 1):
        print(f"\n[Test {i}/{len(test_messages)}]")
        print("-" * 70)
        success = send_voice_reminder(message, tracker)
        print(f"Status: {'✓ Sent' if success else '✗ Failed (cooldown)'}")
        print()

        if i < len(test_messages):
            input("Press Enter for next test...")

    print("\n" + "=" * 70)
    print("VOICE TEST COMPLETE")
    print("=" * 70)
    print("\nIf you heard the voice messages, the TTS is working!")
    print("If not, check that:")
    print("  • pyttsx3 is installed: pip install pyttsx3")
    print("  • Your system has audio output enabled")
    print("  • Volume is not muted")

if __name__ == "__main__":
    test_voice()
