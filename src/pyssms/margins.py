"""Physical margins to a collision course: time margin (s) and lateral margin (m).

Two of the three candidate definitions of ``docs/beta_proposal.md`` (the third, a statistically
scaled combination, is an open question):

* **Time margin** = Time Advantage (:mod:`pyssms.timetime`): the smallest delay of one road user
  that puts the encounter on a collision course (0 on a collision course).
* **Lateral margin**: the smallest sideways shift (perpendicular to the direction of travel) of
  one road user's path that puts the encounter on a collision course, all else (speeds, timing)
  unchanged.
  It is finite for non-crossing courses (state C) such as two vehicles in adjacent lanes, which
  the time margin cannot describe.

For constant velocities and a shift ``delta`` of road user ``i`` along its unit normal ``u_i``, the
bodies overlap at time ``t`` iff ``n_k . (v2 - v1) t + e_k delta <= b_k - n_k . (c2 - c1)`` for all
edge normals ``n_k`` of the Minkowski difference, with ``e_k = +n_k . u_2`` (road user 2 shifted) or
``-n_k . u_1`` (road user 1 shifted). That is a polygon in the ``(t, delta)`` plane; the shortest
distance from ``delta = 0`` to its projection on the ``delta`` axis is the margin.
"""

from __future__ import annotations

import numpy as np

from pyssms.geometry import FloatArray, minkowski_halfplanes
from pyssms.timetime import _vertices

__all__ = ["lateral_margin"]


def _one_side(
    shape1: FloatArray,
    pos1: FloatArray,
    vel1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    vel2: FloatArray,
    normal: FloatArray,
    who: int,
    horizon: float,
    max_shift: float,
) -> tuple[FloatArray, FloatArray]:
    normals, b = minkowski_halfplanes(shape1, shape2)
    a = np.einsum("nkd,nd->nk", normals, vel2 - vel1)  # coefficient of t
    sign = 1.0 if who == 2 else -1.0
    e = sign * np.einsum("nkd,nd->nk", normals, normal)  # coefficient of delta
    r = b - np.einsum("nkd,nd->nk", normals, pos2 - pos1)
    norm = np.hypot(a, e)
    flat = norm < 1e-12
    bad = np.any(flat & (r < -1e-12), axis=1)
    safe = np.where(flat, 1.0, norm)
    a, e, r = (
        np.where(flat, 0.0, a / safe),
        np.where(flat, 0.0, e / safe),
        np.where(flat, np.inf, r / safe),
    )
    n = a.shape[0]
    box = [(-1.0, 0.0, 0.0), (1.0, 0.0, horizon), (0.0, -1.0, max_shift), (0.0, 1.0, max_shift)]
    a = np.concatenate([a] + [np.full((n, 1), q[0]) for q in box], axis=1)
    e = np.concatenate([e] + [np.full((n, 1), q[1]) for q in box], axis=1)
    r = np.concatenate([r] + [np.full((n, 1), q[2]) for q in box], axis=1)
    verts, feas = _vertices(a, e, r)
    feas &= ~bad[:, None]
    delta = verts[..., 1]
    lo = np.where(feas, delta, np.inf).min(axis=1)
    hi = np.where(feas, delta, -np.inf).max(axis=1)
    shift = np.where(lo <= 0.0, np.where(hi >= 0.0, 0.0, hi), lo)
    shift = np.where(np.isfinite(lo), shift, np.nan)
    margin = np.abs(shift)
    margin = np.where(margin < max_shift - 1e-6, margin, np.nan)
    return margin, np.where(np.isnan(margin), np.nan, shift)


def lateral_margin(
    shape1: FloatArray,
    pos1: FloatArray,
    vel1: FloatArray,
    normal1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    vel2: FloatArray,
    normal2: FloatArray,
    horizon: float = 10.0,
    max_shift: float = 20.0,
) -> dict[str, FloatArray]:
    """Smallest sideways shift of either path that creates a collision course within ``horizon``.

    Args:
        shape1: Footprint of road user 1 relative to its centre, ``(N, V, 2)``.
        pos1: Centre, ``(N, 2)``.
        vel1: Velocity, ``(N, 2)`` (constant, no rotation).
        normal1: Unit vector along which road user 1 is shifted (usually its left normal),
            ``(N, 2)``.
        shape2: Footprint of road user 2.
        pos2: Centre of road user 2.
        vel2: Velocity of road user 2.
        normal2: Unit shift direction of road user 2.
        horizon: Prediction horizon (s).
        max_shift: Largest shift considered (m); larger optima are reported as ``NaN``.

    Returns:
        Dict with ``margin1``/``shift1`` (road user 1 shifted), ``margin2``/``shift2``, and
        ``margin`` = the smaller of the two (m; 0 on a collision course; ``NaN`` if none within
        the limits). ``shift*`` carry the sign along the given normal.
    """
    m1, s1 = _one_side(shape1, pos1, vel1, shape2, pos2, vel2, normal1, 1, horizon, max_shift)
    m2, s2 = _one_side(shape1, pos1, vel1, shape2, pos2, vel2, normal2, 2, horizon, max_shift)
    best = np.fmin(m1, m2)
    return {"margin": best, "margin1": m1, "shift1": s1, "margin2": m2, "shift2": s2}
