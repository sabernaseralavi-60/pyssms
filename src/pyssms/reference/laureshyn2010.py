"""Reference implementation of Appendix A of Laureshyn, Svensson and Hydén (2010).

This module follows the paper's own procedure, independently of :mod:`pyssms.timetime`:
every corner of one road user is tested against every side of the other (4 x 4 x 2 = 32
corner-side combinations for two rectangles) and the lowest value is kept.

* A.1, TTC: Eqs. (6)-(10). The slope form ``k`` of Eq. (7) is used, with Eq. (9) when the
  side is vertical, and the in-section test of Eq. (10). Eq. (10) is printed with ``x2``/``y2``
  in its second lines (in the 2010 thesis as well as in the journal preprint); we read them as
  ``x_ln2``/``y_ln2``. Only positive times are kept. ``tol`` widens the in-section test;
  ``tol=0`` is the printed test (exact floating-point comparison).
* Eqs. (8) and (9) carry a leading minus sign in the author's 2010 thesis (Appendix, p. 138) and
  are correct; the minus sign is absent from the "article in press" PDF of the journal paper.
  The default here is the thesis form; ``as_printed=True`` evaluates the preprint form.
* A.2, TAdv, T2 and TG: Eqs. (11)-(12). The "common points" are where the corner's path meets
  the paths of the side's ends; the special cases of Fig. 11 (a time equal to zero) are read
  as: the corner's path enters or leaves the region swept by the side through the side's
  present position (``t_ln = 0``), or the corner is inside that region now (``t_p = 0``).
  Equivalently, for ``lambda`` along the side, the arrival times ``t_p(lambda)`` and
  ``t_ln(lambda)`` are affine, and the procedure evaluates them at the ends of the interval of
  ``lambda`` where both are non-negative.

Interpretations that the printed text leaves open are listed in ``docs/methods.md``. Cases the
appendix does not cover (parallel paths of a corner and a side, a road user standing still)
are returned as ``NaN`` with ``covered=False``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pyssms.geometry import BoolArray, FloatArray, IntArray

__all__ = ["ReferenceResult", "appendix_a"]


@dataclass(frozen=True)
class ReferenceResult:
    """Indicators from the 32 corner-side combinations (``NaN`` where undefined)."""

    ttc: FloatArray
    tadv: FloatArray
    t2: FloatArray
    tg: FloatArray
    first: IntArray
    covered: BoolArray


def _ttc_a1(
    p: FloatArray,
    vp: FloatArray,
    e1: FloatArray,
    e2: FloatArray,
    vl: FloatArray,
    tol: float,
    as_printed: bool,
) -> FloatArray:
    """Eqs. (6)-(10): time when a moving point crosses a moving line section.

    Substituting Eq. (4) into Eq. (6) gives ``t = -[(y_p - y_ln1) - k (x_p - x_ln1)] / den``,
    the form printed in the 2010 thesis. The "article in press" PDF of the journal paper omits
    the leading minus sign (with ``x' = x + v t`` that form returns ``-t``);
    ``as_printed=True`` evaluates that preprint form.
    """
    xp, yp = p[:, 0], p[:, 1]
    x1, y1, x2, y2 = e1[:, 0], e1[:, 1], e2[:, 0], e2[:, 1]
    vertical = x2 == x1
    sign = 1.0 if as_printed else -1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        k = (y2 - y1) / (x2 - x1)  # Eq. (7)
        den_k = (vp[:, 1] - vl[:, 1]) - k * (vp[:, 0] - vl[:, 0])
        t_k = sign * ((yp - y1) - k * (xp - x1)) / den_k  # Eq. (8)
        den_v = vp[:, 0] - vl[:, 0]
        t_v = sign * (xp - x1) / den_v  # Eq. (9)
    t = np.where(vertical, t_v, t_k)
    t = np.where(np.isfinite(t) & (t > 0), t, np.nan)
    tt = np.where(np.isfinite(t), t, 0.0)
    pxt, pyt = xp + vp[:, 0] * tt, yp + vp[:, 1] * tt
    ax, ay = x1 + vl[:, 0] * tt, y1 + vl[:, 1] * tt
    bx, by = x2 + vl[:, 0] * tt, y2 + vl[:, 1] * tt
    in_x = (np.minimum(ax, bx) - tol <= pxt) & (pxt <= np.maximum(ax, bx) + tol)  # Eq. (10)
    in_y = (np.minimum(ay, by) - tol <= pyt) & (pyt <= np.maximum(ay, by) + tol)
    out: FloatArray = np.where(in_x & in_y, t, np.nan)
    return out


def _times_a2(
    p: FloatArray, vp: FloatArray, e1: FloatArray, e2: FloatArray, vl: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, BoolArray]:
    """Arrival times of point and side at the two common points (Eq. 11 and Fig. 11).

    Returns ``(tp_lo, tl_lo, tp_hi, tl_hi, covered)``; times are ``NaN`` where the corner's
    path never meets the region swept by the side.
    """
    det = -vp[:, 0] * vl[:, 1] + vl[:, 0] * vp[:, 1]
    # parallel paths (relative tolerance) or a standing road user: no common points
    covered = np.abs(det) > 1e-9 * np.hypot(*vp.T) * np.hypot(*vl.T)
    sdet = np.where(covered, det, 1.0)

    def solve(bx: FloatArray, by: FloatArray) -> tuple[FloatArray, FloatArray]:
        tp = (-vl[:, 1] * bx + vl[:, 0] * by) / sdet
        tl = (-vp[:, 1] * bx + vp[:, 0] * by) / sdet
        return tp, tl

    b0 = e1 - p
    u = e2 - e1
    tp0, tl0 = solve(b0[:, 0], b0[:, 1])
    tp1, tl1 = solve(u[:, 0], u[:, 1])  # slope in lambda
    lo: FloatArray = np.zeros(len(p))
    hi: FloatArray = np.ones(len(p))
    for t0, t1 in ((tp0, tp1), (tl0, tl1)):  # t0 + lambda * t1 >= 0
        with np.errstate(divide="ignore", invalid="ignore"):
            root = -t0 / t1
        lo = np.where(t1 > 0, np.maximum(lo, root), lo)
        hi = np.where(t1 < 0, np.minimum(hi, root), hi)
        never = (t1 == 0) & (t0 < 0)
        lo = np.where(never, np.inf, lo)
    exists = covered & (lo <= hi)
    nan = np.full(len(p), np.nan)
    lo = np.where(exists, lo, 0.0)
    hi = np.where(exists, hi, 0.0)
    tp_lo = np.where(exists, np.maximum(tp0 + lo * tp1, 0.0), nan)
    tl_lo = np.where(exists, np.maximum(tl0 + lo * tl1, 0.0), nan)
    tp_hi = np.where(exists, np.maximum(tp0 + hi * tp1, 0.0), nan)
    tl_hi = np.where(exists, np.maximum(tl0 + hi * tl1, 0.0), nan)
    return tp_lo, tl_lo, tp_hi, tl_hi, covered


def appendix_a(
    corners1: FloatArray,
    vel1: FloatArray,
    corners2: FloatArray,
    vel2: FloatArray,
    tol: float = 0.0,
    as_printed: bool = False,
) -> ReferenceResult:
    """Indicators by the 32 corner-side combinations of Appendix A.

    Args:
        corners1: Absolute corners ``(N, 4, 2)`` of road user 1 in order around the body.
        vel1: Velocity ``(N, 2)``.
        corners2: Absolute corners of road user 2.
        vel2: Velocity of road user 2.
        tol: Tolerance of the in-section test of Eq. (10); 0 reproduces the printed test.
        as_printed: Use Eqs. (8)-(9) as in the journal preprint, without the minus sign
            printed in the thesis (see ``_ttc_a1``).
    """
    n = corners1.shape[0]
    inf: FloatArray = np.full(n, np.inf)
    ttc: FloatArray = inf.copy()
    best_gap: FloatArray = inf.copy()
    best_t2: FloatArray = inf.copy()
    best_first: IntArray = np.zeros(n, dtype=int)
    tg: FloatArray = inf.copy()
    covered = np.ones(n, dtype=bool)
    for a_c, a_v, b_c, b_v, a_is_1 in (
        (corners1, vel1, corners2, vel2, True),
        (corners2, vel2, corners1, vel1, False),
    ):
        nb = b_c.shape[1]
        for ci in range(a_c.shape[1]):
            for sj in range(nb):
                p = a_c[:, ci]
                e1, e2 = b_c[:, sj], b_c[:, (sj + 1) % nb]
                t = _ttc_a1(p, a_v, e1, e2, b_v, tol, as_printed)
                ttc = np.fmin(ttc, t)
                tp_lo, tl_lo, tp_hi, tl_hi, cov = _times_a2(p, a_v, e1, e2, b_v)
                covered &= cov
                d_lo, d_hi = tp_lo - tl_lo, tp_hi - tl_hi
                crossing = d_lo * d_hi <= 0  # collision course for this pair
                for tp, tl in ((tp_lo, tl_lo), (tp_hi, tl_hi)):
                    gap = np.abs(tp - tl)
                    later = np.maximum(tp, tl)
                    tg = np.fmin(tg, later)  # Eq. (12)
                    better = (gap < best_gap - 1e-9) | (
                        (np.abs(gap - best_gap) <= 1e-9) & (later < best_t2)
                    )
                    better &= np.isfinite(gap) & ~crossing
                    best_gap = np.where(better, gap, best_gap)
                    best_t2 = np.where(better, later, best_t2)
                    point_first = tp < tl
                    first = np.where(point_first == a_is_1, 1, 2)
                    best_first = np.where(better, first, best_first)
    ttc = np.where(np.isfinite(ttc), ttc, np.nan)
    on_course = np.isfinite(ttc)
    tg = np.where(on_course, np.fmin(tg, ttc), tg)
    tadv = np.where(on_course, 0.0, best_gap)
    t2 = np.where(on_course, ttc, best_t2)
    first_out = np.where(on_course, 0, best_first)
    clean = [np.where(np.isfinite(v), v, np.nan) for v in (tadv, t2, tg)]
    return ReferenceResult(
        ttc=ttc, tadv=clean[0], t2=clean[1], tg=clean[2], first=first_out, covered=covered
    )
