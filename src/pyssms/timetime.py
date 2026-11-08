"""Time-time conflict polygon and the indicators of Laureshyn et al. (2010).

Road user ``i`` is predicted to move with constant velocity ``v_i`` (the assumption of the
2010 paper). Give each road user its own clock ``tau_i >= 0`` (time from now). The two bodies
overlap at the pair of clock readings ``(tau1, tau2)`` exactly when

    (c2 - c1) + v2 * tau2 - v1 * tau1  in  M = S1 (+) (-S2),

which is a set of linear inequalities in ``(tau1, tau2)``. Their solution set, clipped to the
prediction horizon ``[0, T]^2``, is the *conflict polygon* ``K``: a convex polygon (it may
degenerate to a segment, a point or the empty set). When the paths are parallel or a road user
stands still, the inequalities have rank one and ``K`` is a strip; the horizon box turns it into a
bounded polygon, so no case needs special treatment.

Undisturbed motion is the diagonal ``tau1 == tau2``. Delaying one road user by ``delta`` moves
along ``tau1 - tau2 = delta``. The four indicators of the 2010 paper are then readings of ``K``:

* Time-to-Collision ``TTC = min{t : (t, t) in K}`` (collision course, state A);
* Time Advantage ``TAdv = min{|tau1 - tau2| : (tau1, tau2) in K}`` (the "minimal delay of the
  first road user which, if applied, will result in a collision"; zero on a collision course);
* ``T2`` = arrival time of the second road user at the avoided collision point
  ``= max(tau1, tau2)`` at the minimiser of TAdv (equal to TTC on a collision course);
* Time Gap ``TG = min{max(tau1, tau2) : (tau1, tau2) in K}`` (the delay that gives the collision
  point closest in time; the time for the second road user to get there).

All objectives are piecewise linear, so the optima are attained at vertices of ``K`` or, for
TTC, at an end of the diagonal chord; the computation is exact up to floating point.

If ``K`` is empty the future paths do not overlap within the horizon (state C, or the encounter
is over). Values whose optimum lies on the horizon edge are reported as ``NaN``.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from numpy.typing import ArrayLike

from pyssms.geometry import (
    BoolArray,
    FloatArray,
    IntArray,
    StrArray,
    minkowski_halfplanes,
    rectangle,
)

__all__ = ["Indicators", "conflict_polygon", "indicators", "indicators_rect", "constraint_rows"]

_EPS_ROW = 1e-12  # a row with smaller norm has no tau-dependence
_EPS_DET = 1e-12  # parallel constraint lines
_TOL = 1e-9  # feasibility tolerance in seconds (rows are normalised)


@dataclass(frozen=True)
class Indicators:
    """Indicator arrays for ``N`` encounters (seconds; ``NaN`` where undefined).

    Attributes:
        ttc: Time-to-Collision; finite only on a collision course (state A).
        tadv: Time Advantage; 0 on a collision course.
        t2: Arrival time of the second road user at the (avoided) collision point.
        tg: Time Gap.
        first: 1 or 2 = road user that passes the avoided collision point first; 0 on a
            collision course or when undefined.
        state: ``"A"`` collision course, ``"B"`` crossing course, ``"C"`` no overlap of the
            future paths within the horizon.
    """

    ttc: FloatArray
    tadv: FloatArray
    t2: FloatArray
    tg: FloatArray
    first: IntArray
    state: StrArray


def constraint_rows(
    shape1: FloatArray,
    pos1: FloatArray,
    vel1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    vel2: FloatArray,
    horizon: float,
) -> tuple[FloatArray, FloatArray, FloatArray, BoolArray]:
    """Rows ``a*tau1 + c*tau2 <= r`` of ``K`` including the horizon box.

    Rows are normalised to unit length in the ``(tau1, tau2)`` plane, so residuals are in
    seconds. Rows with no ``tau``-dependence (rank-deficient cases) are replaced by an always
    satisfied row; the returned ``ok`` flag is ``False`` where such a row is violated, which
    means ``K`` is empty.

    Returns:
        ``a``, ``c``, ``r`` of shape ``(N, m)`` and ``ok`` of shape ``(N,)``.
    """
    normals, b = minkowski_halfplanes(shape1, shape2)
    d = pos2 - pos1
    a = -np.einsum("nkd,nd->nk", normals, vel1)
    c = np.einsum("nkd,nd->nk", normals, vel2)
    r = b - np.einsum("nkd,nd->nk", normals, d)
    norm = np.hypot(a, c)
    flat = norm < _EPS_ROW
    ok = ~np.any(flat & (r < -1e-12), axis=1)
    safe = np.where(flat, 1.0, norm)
    a = np.where(flat, 0.0, a / safe)
    c = np.where(flat, 0.0, c / safe)
    r = np.where(flat, np.inf, r / safe)
    n = a.shape[0]
    box_a = np.tile(np.array([-1.0, 0.0, 1.0, 0.0]), (n, 1))
    box_c = np.tile(np.array([0.0, -1.0, 0.0, 1.0]), (n, 1))
    box_r = np.tile(np.array([0.0, 0.0, horizon, horizon]), (n, 1))
    return (
        np.concatenate([a, box_a], axis=1),
        np.concatenate([c, box_c], axis=1),
        np.concatenate([r, box_r], axis=1),
        ok,
    )


def _vertices(a: FloatArray, c: FloatArray, r: FloatArray) -> tuple[FloatArray, BoolArray]:
    """All feasible pairwise intersections of the constraint lines: ``(N, P, 2)`` and mask."""
    m = a.shape[1]
    idx = np.array(list(combinations(range(m), 2)))
    i, j = idx[:, 0], idx[:, 1]
    ai, aj, ci, cj, ri, rj = a[:, i], a[:, j], c[:, i], c[:, j], r[:, i], r[:, j]
    det = ai * cj - aj * ci
    good = (np.abs(det) > _EPS_DET) & np.isfinite(ri) & np.isfinite(rj)
    sdet = np.where(good, det, 1.0)
    with np.errstate(invalid="ignore"):
        t1 = np.where(good, (ri * cj - rj * ci) / sdet, np.nan)
        t2 = np.where(good, (ai * rj - aj * ri) / sdet, np.nan)
        verts = np.stack([t1, t2], axis=-1)
        # Feasibility of every candidate vertex against every row as one batched product
        # (N, P, 2) @ (N, 2, m); faster than three broadcast temporaries and identical in value.
        lhs = np.matmul(np.where(good[..., None], verts, 0.0), np.stack([a, c], axis=1))
        feas = good & np.all(lhs <= r[:, None, :] + _TOL, axis=2)
    return verts, feas


def _diagonal(a: FloatArray, c: FloatArray, r: FloatArray) -> FloatArray:
    """Smallest ``t`` with ``(t, t)`` in ``K`` (``NaN`` if the diagonal misses ``K``)."""
    s = a + c
    neg, pos = s < -_EPS_ROW, s > _EPS_ROW
    with np.errstate(divide="ignore", invalid="ignore"):
        q = r / s
    lo = np.max(np.where(neg, q, -np.inf), axis=1)
    hi = np.min(np.where(pos, q, np.inf), axis=1)
    zero_ok = np.all(np.where(~neg & ~pos, r >= -_TOL, True), axis=1)
    hit = zero_ok & (lo <= hi + _TOL)
    out: FloatArray = np.where(hit, np.maximum(lo, 0.0), np.nan)
    return out


def _evaluate(
    a: FloatArray, c: FloatArray, r: FloatArray, ok: BoolArray, horizon: float
) -> Indicators:
    edge = horizon - 1e-6
    ttc = np.where(ok, _diagonal(a, c, r), np.nan)
    ttc = np.where(ttc < edge, ttc, np.nan)
    verts, feas = _vertices(a, c, r)
    feas &= ok[:, None]
    tau1, tau2 = verts[..., 0], verts[..., 1]
    later = np.where(feas, np.maximum(tau1, tau2), np.inf)
    gap = np.where(feas, np.abs(tau1 - tau2), np.inf)

    on_course = np.isfinite(ttc)
    best_gap = gap.min(axis=1)
    tie = gap <= best_gap[:, None] + _TOL
    k = np.argmin(np.where(tie, later, np.inf), axis=1)
    rows = np.arange(a.shape[0])
    t2_b = later[rows, k]
    first_b = np.where(tau1[rows, k] < tau2[rows, k], 1, 2)
    valid_b = np.isfinite(best_gap) & (t2_b < edge)

    tadv = np.where(on_course, 0.0, np.where(valid_b, best_gap, np.nan))
    t2 = np.where(on_course, ttc, np.where(valid_b, t2_b, np.nan))
    first = np.where(on_course | ~valid_b, 0, first_b)

    tg_v = later.min(axis=1)
    tg = np.minimum(tg_v, np.where(on_course, ttc, np.inf))
    tg = np.where(tg < edge, tg, np.nan)

    state = np.where(on_course, "A", np.where(valid_b, "B", "C"))
    return Indicators(ttc=ttc, tadv=tadv, t2=t2, tg=tg, first=first, state=state)


def _side_rows_axis_parallel(a: FloatArray, c: FloatArray) -> BoolArray:
    """Encounters whose four side-face rows are parallel to the axes of the time-time plane.

    Applies to two rectangles (rows 0-3 are the faces of body 1 in the order front, left, rear,
    right; rows 4-7 those of body 2): the left and right faces of body 1 have ``a == 0`` when body 1
    moves along its length, and those of body 2 have ``c == 0``. Then each of the four rows bounds
    one clock only.
    """
    tol = _EPS_ROW
    out: BoolArray = (
        (np.abs(a[:, 1]) <= tol)
        & (np.abs(a[:, 3]) <= tol)
        & (np.abs(c[:, 5]) <= tol)
        & (np.abs(c[:, 7]) <= tol)
    )
    return out


def _merge_side_rows(
    a: FloatArray, c: FloatArray, r: FloatArray, horizon: float
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Fold the four axis-parallel side rows into the horizon box (12 rows -> 8).

    Row ``(a, c, r)`` with ``a == 0`` is ``c tau2 <= r`` with ``c = +-1`` (rows are normalised): an
    upper (``c = 1``) or lower (``c = -1``) bound of ``tau2``; likewise ``c == 0`` bounds ``tau1``.
    The result describes the same polygon ``K`` with the four slanted rows (front and rear faces)
    and a box ``[lo1, hi1] x [lo2, hi2]``. A flat row (``r == inf``) bounds nothing.
    """
    n = a.shape[0]
    hi1: FloatArray = np.full(n, horizon)
    lo1: FloatArray = np.zeros(n)
    hi2: FloatArray = np.full(n, horizon)
    lo2: FloatArray = np.zeros(n)
    for k in (5, 7):  # body 2 side faces: c == 0, a = +-1 bounds tau1
        up, low = a[:, k] > 0.5, a[:, k] < -0.5
        hi1 = np.asarray(np.where(up, np.minimum(hi1, r[:, k]), hi1), dtype=float)
        lo1 = np.asarray(np.where(low, np.maximum(lo1, -r[:, k]), lo1), dtype=float)
    for k in (1, 3):  # body 1 side faces: a == 0, c = +-1 bounds tau2
        up, low = c[:, k] > 0.5, c[:, k] < -0.5
        hi2 = np.asarray(np.where(up, np.minimum(hi2, r[:, k]), hi2), dtype=float)
        lo2 = np.asarray(np.where(low, np.maximum(lo2, -r[:, k]), lo2), dtype=float)
    slanted = [0, 2, 4, 6]
    z = np.zeros(n)
    one = np.ones(n)
    a_new = np.concatenate([a[:, slanted], np.stack([-one, z, one, z], 1)], axis=1)
    c_new = np.concatenate([c[:, slanted], np.stack([z, -one, z, one], 1)], axis=1)
    r_new = np.concatenate([r[:, slanted], np.stack([-lo1, -lo2, hi1, hi2], 1)], axis=1)
    return a_new, c_new, r_new


