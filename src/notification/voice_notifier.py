from __future__ import annotations

import os
import subprocess
from typing import Optional

from notification.cooldown import CooldownTracker


def send_voice_reminder(
    message: str,
    cooldown_tracker: CooldownTracker,
) -> bool:
    """Send a voice reminder if cooldown allows."""
    if not cooldown_tracker.can_remind():
        return False
    cooldown_tracker.record_reminder()
    _emit_voice(message)
    return True


def _emit_voice(message: str, device_id: Optional[str] = None) -> None:
    """
    Emit voice notification using available TTS engine.

    Supports multiple backends in order of preference:
    1. pyttsx3 (offline, cross-platform)
    2. espeak (Linux command-line)
    3. say (macOS command-line)
    4. fallback to console print

    Can be disabled via VOICE_ENABLED environment variable.
    """
    _ = device_id

    # Check if voice is enabled
    voice_enabled = os.getenv("VOICE_ENABLED", "true").lower() in ("true", "1", "yes")

    # Always print to console for logging
    print(f"[VOICE] {message}")

    if not voice_enabled:
        print("  (Voice output disabled via VOICE_ENABLED env variable)")
        return

    # Try different TTS backends
    success = (
        _try_pyttsx3(message) or
        _try_espeak(message) or
        _try_macos_say(message)
    )

    if not success:
        print("  (No TTS engine available - voice output disabled)")


def _try_pyttsx3(message: str) -> bool:
    """Try using pyttsx3 (offline, cross-platform)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()

        # Configure voice properties
        rate = int(os.getenv("VOICE_RATE", "150"))  # Speed (words per minute)
        volume = float(os.getenv("VOICE_VOLUME", "1.0"))  # 0.0 to 1.0

        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)

        # Try to use Chinese voice if available for better pronunciation
        voices = engine.getProperty('voices')
        chinese_voice = None
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                chinese_voice = voice.id
                break

        if chinese_voice:
            engine.setProperty('voice', chinese_voice)

        print(f"  → Speaking with pyttsx3 (rate={rate}, volume={volume})")
        engine.say(message)
        engine.runAndWait()
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"  ⚠ pyttsx3 failed: {e}")
        return False


def _try_espeak(message: str) -> bool:
    """Try using espeak (Linux command-line TTS)."""
    try:
        result = subprocess.run(
            ["espeak", message],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  → Speaking with espeak")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def _try_macos_say(message: str) -> bool:
    """Try using macOS 'say' command."""
    try:
        result = subprocess.run(
            ["say", message],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print("  → Speaking with macOS say")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False

