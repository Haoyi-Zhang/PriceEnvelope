"""Minimal owned-state model of the decrease-barrier-increase protocol."""
from dataclasses import dataclass, field
from fractions import Fraction as Q

@dataclass
class Transition:
    old: tuple[Q, ...]
    target: tuple[Q, ...]
    epoch: int = 1
    rates: list[Q] = field(init=False)
    reduced: set[int] = field(default_factory=set)
    increased: set[int] = field(default_factory=set)

    def __post_init__(self):
        if len(self.old) != len(self.target) or any(v < 0 for v in self.old+self.target):
            raise ValueError("nonnegative equal-length vectors required")
        self.rates = list(self.old)

    def apply(self, epoch: int, phase: str, source: int) -> bool:
        if epoch != self.epoch or not 0 <= source < len(self.old):
            return False
        if phase == "decrease":
            if source in self.reduced or source in self.increased:
                return False
            self.rates[source] = min(self.old[source], self.target[source])
            self.reduced.add(source)
            return True
        if phase == "increase":
            if len(self.reduced) != len(self.old) or source in self.increased:
                return False
            self.rates[source] = self.target[source]
            self.increased.add(source)
            return True
        return False