def _evaluate_chunk(
    a: FloatArray, c: FloatArray, r: FloatArray, ok: BoolArray, horizon: float, fast: bool
) -> Indicators:
    """Evaluate one block of rows, using the 8-row form where the side rows are axis-parallel."""
    if fast and a.shape[1] == 12:
        side = _side_rows_axis_parallel(a, c)
        if side.any():
            if side.all():
                return _evaluate(*_merge_side_rows(a, c, r, horizon), ok, horizon)
            first = _evaluate(
                *_merge_side_rows(a[side], c[side], r[side], horizon), ok[side], horizon
            )
            rest = _evaluate(a[~side], c[~side], r[~side], ok[~side], horizon)
            n = a.shape[0]
            cols = {}
            for f in Indicators.__annotations__:
                x, y = getattr(first, f), getattr(rest, f)
                out = np.empty(n, dtype=x.dtype)
                out[side], out[~side] = x, y
                cols[f] = out
            return Indicators(**cols)
    return _evaluate(a, c, r, ok, horizon)


def indicators(
    shape1: FloatArray,
    pos1: ArrayLike,
    vel1: ArrayLike,
    shape2: FloatArray,
    pos2: ArrayLike,
    vel2: ArrayLike,
    horizon: float = 60.0,
    chunk: int = 500,
    fast: bool = True,
) -> Indicators:
    """TTC, TAdv, T2 and TG for convex polygonal road users (vectorised).

    Args:
        shape1: Footprint of road user 1 relative to its reference point, ``(N, V1, 2)``.
        pos1: Reference point ``(N, 2)``.
        vel1: Velocity ``(N, 2)`` (m/s); the body translates without rotating.
        shape2: Footprint of road user 2, ``(N, V2, 2)``.
        pos2: Reference point of road user 2.
        vel2: Velocity of road user 2.
        horizon: Prediction horizon ``T`` in seconds.
        chunk: Encounters processed per block (memory and cache control; 500 is about
            1.5 times faster than 20,000 on the benchmark machine).
        fast: Use the 8-row form of ``K`` for pairs of rectangles that move along their length
            (side faces parallel to the axes of the time-time plane, exactly: ``|a| <= 1e-12``);
            other encounters use the general 12-row form. The result is the same polygon.

    Returns:
        :class:`Indicators`.
    """
    p1 = np.atleast_2d(np.asarray(pos1, float))
    p2 = np.atleast_2d(np.asarray(pos2, float))
    u1 = np.atleast_2d(np.asarray(vel1, float))
    u2 = np.atleast_2d(np.asarray(vel2, float))
    n = p1.shape[0]
    parts = []
    for s in range(0, n, chunk):
        e = slice(s, s + chunk)
        rows = constraint_rows(shape1[e], p1[e], u1[e], shape2[e], p2[e], u2[e], horizon)
        parts.append(_evaluate_chunk(*rows, horizon, fast))
    return Indicators(
        **{f: np.concatenate([getattr(p, f) for p in parts]) for f in Indicators.__annotations__}
    )


