"""Short-term motion "stories" along straight paths and first contact on the overlap polygon.

Each road user moves along a straight line with unit direction ``d_i``; its travelled distance
is ``sigma_i(t)``. Its story is a polynomial in time (constant speed, constant acceleration or
constant jerk, the L2/F1 stories of Naseralavi et al., 2025); a decelerating road user stops when
its speed reaches zero and does not reverse (maximum or minimum braking stories are constant
acceleration with a negative value).

Two bodies overlap exactly when ``(sigma1, sigma2)`` lies in the polygon

    R = {(s1, s2) : (c2 - c1) + s2 d2 - s1 d1  in  S1 (+) (-S2)},

which is described by linear inequalities ``a_k s1 + c_k s2 <= r_k`` that depend only on the
geometry of the two paths, not on speeds, accelerations or jerks. A story therefore turns every
inequality into a polynomial inequality in ``t``. The first contact time is found on a fine time
grid and refined by bisection (exact to ``tol``); the result does not use the time-time
polygon of :mod:`pyssms.timetime`, which is the special case of constant velocity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from pyssms.geometry import FloatArray, minkowski_halfplanes

__all__ = ["Story", "first_contact", "overlap_rows", "profile"]


@dataclass(frozen=True)
class Story:
    """Kinematic story of one road user along its path (arrays of shape ``(N,)``).

    Attributes:
        v0: Initial speed (m/s, >= 0).
        a: Constant acceleration (m/s^2) or the initial acceleration if ``j`` is not zero.
        j: Constant jerk (m/s^3).
    """

    v0: FloatArray
    a: FloatArray
    j: FloatArray

    @staticmethod
    def constant_speed(v0: ArrayLike) -> Story:
        """L21 / F11: constant speed."""
        v = np.atleast_1d(np.asarray(v0, float))
        return Story(v, np.zeros_like(v), np.zeros_like(v))

    @staticmethod
    def constant_acceleration(v0: ArrayLike, a: ArrayLike) -> Story:
        """L22 / F12, or braking stories (L3, F22, F32) with a negative ``a``."""
        v, acc = np.broadcast_arrays(np.asarray(v0, float), np.asarray(a, float))
        v, acc = np.atleast_1d(v), np.atleast_1d(acc)
        return Story(v, acc, np.zeros_like(v))

    @staticmethod
    def constant_jerk(v0: ArrayLike, a0: ArrayLike, j: ArrayLike) -> Story:
        """L23 / F13: constant jerk."""
        v, a, jj = (np.atleast_1d(x) for x in np.broadcast_arrays(*map(np.asarray, (v0, a0, j))))
        return Story(v.astype(float), a.astype(float), jj.astype(float))

    def stop_time(self, horizon: float, h: float = 0.01) -> FloatArray:
        """Time when the speed reaches zero while braking (``inf`` if not within ``horizon``)."""
        grid = np.arange(0.0, horizon + h, h)
        t = grid[None, :]
        v = self.v0[:, None] + self.a[:, None] * t + 0.5 * self.j[:, None] * t**2
        started = self.v0 > 0
        below = (v <= 0) & (t > 0)
        first = np.where(below.any(1), below.argmax(1), -1)
        lo = np.where(first > 0, grid[np.maximum(first - 1, 0)], 0.0)
        hi = np.where(first > 0, grid[np.maximum(first, 0)], 0.0)
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            vm = self.v0 + self.a * mid + 0.5 * self.j * mid**2
            lo = np.where(vm > 0, mid, lo)
            hi = np.where(vm > 0, hi, mid)
        out = np.where(first > 0, hi, np.inf)
        # starting at rest and braking: stays at rest from t = 0
        out = np.where((~started) & (self.a < 0), 0.0, out)
        stop: FloatArray = np.where(started | (self.a < 0), out, np.inf)
        return stop

    def max_speed(self, horizon: float, t_stop: FloatArray, h: float = 0.01) -> FloatArray:
        """Largest speed on ``[0, horizon]`` (sampled; the stop time is respected)."""
        t = np.minimum(np.arange(0.0, horizon + h, h)[None, :], t_stop[:, None])
        v = self.v0[:, None] + self.a[:, None] * t + 0.5 * self.j[:, None] * t**2
        out: FloatArray = np.maximum(v, 0.0).max(axis=1) + 1e-3
        return out

    def sigma(self, t: FloatArray, t_stop: FloatArray) -> FloatArray:
        """Travelled distance at times ``t`` (broadcast against ``(N,)`` story arrays)."""
        te = np.minimum(t, t_stop)
        out: FloatArray = self.v0 * te + 0.5 * self.a * te**2 + self.j * te**3 / 6.0
        return out


def profile(story: Story, horizon: float = 10.0, dt: float = 0.1) -> dict[str, FloatArray]:
    """Position, speed, acceleration and jerk of each story on a time grid.

    Returns arrays of shape ``(N, len(t))`` for ``x``, ``v``, ``a``, ``j`` and the vector ``t``.
    """
    t = np.round(np.arange(0.0, horizon + dt / 2, dt), 10)
    ts = story.stop_time(horizon)[:, None]
    te = np.minimum(t[None, :], ts)
    moving = t[None, :] < ts
    v0, a0, j0 = story.v0[:, None], story.a[:, None], story.j[:, None]
    return {
        "t": t,
        "x": v0 * te + 0.5 * a0 * te**2 + j0 * te**3 / 6.0,
        "v": np.where(moving, v0 + a0 * te + 0.5 * j0 * te**2, 0.0),
        "a": np.where(moving, a0 + j0 * te, 0.0),
        "j": np.where(moving, j0, 0.0) * np.ones_like(te),
    }


def overlap_rows(
    shape1: FloatArray,
    pos1: FloatArray,
    dir1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    dir2: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Rows ``a s1 + c s2 <= r`` of the overlap polygon ``R`` in the (sigma1, sigma2) plane."""
    normals, b = minkowski_halfplanes(shape1, shape2)
    a = -np.einsum("nkd,nd->nk", normals, dir1)
    c = np.einsum("nkd,nd->nk", normals, dir2)
    r = b - np.einsum("nkd,nd->nk", normals, pos2 - pos1)
    return a, c, r


