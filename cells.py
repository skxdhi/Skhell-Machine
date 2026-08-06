"""Cell data object used by the simulation grid."""
from __future__ import annotations

from typing import Any, Optional


class Cell:
    __slots__ = (
        'x', 'y', 'direction', 'name',
        'oldx', 'oldy', 'olddirection',
        'effects', 'properties', 'updated', 'storing', 'other',
    )

    def __init__(
        self,
        x: int,
        y: int,
        direction,
        name: str,
        oldx=None,
        oldy=None,
        olddirection=None,
        effects=None,
        properties=None,
        updated: bool = False,
        storing=None,
        other=None,
    ):
        self.x = x
        self.y = y
        self.direction = direction % 4
        self.name = name.lower()

        self.oldx = oldx if oldx is not None else x
        self.oldy = oldy if oldy is not None else y
        self.olddirection = (
            olddirection % 4 if olddirection is not None else self.direction
        )

        self.effects = dict(effects) if effects is not None else {}
        self.properties = dict(properties) if properties is not None else {}
        self.updated = updated
        self.storing = storing
        self.other = dict(other) if other is not None else {}

    def copy(self) -> 'Cell':
        return Cell(
            self.x,
            self.y,
            self.direction,
            self.name,
            self.oldx,
            self.oldy,
            self.olddirection,
            self.effects,
            self.properties,
            self.updated,
            self.storing,
            self.other,
        )

    def reset(self) -> None:
        """Snap animation pose to current pose and clear per-tick effects."""
        self.oldx = self.x
        self.oldy = self.y
        self.olddirection = self.direction
        self.effects = {}
        self.updated = False

    def pos(self) -> tuple[int, int]:
        return (self.x, self.y)

    def set_pos(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Cell({self.name!r} @ ({self.x},{self.y}) dir={self.direction})"