def indicators_rect(
    x1: ArrayLike,
    y1: ArrayLike,
    heading1: ArrayLike,
    vx1: ArrayLike,
    vy1: ArrayLike,
    length1: ArrayLike,
    width1: ArrayLike,
    x2: ArrayLike,
    y2: ArrayLike,
    heading2: ArrayLike,
    vx2: ArrayLike,
    vy2: ArrayLike,
    length2: ArrayLike,
    width2: ArrayLike,
    horizon: float = 60.0,
) -> Indicators:
    """Indicators for rectangular road users given by centre, heading, velocity and size."""
    cols = np.broadcast_arrays(
        *[
            np.atleast_1d(np.asarray(v, float))
            for v in (x1, y1, heading1, vx1, vy1, length1, width1)
            + (x2, y2, heading2, vx2, vy2, length2, width2)
        ]
    )
    x1a, y1a, h1, vx1a, vy1a, l1, w1, x2a, y2a, h2, vx2a, vy2a, l2, w2 = cols
    return indicators(
        rectangle(h1, l1, w1),
        np.stack([x1a, y1a], -1),
        np.stack([vx1a, vy1a], -1),
        rectangle(h2, l2, w2),
        np.stack([x2a, y2a], -1),
        np.stack([vx2a, vy2a], -1),
        horizon,
    )


def conflict_polygon(
    shape1: FloatArray,
    pos1: ArrayLike,
    vel1: ArrayLike,
    shape2: FloatArray,
    pos2: ArrayLike,
    vel2: ArrayLike,
    horizon: float = 60.0,
) -> FloatArray:
    """Ordered vertices ``(k, 2)`` of the conflict polygon ``K`` for one encounter (for plots)."""
    rows = constraint_rows(
        shape1[:1],
        np.atleast_2d(np.asarray(pos1, float)),
        np.atleast_2d(np.asarray(vel1, float)),
        shape2[:1],
        np.atleast_2d(np.asarray(pos2, float)),
        np.atleast_2d(np.asarray(vel2, float)),
        horizon,
    )
    if not rows[3][0]:
        return np.empty((0, 2))
    verts, feas = _vertices(*rows[:3])
    pts = np.unique(np.round(verts[0][feas[0]], 9), axis=0)
    if len(pts) < 3:
        out: FloatArray = pts
        return out
    centre = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - centre[1], pts[:, 0] - centre[0])
    ordered: FloatArray = pts[np.argsort(ang)]
    return ordered
