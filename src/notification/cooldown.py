from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CooldownState:
    remaining_cycles: int = 0

    def to_dict(self) -> dict:
        return {"remaining_cycles": self.remaining_cycles}

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownState":
        return cls(remaining_cycles=int(data.get("remaining_cycles", 0)))


class CooldownStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> CooldownState:
        if not self.path.exists():
            return CooldownState()
        with open(self.path, "r", encoding="utf-8") as handle:
            return CooldownState.from_dict(json.load(handle))

    def save(self, state: CooldownState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)


class CooldownTracker:
    def __init__(self, cycles_after_reminder: int, store: CooldownStore):
        self.cycles_after_reminder = max(0, cycles_after_reminder)
        self.store = store

    def can_remind(self) -> bool:
        return self.store.load().remaining_cycles == 0

    def record_reminder(self) -> None:
        state = CooldownState(remaining_cycles=self.cycles_after_reminder)
        self.store.save(state)

    def tick(self) -> None:
        state = self.store.load()
        if state.remaining_cycles > 0:
            state.remaining_cycles -= 1
        self.store.save(state)