def first_contact(
    shape1: FloatArray,
    pos1: FloatArray,
    dir1: FloatArray,
    story1: Story,
    shape2: FloatArray,
    pos2: FloatArray,
    dir2: FloatArray,
    story2: Story,
    horizon: float = 10.0,
    min_step: float = 2e-3,
) -> FloatArray:
    """First time ``t`` in ``[0, horizon]`` when the bodies overlap (``NaN`` if never).

    Conservative advancement: ``g(t) = max_k (a_k s1(t) + c_k s2(t) - r_k)`` is positive while the
    bodies are apart and its slope is bounded by ``L = max speed1 + max speed2`` (the normals
    have unit length), so the time can safely jump ahead by ``g / L`` without skipping a contact.
    The contact time is then refined by bisection. A contact window shorter than ``min_step``
    can still be missed.

    Args:
        shape1: Footprint of road user 1 relative to its centre ``(N, V, 2)``.
        pos1: Centre at ``t = 0``, ``(N, 2)``.
        dir1: Unit direction of the straight path, ``(N, 2)``.
        story1: Story of road user 1.
        shape2: Footprint of road user 2.
        pos2: Centre of road user 2.
        dir2: Unit direction of road user 2.
        story2: Story of road user 2.
        horizon: Prediction horizon (s).
        min_step: Smallest advance per iteration (s).
    """
    a, c, r = overlap_rows(shape1, pos1, dir1, shape2, pos2, dir2)
    ts1, ts2 = story1.stop_time(horizon), story2.stop_time(horizon)
    lip = story1.max_speed(horizon, ts1) + story2.max_speed(horizon, ts2) + 1e-6

    def gap(t: FloatArray) -> FloatArray:
        s1, s2 = story1.sigma(t, ts1), story2.sigma(t, ts2)
        out: FloatArray = np.max(a * s1[:, None] + c * s2[:, None] - r, axis=1)
        return out

    n = pos1.shape[0]
    t: FloatArray = np.zeros(n)
    g: FloatArray = gap(t)
    lo: FloatArray = np.zeros(n)
    hi: FloatArray = np.zeros(n)
    found = g <= 0.0
    active = ~found
    while active.any():
        step = np.maximum(g / lip, min_step)
        tn = np.where(active, np.minimum(t + step, horizon), t)
        gn = np.where(active, gap(tn), g)
        hit = active & (gn <= 0.0)
        lo = np.where(hit, t, lo)
        hi = np.where(hit, tn, hi)
        found |= hit
        active &= ~hit & (tn < horizon)
        t, g = tn, gn
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        inside = gap(mid) <= 0.0
        hi = np.where(inside, mid, hi)
        lo = np.where(inside, lo, mid)
    first = np.where(np.isfinite(hi), hi, np.nan)
    out: FloatArray = np.where(found, np.where(lo == hi, 0.0, first), np.nan)
    return out
