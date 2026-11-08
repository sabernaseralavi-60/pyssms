"""Random encounters of rectangular road users for equivalence tests and benchmarks.

Each encounter is built around a potential conflict point ``X``: road user ``i`` is placed so
that it would reach ``X`` after ``t_i`` seconds, plus a lateral offset. This gives a mixture of
collision courses (A), crossing courses (B) and non-overlapping paths (C). ``kind`` adds the
cases where the 2010 appendix is fragile or silent: parallel or opposite headings, a road user
standing still, axis-aligned bodies (sides with ``x1 == x2`` or ``y1 == y2``) and bodies that
already overlap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pyssms.geometry import FloatArray, rectangle

__all__ = ["KINDS", "Encounters", "random_encounters"]

KINDS = ("generic", "parallel", "stopped", "axis_aligned", "overlap")

# length, width (m): car, pedestrian, cyclist, truck
_SIZES = np.array([[4.5, 1.8], [0.6, 0.6], [1.8, 0.7], [12.0, 2.5]])
_SPEEDS = np.array([[3.0, 20.0], [0.5, 2.0], [2.0, 8.0], [3.0, 16.0]])


@dataclass(frozen=True)
class Encounters:
    """Centres, headings, velocities and sizes of ``N`` encounters (road users 1 and 2)."""

    pos1: FloatArray
    vel1: FloatArray
    heading1: FloatArray
    size1: FloatArray
    pos2: FloatArray
    vel2: FloatArray
    heading2: FloatArray
    size2: FloatArray

    @property
    def shape1(self) -> FloatArray:
        """Footprints of road user 1 relative to the centre."""
        return rectangle(self.heading1, self.size1[:, 0], self.size1[:, 1])

    @property
    def shape2(self) -> FloatArray:
        """Footprints of road user 2 relative to the centre."""
        return rectangle(self.heading2, self.size2[:, 0], self.size2[:, 1])

    @property
    def corners1(self) -> FloatArray:
        """Absolute corners of road user 1."""
        return self.shape1 + self.pos1[:, None, :]

    @property
    def corners2(self) -> FloatArray:
        """Absolute corners of road user 2."""
        return self.shape2 + self.pos2[:, None, :]


def random_encounters(n: int, kind: str = "generic", seed: int = 0) -> Encounters:
    """Draw ``n`` random encounters of the given ``kind`` (see :data:`KINDS`)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    rng = np.random.default_rng(seed)
    cls1, cls2 = rng.integers(0, 4, n), rng.integers(0, 4, n)
    size1, size2 = _SIZES[cls1], _SIZES[cls2]
    sp1 = rng.uniform(_SPEEDS[cls1, 0], _SPEEDS[cls1, 1])
    sp2 = rng.uniform(_SPEEDS[cls2, 0], _SPEEDS[cls2, 1])
    h1 = rng.uniform(-np.pi, np.pi, n)
    h2 = rng.uniform(-np.pi, np.pi, n)
    if kind == "parallel":
        h2 = h1 + np.where(rng.random(n) < 0.5, 0.0, np.pi)
    if kind == "axis_aligned":
        h1 = rng.integers(0, 4, n).astype(float) * (np.pi / 2)
        h2 = rng.integers(0, 4, n).astype(float) * (np.pi / 2)
    if kind == "stopped":
        who = rng.random(n) < 0.5
        sp1 = np.where(who, 0.0, sp1)
        sp2 = np.where(~who, 0.0, sp2)
    d1 = np.stack([np.cos(h1), np.sin(h1)], -1)
    d2 = np.stack([np.cos(h2), np.sin(h2)], -1)
    v1, v2 = d1 * sp1[:, None], d2 * sp2[:, None]
    t1, t2 = rng.uniform(0.0, 8.0, n), rng.uniform(0.0, 8.0, n)
    if kind == "overlap":
        t1, t2 = np.zeros(n), rng.uniform(0.0, 0.3, n) * size2[:, 0] / np.maximum(sp2, 0.1)
    lat1 = rng.normal(0.0, 1.5, n)[:, None] * np.stack([-d1[:, 1], d1[:, 0]], -1)
    lat2 = rng.normal(0.0, 1.5, n)[:, None] * np.stack([-d2[:, 1], d2[:, 0]], -1)
    x = rng.uniform(-20.0, 20.0, (n, 2))
    # travel time to X for a stopped user: place it near X
    p1 = x - d1 * (sp1 * t1)[:, None] + lat1
    p2 = x - d2 * (sp2 * t2)[:, None] + lat2
    if kind == "overlap":
        p1, p2 = x, x - d2 * (sp2 * t2)[:, None] + 0.2 * lat2
    return Encounters(p1, v1, h1, size1, p2, v2, h2, size2)
