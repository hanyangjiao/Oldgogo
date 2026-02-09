from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from notification import voice_notifier


def test_emit_voice_disabled_skips_backends(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VOICE_ENABLED", "false")

    def _fail(*_args, **_kwargs):
        raise AssertionError("TTS backend should not be called when disabled")

    monkeypatch.setattr(voice_notifier, "_try_pyttsx3", _fail)
    monkeypatch.setattr(voice_notifier, "_try_espeak", _fail)
    monkeypatch.setattr(voice_notifier, "_try_macos_say", _fail)

    voice_notifier._emit_voice("test message")


def test_emit_voice_prefers_pyttsx3(monkeypatch: pytest.MonkeyPatch):
    calls = {"pyttsx3": 0, "espeak": 0, "say": 0}

    def _pyttsx3(_message: str) -> bool:
        calls["pyttsx3"] += 1
        return True

    def _espeak(_message: str) -> bool:
        calls["espeak"] += 1
        return True

    def _say(_message: str) -> bool:
        calls["say"] += 1
        return True

    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setattr(voice_notifier, "_try_pyttsx3", _pyttsx3)
    monkeypatch.setattr(voice_notifier, "_try_espeak", _espeak)
    monkeypatch.setattr(voice_notifier, "_try_macos_say", _say)

    voice_notifier._emit_voice("test message")
    assert calls == {"pyttsx3": 1, "espeak": 0, "say": 0}


def test_pyttsx3_uses_env_settings_and_voice(monkeypatch: pytest.MonkeyPatch):
    class _Voice:
        def __init__(self, name: str, voice_id: str):
            self.name = name
            self.id = voice_id

    class _Engine:
        def __init__(self):
            self.properties = {}
            self.spoken = []
            self.ran = False

        def setProperty(self, key, value):
            self.properties[key] = value

        def getProperty(self, key):
            if key == "voices":
                return [_Voice("English", "en"), _Voice("Chinese", "zh-CN")]
            return None

        def say(self, message: str):
            self.spoken.append(message)

        def runAndWait(self):
            self.ran = True

    engine = _Engine()
    fake_module = SimpleNamespace(init=lambda: engine)
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_module)
    monkeypatch.setenv("VOICE_RATE", "175")
    monkeypatch.setenv("VOICE_VOLUME", "0.7")

    ok = voice_notifier._try_pyttsx3("hello")
    assert ok is True
    assert engine.properties["rate"] == 175
    assert engine.properties["volume"] == 0.7
    assert engine.properties["voice"] == "zh-CN"
    assert engine.spoken == ["hello"]
    assert engine.ran is True
