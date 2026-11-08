"""Trajectory container shared by all readers and by the encounter processing.

A :class:`Trajectories` object is a *long table*: one row per road user per time stamp, stored as
parallel NumPy arrays (no pandas dependency). Positions are the **centre** of the body (m),
``heading`` is the body orientation in radians (counter-clockwise from the x axis), velocities are
in m/s and sizes in m. Readers fill ``vx``/``vy`` from the source when it provides them and by
finite differences otherwise (:func:`finite_difference_velocity`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike

from pyssms.geometry import FloatArray, IntArray, StrArray

__all__ = ["Trajectories", "finite_difference_velocity", "from_arrays"]

_FIELDS = ("t", "uid", "x", "y", "heading", "vx", "vy", "length", "width")


@dataclass(frozen=True)
class Trajectories:
    """Long table of road-user states (all arrays have the same length ``n``).

    Attributes:
        t: Time (s).
        uid: Road-user id (integer; unique within a recording).
        x: Centre x (m).
        y: Centre y (m).
        heading: Body orientation (rad, counter-clockwise from +x).
        vx: Velocity x (m/s).
        vy: Velocity y (m/s).
        length: Body length (m); 0 where unknown.
        width: Body width (m); 0 where unknown.
        kind: Road-user class as text (``"car"``, ``"pedestrian"``, ... or ``""``).
        source: Free-text description of where the data came from.
        meta: Additional information of the reader (frame rate, units, file name, ...).
    """

    t: FloatArray
    uid: IntArray
    x: FloatArray
    y: FloatArray
    heading: FloatArray
    vx: FloatArray
    vy: FloatArray
    length: FloatArray
    width: FloatArray
    kind: StrArray
    source: str = ""
    meta: dict[str, object] = field(default_factory=dict)

    def __len__(self) -> int:
        """Number of rows."""
        return int(self.t.shape[0])

    @property
    def ids(self) -> IntArray:
        """Sorted unique road-user ids."""
        out: IntArray = np.unique(self.uid)
        return out

    @property
    def times(self) -> FloatArray:
        """Sorted unique time stamps."""
        out: FloatArray = np.unique(self.t)
        return out

    @property
    def dt(self) -> float:
        """Median spacing of the time stamps (s); ``nan`` for a single time stamp."""
        ts = self.times
        return float(np.median(np.diff(ts))) if ts.size > 1 else float("nan")

    def select(self, mask: ArrayLike) -> Trajectories:
        """Rows where ``mask`` is true (a boolean array of length ``n``)."""
        m = np.asarray(mask, dtype=bool)
        cols = {f: getattr(self, f)[m] for f in (*_FIELDS, "kind")}
        return Trajectories(**cols, source=self.source, meta=dict(self.meta))

    def track(self, uid: int) -> Trajectories:
        """Rows of a single road user, ordered by time."""
        sub = self.select(self.uid == uid)
        order = np.argsort(sub.t, kind="stable")
        cols = {f: getattr(sub, f)[order] for f in (*_FIELDS, "kind")}
        return Trajectories(**cols, source=self.source, meta=dict(self.meta))


def finite_difference_velocity(
    t: FloatArray, uid: IntArray, x: FloatArray, y: FloatArray
) -> tuple[FloatArray, FloatArray]:
    """Central-difference velocity per road user (one-sided at the ends).

    Rows need not be sorted. A road user with a single row gets zero velocity.
    """
    vx = np.zeros_like(x)
    vy = np.zeros_like(y)
    order = np.lexsort((t, uid))
    us = uid[order]
    starts = np.flatnonzero(np.r_[True, us[1:] != us[:-1]])
    stops = np.r_[starts[1:], us.size]
    for s, e in zip(starts, stops, strict=True):
        idx = order[s:e]
        if idx.size < 2:
            continue
        vx[idx] = np.gradient(x[idx], t[idx])
        vy[idx] = np.gradient(y[idx], t[idx])
    return vx, vy


def from_arrays(
    t: ArrayLike,
    uid: ArrayLike,
    x: ArrayLike,
    y: ArrayLike,
    heading: ArrayLike | None = None,
    vx: ArrayLike | None = None,
    vy: ArrayLike | None = None,
    length: ArrayLike | float = 0.0,
    width: ArrayLike | float = 0.0,
    kind: ArrayLike | str = "",
    source: str = "",
    meta: dict[str, object] | None = None,
) -> Trajectories:
    """Build a :class:`Trajectories` from columns, filling what is missing.

    Missing velocities are obtained by finite differences; a missing heading is the direction of
    the velocity (kept from the previous time stamp where the road user stands still).
    """
    ta = np.asarray(t, dtype=float)
    n = ta.shape[0]
    ua = np.asarray(uid).astype(np.int64)
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    if vx is None or vy is None:
        vxa, vya = finite_difference_velocity(ta, ua, xa, ya)
    else:
        vxa, vya = np.asarray(vx, dtype=float), np.asarray(vy, dtype=float)
    if heading is None:
        ha = _heading_from_velocity(ta, ua, vxa, vya)
    else:
        ha = np.asarray(heading, dtype=float)
    cols = {
        "length": np.broadcast_to(np.asarray(length, dtype=float), (n,)).copy(),
        "width": np.broadcast_to(np.asarray(width, dtype=float), (n,)).copy(),
        "kind": np.broadcast_to(np.asarray(kind, dtype=str), (n,)).copy(),
    }
    return Trajectories(
        t=ta, uid=ua, x=xa, y=ya, heading=ha, vx=vxa, vy=vya, **cols, source=source,
        meta=dict(meta or {}),
    )  # fmt: skip


def _heading_from_velocity(
    t: FloatArray, uid: IntArray, vx: FloatArray, vy: FloatArray, min_speed: float = 0.1
) -> FloatArray:
    """Direction of travel; below ``min_speed`` the last moving direction of that user is kept."""
    h = np.arctan2(vy, vx)
    slow = np.hypot(vx, vy) < min_speed
    if not slow.any():
        return h
    order = np.lexsort((t, uid))
    last: dict[int, float] = {}
    for i in order:
        u = int(uid[i])
        if slow[i]:
            h[i] = last.get(u, h[i])
        else:
            last[u] = h[i]
    return h
