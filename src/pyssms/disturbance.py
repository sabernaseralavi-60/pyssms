"""Disturbance set of an encounter and the signed margin to a collision course.

Disturb a constant-velocity encounter in two ways at once: shift the clock of road user 1 against
that of road user 2 by ``delta`` seconds (``delta = tau1 - tau2``; the diagonal of the time-time
plane of :mod:`pyssms.timetime` is ``delta = 0``) and move the path of road user 2 sideways by
``eps`` metres along a unit vector ``u`` (shifting road user 1 along ``u`` is the same as shifting
road user 2 along ``-u``). The bodies overlap at some time ``t`` in ``[0, T]`` exactly when

    (c2 - c1) + eps*u + v2*t - v1*(t + delta)  in  M = S1 (+) (-S2),   t >= 0, t + delta in [0, T],

which is a set of linear inequalities in ``(t, delta, eps)``. Their solution set is a convex
polytope; its projection on the ``(delta, eps)`` plane is the **disturbance set** ``D``: a convex
polygon (Fourier-Motzkin elimination of ``t`` is exact and gives its half-planes). The undisturbed
encounter is the origin, so

* the origin lies in ``D`` iff the encounter is on a collision course (state A);
* Time Advantage is the shortest distance from the origin to ``D`` along the ``delta`` axis
  (``TAdv = min{|delta| : (delta, 0) in D}``), the lateral margin the same along the ``eps`` axis;
* the **signed margin** ``beta`` is the Euclidean distance from the origin to ``D`` in the scaled
  coordinates ``(delta/sigma_delta, eps/sigma_eps)``: positive outside ``D`` (no collision course),
  zero on its boundary and negative inside it (minus the depth of penetration). It is continuous
  through the states A, B and C and, for independent Gaussian disturbances with the given standard
  deviations, ``Phi(-beta)`` is the first-order reliability (Hasofer-Lind) approximation of the
  probability of a collision course; it is exact only when ``D`` is a half-plane.

The scales ``sigma_delta`` (s) and ``sigma_eps`` (m) are data, not constants of the method
(``docs/beta_proposal.md``); the default of 1 only makes the units visible. Everything is within the
prediction horizon ``T``: boundaries produced by the horizon are boundaries of ``D``.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import erfc, sqrt

import numpy as np

from pyssms.geometry import BoolArray, FloatArray, minkowski_halfplanes

__all__ = ["DisturbanceSet", "disturbance_set", "form_probability"]

_EPS_ROW = 1e-12
_TOL = 1e-9


@dataclass(frozen=True)
class DisturbanceSet:
    """Half-planes ``g[..., 0]*delta + g[..., 1]*eps <= h`` of ``D`` for ``N`` encounters.

    Rows are normalised to unit length in ``(delta, eps)``; unused columns have ``g = 0`` and
    ``h = inf``. ``empty`` marks encounters whose disturbed paths never overlap within the horizon.
    """

    g: FloatArray
    h: FloatArray
    empty: BoolArray

    def contains(self, delta: FloatArray, eps: FloatArray, tol: float = _TOL) -> BoolArray:
        """Whether ``(delta, eps)`` (one pair per encounter) lies in ``D``."""
        dl, ep = np.asarray(delta)[:, None], np.asarray(eps)[:, None]
        lhs = self.g[..., 0] * dl + self.g[..., 1] * ep
        inside: BoolArray = np.all(lhs <= self.h + tol, axis=1) & ~self.empty
        return inside

    def axis_margin(self, axis: int) -> FloatArray:
        """Shortest distance from the origin to ``D`` along an axis (``0`` = delta, ``1`` = eps).

        ``0`` if the origin is in ``D``; ``NaN`` if the axis misses ``D`` (state C for the
        ``delta`` axis).
        """
        a = self.g[..., axis]
        pos, neg = a > _EPS_ROW, a < -_EPS_ROW
        with np.errstate(divide="ignore", invalid="ignore"):
            q = self.h / a
        hi = np.min(np.where(pos, q, np.inf), axis=1)
        lo = np.max(np.where(neg, q, -np.inf), axis=1)
        zero_ok = np.all(np.where(~pos & ~neg, self.h >= -_TOL, True), axis=1)
        hit = zero_ok & (lo <= hi + _TOL) & ~self.empty
        bounded = np.isfinite(lo) | np.isfinite(hi)
        nearest = np.where(lo > 0, lo, np.where(hi < 0, -hi, 0.0))
        out: FloatArray = np.where(hit & bounded, nearest, np.nan)
        return out

    def time_margin(self) -> FloatArray:
        """Time Advantage read from ``D`` (s); ``0`` on a collision course, ``NaN`` in state C."""
        return self.axis_margin(0)

    def lateral_margin(self) -> FloatArray:
        """Lateral margin of road user 2 (m); ``0`` on a collision course, ``NaN`` if none."""
        return self.axis_margin(1)

    def signed_margin(
        self, sigma_delta: float = 1.0, sigma_eps: float = 1.0, chunk: int = 2000
    ) -> FloatArray:
        """Signed distance ``beta`` from the origin to ``D`` in scaled coordinates.

        Positive outside ``D``, negative inside, ``NaN`` if ``D`` is empty.
        """
        scale = np.array([sigma_delta, sigma_eps], dtype=float)
        gs = self.g * scale
        norm = np.hypot(gs[..., 0], gs[..., 1])
        live = norm > _EPS_ROW
        gs = np.where(live[..., None], gs / np.where(live, norm, 1.0)[..., None], 0.0)
        hs = np.where(live, self.h / np.where(live, norm, 1.0), np.inf)
        out = np.empty(self.g.shape[0])
        for s in range(0, len(out), chunk):
            e = slice(s, s + chunk)
            out[e] = _signed_distance(gs[e], hs[e], self.empty[e])
        return out

    def vertices(self, index: int = 0) -> FloatArray:
        """Ordered vertices ``(k, 2)`` of ``D`` for one encounter (for plots)."""
        v, feas = _vertices(self.g[index : index + 1], self.h[index : index + 1])
        pts = np.unique(np.round(v[0][feas[0]], 9), axis=0)
        if len(pts) < 3:
            out: FloatArray = pts
            return out
        c = pts.mean(axis=0)
        ordered: FloatArray = pts[np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))]
        return ordered


def _vertices(g: FloatArray, h: FloatArray) -> tuple[FloatArray, BoolArray]:
    m = g.shape[1]
    idx = np.array(list(combinations(range(m), 2)))
    if len(idx) == 0:
        return np.empty((g.shape[0], 0, 2)), np.zeros((g.shape[0], 0), bool)
    i, j = idx[:, 0], idx[:, 1]
    ai, aj = g[:, i, 0], g[:, j, 0]
    ci, cj = g[:, i, 1], g[:, j, 1]
    ri, rj = h[:, i], h[:, j]
    det = ai * cj - aj * ci
    good = (np.abs(det) > 1e-12) & np.isfinite(ri) & np.isfinite(rj)
    sd = np.where(good, det, 1.0)
    with np.errstate(invalid="ignore"):
        x = np.where(good, (ri * cj - rj * ci) / sd, np.nan)
        y = np.where(good, (ai * rj - aj * ri) / sd, np.nan)
        lhs = g[:, None, :, 0] * x[..., None] + g[:, None, :, 1] * y[..., None]
        feas = good & np.all(lhs <= h[:, None, :] + 1e-7, axis=2)
    return np.stack([x, y], axis=-1), feas


def _signed_distance(g: FloatArray, h: FloatArray, empty: BoolArray) -> FloatArray:
    n = g.shape[0]
    depth = np.min(h, axis=1)  # unit rows: distance from the origin to the nearest face
    inside = depth >= -_TOL
    verts, feas = _vertices(g, h)
    count = feas.sum(axis=1)
    feas_any = count > 0
    cx = np.where(feas, verts[..., 0], 0.0).sum(axis=1) / np.maximum(count, 1)
    cy = np.where(feas, verts[..., 1], 0.0).sum(axis=1) / np.maximum(count, 1)
    ang = np.arctan2(
        np.where(feas, verts[..., 1], 0.0) - cy[:, None],
        np.where(feas, verts[..., 0], 0.0) - cx[:, None],
    )
    order = np.argsort(np.where(feas, ang, np.inf), axis=1)
    rows = np.arange(n)[:, None]
    v = np.where(feas[..., None], verts, 0.0)[rows, order]
    p = v.shape[1]
    a, b = v[:, :-1], v[:, 1:]
    seg_ok = np.arange(p - 1)[None, :] + 1 < count[:, None]
    last = v[np.arange(n), np.maximum(count - 1, 0)]
    a = np.concatenate([a, last[:, None, :]], axis=1)
    b = np.concatenate([b, v[:, :1, :]], axis=1)
    seg_ok = np.concatenate([seg_ok, feas_any[:, None]], axis=1)
    ab = b - a
    denom = np.einsum("nkd,nkd->nk", ab, ab)
    tt = np.clip(-np.einsum("nkd,nkd->nk", a, ab) / np.where(denom > 0, denom, 1.0), 0.0, 1.0)
    tt = np.where(denom > 0, tt, 0.0)
    nearest = a + tt[..., None] * ab
    dist = np.where(seg_ok, np.hypot(nearest[..., 0], nearest[..., 1]), np.inf).min(axis=1)
    out = np.where(inside, -np.maximum(depth, 0.0), dist)
    out = np.where(empty | (~inside & ~feas_any), np.nan, out)
    result: FloatArray = np.where(np.isfinite(out), out, np.nan)
    return result


def disturbance_set(
    shape1: FloatArray,
    pos1: FloatArray,
    vel1: FloatArray,
    shape2: FloatArray,
    pos2: FloatArray,
    vel2: FloatArray,
    normal2: FloatArray,
    horizon: float = 10.0,
) -> DisturbanceSet:
    """Disturbance set ``D`` in the ``(delta, eps)`` plane for convex, translating road users.

    Args:
        shape1: Footprint of road user 1 relative to its reference point, ``(N, V, 2)``.
        pos1: Reference point, ``(N, 2)``.
        vel1: Constant velocity, ``(N, 2)``.
        shape2: Footprint of road user 2.
        pos2: Reference point of road user 2.
        vel2: Velocity of road user 2.
        normal2: Unit vector ``(N, 2)`` along which road user 2 is shifted by ``eps`` (shifting
            road user 1 along ``u`` is the same as shifting road user 2 along ``-u``).
        horizon: Prediction horizon ``T`` (s); both clocks stay in ``[0, T]``.

    Returns:
        :class:`DisturbanceSet`.
    """
    normals, b = minkowski_halfplanes(shape1, shape2)
    n = normals.shape[0]
    a = np.einsum("nkd,nd->nk", normals, vel2 - vel1)  # t
    p = -np.einsum("nkd,nd->nk", normals, vel1)  # delta
    q = np.einsum("nkd,nd->nk", normals, normal2)  # eps
    r = b - np.einsum("nkd,nd->nk", normals, pos2 - pos1)
    box = np.array(
        [
            [-1.0, 0.0, 0.0, 0.0],
            [-1.0, -1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, horizon],
            [1.0, 1.0, 0.0, horizon],
        ]
    )  # t >= 0, t + delta >= 0, t <= T, t + delta <= T
    a = np.concatenate([a, np.tile(box[:, 0], (n, 1))], axis=1)
    p = np.concatenate([p, np.tile(box[:, 1], (n, 1))], axis=1)
    q = np.concatenate([q, np.tile(box[:, 2], (n, 1))], axis=1)
    r = np.concatenate([r, np.tile(box[:, 3], (n, 1))], axis=1)
    nrm = np.sqrt(a * a + p * p + q * q)
    flat = nrm < _EPS_ROW
    empty = np.any(flat & (r < -_TOL), axis=1)
    safe = np.where(flat, 1.0, nrm)
    a, p, q, r = a / safe, p / safe, q / safe, r / safe
    m = a.shape[1]
    pos_row = ~flat & (a > _EPS_ROW)
    neg_row = ~flat & (a < -_EPS_ROW)
    zero_row = ~flat & ~pos_row & ~neg_row
    grid = np.meshgrid(np.arange(m), np.arange(m), indexing="ij")
    ii, jj = grid[0].ravel(), grid[1].ravel()
    wu, wl = -a[:, jj], a[:, ii]  # |a_lower|, a_upper
    pair_ok = pos_row[:, ii] & neg_row[:, jj]
    gp = np.concatenate([p, p[:, ii] * wu + p[:, jj] * wl], axis=1)
    gq = np.concatenate([q, q[:, ii] * wu + q[:, jj] * wl], axis=1)
    gr = np.concatenate([r, r[:, ii] * wu + r[:, jj] * wl], axis=1)
    keep = np.concatenate([zero_row, pair_ok], axis=1)
    gn = np.hypot(gp, gq)
    degenerate = keep & (gn < _EPS_ROW)
    empty = empty | np.any(degenerate & (gr < -_TOL), axis=1)
    keep &= gn >= _EPS_ROW
    gn = np.where(keep, gn, 1.0)
    gp, gq, gr = gp / gn, gq / gn, gr / gn
    order = np.argsort(~keep, axis=1, kind="stable")
    width = max(int(keep.sum(axis=1).max()), 1)
    take = order[:, :width]
    rows = np.arange(n)[:, None]
    ok = keep[rows, take]
    g = np.stack([np.where(ok, gp[rows, take], 0.0), np.where(ok, gq[rows, take], 0.0)], axis=-1)
    h = np.where(ok, gr[rows, take], np.inf)
    return DisturbanceSet(g=g, h=h, empty=empty)


def form_probability(beta: FloatArray) -> FloatArray:
    """First-order reliability approximation ``Phi(-beta)`` of a collision-course probability.

    Exact for a half-plane ``D`` with independent Gaussian disturbances of the scales used to
    compute ``beta``; an approximation for the polygon ``D`` in general (``NaN`` stays ``NaN``).
    """
    b = np.asarray(beta, dtype=float)
    flat = b.ravel()
    vals = np.array([np.nan if np.isnan(x) else 0.5 * erfc(x / sqrt(2.0)) for x in flat])
    out: FloatArray = vals.reshape(b.shape)
    return out
