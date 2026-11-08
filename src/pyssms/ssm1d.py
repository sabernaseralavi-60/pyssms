r"""Car-following surrogate safety measures of Naseralavi et al. (2025, Future Transportation 5:86).

The ten measures of Table 1 of that paper, written from the motion "story" each one assumes (the
L/F/T coding of its Table 4) and **derived from those definitions**, not copied from the printed
equations (several printed forms could not be checked, see ``docs/ssm1d_notes.md``).

Conventions: the leader L is ahead of the follower F on the same path. ``gap`` is the clear
distance between the rear of L and the front of F (m, >= 0). Speeds are in m/s, accelerations and
jerks signed (m/s^2, m/s^3); ``dec_*`` are positive deceleration magnitudes. All functions are
vectorised.

=======  =====================  ===========================================================
measure  code (leader/follower)  definition used here
=======  =====================  ===========================================================
TTC1     L21/F11/T1             first root of the gap with constant speeds
TTC2     L22/F12/T1             ... with constant accelerations
TTC3     L23/F13/T1             ... with constant jerks
TTCD     L3/F11/T1              leader brakes at ``dec_l`` until it stops, follower keeps speed
SDI      L3/F32/T2              1 if the follower's stopping position (reaction ``t_r``, then
                                ``dec_f``) reaches the leader's rear stopping position
DRAC     L21/F21/T3             constant deceleration, applied at once, that stops the closing
PSD      L1/F22/T4              gap / (v_f^2 / (2 dec_f))
MDRAC    L21/F31/T3             DRAC with a reaction time ``r`` at the closing speed
MPSD     L1/F32/T4              gap / (v_f r + v_f^2 / (2 dec_f))
DCIA     L22/F31/T3             constant deceleration after the reaction time ``r`` (follower
                                accelerates at ``a_f`` before) that matches speeds at contact
=======  =====================  ===========================================================

Distance-based and ratio-based measures use the *follower's own speed* as the approach speed in PSD
and MPSD (our reading); the paper's printed Eq. (8) agrees with this only if its TTC means
``gap / v_f``.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from pyssms.geometry import FloatArray

__all__ = [
    "dcia",
    "drac",
    "mdrac",
    "mpsd",
    "psd",
    "sdi",
    "ttc_poly",
    "ttcd",
]


def _arr(x: ArrayLike) -> FloatArray:
    return np.atleast_1d(np.asarray(x, dtype=float))


def _first_positive_root(
    c0: FloatArray, c1: FloatArray, c2: FloatArray, c3: FloatArray
) -> FloatArray:
    """Smallest positive real root of ``c0 + c1 t + c2 t^2 + c3 t^3`` (``NaN`` if none)."""
    c0, c1, c2, c3 = np.broadcast_arrays(c0, c1, c2, c3)
    out = np.full(c0.shape, np.nan)
    eps = 1e-12
    for i in range(c0.size):
        coef = np.array([c3.flat[i], c2.flat[i], c1.flat[i], c0.flat[i]])
        if abs(coef[3]) <= eps:  # no constant term: root at 0 (collision already)
            out.flat[i] = 0.0
            continue
        roots = np.roots(coef) if np.any(np.abs(coef[:3]) > eps) else np.array([])
        real = roots[np.abs(roots.imag) < 1e-9].real
        pos = real[real > 0]
        if pos.size:
            out.flat[i] = float(np.min(pos))
    return out


def ttc_poly(
    gap: ArrayLike,
    v_l: ArrayLike,
    v_f: ArrayLike,
    a_l: ArrayLike = 0.0,
    a_f: ArrayLike = 0.0,
    j_l: ArrayLike = 0.0,
    j_f: ArrayLike = 0.0,
) -> FloatArray:
    """TTC1 (default), TTC2 (accelerations) or TTC3 (jerks): first time the gap closes.

    ``gap(t) = gap + (v_l - v_f) t + (a_l - a_f) t^2 / 2 + (j_l - j_f) t^3 / 6``. As in the paper
    the stories ignore that a road user cannot reverse; a collision that needs a negative speed is
    still returned. ``NaN`` if the gap never closes.
    """
    g, vl, vf, al, af, jl, jf = (_arr(x) for x in (gap, v_l, v_f, a_l, a_f, j_l, j_f))
    return _first_positive_root(g, vl - vf, (al - af) / 2.0, (jl - jf) / 6.0)


def ttcd(gap: ArrayLike, v_l: ArrayLike, v_f: ArrayLike, dec_l: ArrayLike) -> FloatArray:
    """TTC with disturbance: leader brakes at ``dec_l`` until it stops, follower keeps ``v_f``.

    ``NaN`` if the follower never reaches the leader (it stands still behind a stopped leader).
    """
    g, vl, vf, d = (_arr(x) for x in (gap, v_l, v_f, dec_l))
    t_stop = np.where(d > 0, vl / np.where(d > 0, d, 1.0), np.inf)
    # while the leader moves: g + (vl - vf) t - d t^2 / 2 = 0
    t1 = _first_positive_root(g, vl - vf, -d / 2.0, np.zeros_like(g))
    # after it stopped: follower reaches the stopped leader
    stopped_gap = g + np.where(d > 0, vl**2 / (2 * np.where(d > 0, d, 1.0)), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        t2 = np.where(vf > 0, stopped_gap / vf, np.nan)
    out: FloatArray = np.where(np.isfinite(t1) & (t1 <= t_stop), t1, t2)
    return out


def drac(gap: ArrayLike, v_l: ArrayLike, v_f: ArrayLike) -> FloatArray:
    """Deceleration (m/s^2, positive) that, applied at once, removes the closing speed in time."""
    g, vl, vf = (_arr(x) for x in (gap, v_l, v_f))
    closing = np.maximum(vf - vl, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        out: FloatArray = np.where(g > 0, closing**2 / (2 * g), np.where(closing > 0, np.inf, 0.0))
    return out


def mdrac(gap: ArrayLike, v_l: ArrayLike, v_f: ArrayLike, reaction: ArrayLike) -> FloatArray:
    """DRAC with a reaction time: the closing speed continues for ``reaction`` seconds first.

    ``d = dv^2 / (2 (gap - dv r))`` which equals ``dv / (2 (TTC1 - r))``; ``inf`` if the gap is
    already closed before the reaction ends.
    """
    g, vl, vf, r = (_arr(x) for x in (gap, v_l, v_f, reaction))
    closing = np.maximum(vf - vl, 0.0)
    left = g - closing * r
    with np.errstate(divide="ignore", invalid="ignore"):
        out: FloatArray = np.where(
            closing == 0, 0.0, np.where(left > 0, closing**2 / (2 * left), np.inf)
        )
    return out


def psd(gap: ArrayLike, v_f: ArrayLike, dec_f: ArrayLike) -> FloatArray:
    """Proportion of stopping distance: ``gap / (v_f^2 / (2 dec_f))`` (< 1: cannot stop in time)."""
    g, vf, d = (_arr(x) for x in (gap, v_f, dec_f))
    msd = vf**2 / (2 * d)
    with np.errstate(divide="ignore", invalid="ignore"):
        out: FloatArray = np.where(msd > 0, g / msd, np.inf)
    return out


def mpsd(gap: ArrayLike, v_f: ArrayLike, dec_f: ArrayLike, reaction: ArrayLike) -> FloatArray:
    """PSD with the distance travelled during the reaction time added to the stopping distance."""
    g, vf, d, r = (_arr(x) for x in (gap, v_f, dec_f, reaction))
    msd = vf * r + vf**2 / (2 * d)
    with np.errstate(divide="ignore", invalid="ignore"):
        out: FloatArray = np.where(msd > 0, g / msd, np.inf)
    return out


def sdi(
    gap: ArrayLike,
    v_l: ArrayLike,
    v_f: ArrayLike,
    dec_l: ArrayLike,
    dec_f: ArrayLike,
    reaction: ArrayLike,
) -> FloatArray:
    """Stopping distance index: 1 (unsafe) if the follower cannot stop behind the stopping leader.

    The leader brakes at ``dec_l`` at once; the follower reacts after ``reaction`` and then brakes
    at ``dec_f``. Unsafe when the follower's front stopping position reaches the leader's rear
    stopping position: ``v_f r + v_f^2 / (2 dec_f) > gap + v_l^2 / (2 dec_l)``.
    """
    g, vl, vf, dl, df, r = (_arr(x) for x in (gap, v_l, v_f, dec_l, dec_f, reaction))
    follower = vf * r + vf**2 / (2 * df)
    leader = g + vl**2 / (2 * dl)
    out: FloatArray = (follower > leader).astype(float)
    return out


def dcia(
    gap: ArrayLike,
    v_l: ArrayLike,
    v_f: ArrayLike,
    a_l: ArrayLike,
    a_f: ArrayLike,
    reaction: ArrayLike,
) -> tuple[FloatArray, FloatArray]:
    """Deceleration to avoid a crash with initial acceleration (Fazekas et al. 2017 story L22/F31).

    The leader keeps its acceleration ``a_l``. The follower keeps its acceleration ``a_f`` during
    the reaction time ``r`` and then brakes at a constant rate ``dec`` so that the speeds are equal
    at the moment the gap closes (a touch, no crash). With ``s = T - r``, ``v_r = v_f + a_f r``:

    * speeds equal at ``T``:  ``dec s = v_r - v_l - a_l T``;
    * gap closed at ``T``:  ``x_r + s (v_r + v_l + a_l T) / 2 = gap + v_l T + a_l T^2 / 2``,
      where the ``a_l T^2 / 2`` terms cancel, so ``T`` is linear:
      ``T = (2 gap - (v_f - v_l) r) / ((v_f - v_l) + (a_f - a_l) r)``.

    Returns:
        ``(dec, T)``: the deceleration (positive; ``NaN`` where no such braking exists, e.g. the
        relative speed after the reaction is not positive) and the contact time.
    """
    g, vl, vf, al, af, r = (_arr(x) for x in (gap, v_l, v_f, a_l, a_f, reaction))
    v_r = vf + af * r
    den = (vf - vl) + (af - al) * r
    with np.errstate(divide="ignore", invalid="ignore"):
        big_t = np.where(den > 1e-12, (2 * g - (vf - vl) * r) / den, np.nan)
        s = big_t - r
        dec = np.where(s > 0, (v_r - vl - al * big_t) / np.where(s > 0, s, 1.0), np.nan)
    ok = (s > 0) & (dec >= 0)
    return np.where(ok, dec, np.nan), np.where(ok, big_t, np.nan)
