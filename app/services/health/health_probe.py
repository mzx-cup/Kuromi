"""L0-L4 health state machine — single component."""
from dataclasses import dataclass
from enum import Enum


class Level(Enum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


@dataclass
class HealthProbe:
    component: str
    downgrade_fails: int = 3
    upgrade_passes: int = 6
    current_level: Level = Level.L0
    _fail_streak: int = 0
    _pass_streak: int = 0

    def record(self, ok: bool) -> None:
        if ok:
            self._fail_streak = 0
            self._pass_streak += 1
            if self._pass_streak >= self.upgrade_passes and self.current_level != Level.L0:
                # Jump up upgrade_passes levels on a full pass streak.
                self.current_level = Level(max(0, self.current_level.value - self.upgrade_passes))
        else:
            self._pass_streak = 0
            self._fail_streak += 1
            if self._fail_streak >= self.downgrade_fails:
                # Jump down downgrade_fails levels on a full fail streak.
                self.current_level = Level(min(4, self.current_level.value + self.downgrade_fails))
