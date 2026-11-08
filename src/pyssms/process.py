"""Encounter processing: from trajectories to indicator time series and per-encounter summaries.

For every pair of road users that come close, the indicators of :mod:`pyssms.timetime` are
computed at each common time stamp from the *current* centre, heading, velocity and body size
(constant-velocity prediction, bodies translate without rotating: the assumption of the package),
giving an :class:`Encounter`. On top of that this module provides

* :func:`observed_pet`: Post-Encroachment Time **observed** in the realised trajectories;
* :func:`tet_tit`: the aggregate Time-Exposed and Time-Integrated measures of Minderhoud and Bovy
  (2001) for any indicator series (TTC by default);
* :func:`braking_onset` and :func:`swedish_pair`: the pair ``(TA, v_conf)`` of the Swedish Traffic
  Conflict Technique (Hyden, 1987): time-to-accident and speed at the start of the evasive action;
* :func:`conflict_type`: crossing / rear-end / lane-change classification by the angle between
  the headings (limits are a configurable convention, see the docstring).

Definitions chosen here that are not unique in the literature are stated in each docstring.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from pyssms.geometry import BoolArray, FloatArray, IntArray, StrArray, rectangle
from pyssms.timetime import indicators_rect
from pyssms.trajectories import Trajectories

__all__ = [
    "Encounter",
    "braking_onset",
    "candidate_pairs",
    "conflict_type",
    "HYDEN_ZONE_WIDTH",
    "hyden_braking_limit",
    "hyden_serious_conflict",
    "hyden_severity_zone",
    "hyden_uniform_severity_ta",
    "hyden_zone_offset",
    "encounters",
    "observed_pet",
    "pair_series",
    "swedish_pair",
    "tet_tit",
]


@dataclass(frozen=True)
class Encounter:
    """Indicator time series of one pair of road users over their common observation time.

    Attributes:
        a: Id of road user 1.
        b: Id of road user 2.
        t: Common time stamps (s).
        distance: Centre-to-centre distance (m).
        ttc: Time-to-Collision (s; NaN unless on a collision course).
        tadv: Time Advantage (s).
        t2: Arrival time of the second road user at the (avoided) collision point (s).
        tg: Time Gap (s).
        state: ``'A'``/``'B'``/``'C'`` per time stamp (collision / crossing / no overlap).
        angle: Angle between the two headings (rad, 0 to pi).
        vel_a: Velocity of road user 1, ``(n, 2)`` (m/s).
        vel_b: Velocity of road user 2, ``(n, 2)`` (m/s).
    """

    a: int
    b: int
    t: FloatArray
    distance: FloatArray
    ttc: FloatArray
    tadv: FloatArray
    t2: FloatArray
    tg: FloatArray
    state: StrArray
    angle: FloatArray
    vel_a: FloatArray
    vel_b: FloatArray

    @property
    def speed_a(self) -> FloatArray:
        """Speed of road user 1 (m/s)."""
        out: FloatArray = np.hypot(self.vel_a[:, 0], self.vel_a[:, 1])
        return out

    @property
    def speed_b(self) -> FloatArray:
        """Speed of road user 2 (m/s)."""
        out: FloatArray = np.hypot(self.vel_b[:, 0], self.vel_b[:, 1])
        return out

    def min_ttc(self) -> float:
        """Smallest TTC over the encounter (NaN if never on a collision course)."""
        return float(np.nanmin(self.ttc)) if np.isfinite(self.ttc).any() else float("nan")

    def min_tadv(self) -> float:
        """Smallest Time Advantage over the encounter (NaN if never defined)."""
        return float(np.nanmin(self.tadv)) if np.isfinite(self.tadv).any() else float("nan")

    def min_t2(self) -> float:
        """Smallest T2 over the encounter (NaN if never defined)."""
        return float(np.nanmin(self.t2)) if np.isfinite(self.t2).any() else float("nan")

    def min_distance(self) -> float:
        """Smallest centre distance (m)."""
        return float(np.min(self.distance))


def _by_user(traj: Trajectories) -> dict[int, IntArray]:
    order = np.lexsort((traj.t, traj.uid))
    us = traj.uid[order]
    starts = np.flatnonzero(np.r_[True, us[1:] != us[:-1]])
    stops = np.r_[starts[1:], us.size]
    return {int(us[s]): order[s:e] for s, e in zip(starts, stops, strict=True)}


def _segment_distance(p1: FloatArray, d1: FloatArray, p2: FloatArray, d2: FloatArray) -> FloatArray:
    """Smallest distance between the segments ``p1 + s d1`` and ``p2 + u d2`` (s, u in [0, 1]).

    Vectorised closest-points-of-two-segments computation; degenerate (zero-length) segments are
    handled as points.
    """
    r = p1 - p2
    a = np.einsum("nd,nd->n", d1, d1)
    e = np.einsum("nd,nd->n", d2, d2)
    f = np.einsum("nd,nd->n", d2, r)
    c = np.einsum("nd,nd->n", d1, r)
    b = np.einsum("nd,nd->n", d1, d2)
    denom = a * e - b * b
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.where(denom > 1e-12, np.clip((b * f - c * e) / denom, 0.0, 1.0), 0.0)
        s = np.where(a > 1e-12, s, 0.0)
        u = np.where(e > 1e-12, (b * s + f) / e, 0.0)
        u_c = np.clip(u, 0.0, 1.0)
        s = np.where(a > 1e-12, np.clip((b * u_c - c) / a, 0.0, 1.0), 0.0)
        u = np.where(e > 1e-12, np.clip((b * s + f) / e, 0.0, 1.0), 0.0)
    diff = (p1 + s[:, None] * d1) - (p2 + u[:, None] * d2)
    out: FloatArray = np.hypot(diff[:, 0], diff[:, 1])
    return out


def candidate_pairs(
    traj: Trajectories,
    max_distance: float = 30.0,
    min_overlap: float = 0.5,
    horizon: float = 10.0,
    reach: float = 6.0,
    scan_dt: float = 0.2,
) -> list[tuple[int, int]]:
    """Pairs of road users that could be in an encounter.

    At a scanned time stamp a pair qualifies if their centres are within ``max_distance`` **or**
    their *future straight paths* (each road user's centre moving at its current velocity for
    ``horizon`` seconds) come within ``reach`` metres of each other. The second rule keeps pairs
    that pass the same place seconds apart, which a distance rule alone would miss. A pair is a
    candidate if it qualifies for at least ``min_overlap`` seconds in total.

    Args:
        traj: Trajectories.
        max_distance: Centre-to-centre distance (m) that makes a pair qualify.
        min_overlap: Minimum total qualifying time (s).
        horizon: Length of the future paths (s).
        reach: Distance (m) between the future paths that makes a pair qualify (a little more than
            the sum of the half-diagonals of two vehicles).
        scan_dt: Time stamps are scanned at about this spacing (s).

    Returns:
        Sorted list of ``(a, b)`` with ``a < b``.
    """
    ts = traj.times
    key = np.searchsorted(ts, traj.t)  # time-stamp index of each row (times are exact floats)
    order = np.argsort(key, kind="stable")
    bounds = np.searchsorted(key[order], np.arange(ts.size + 1))
    dt = traj.dt if np.isfinite(traj.dt) else 1.0
    step = max(1, int(round(scan_dt / dt)))
    count: dict[tuple[int, int], int] = {}
    for k in range(0, ts.size, step):
        rows = order[bounds[k] : bounds[k + 1]]
        if rows.size < 2:
            continue
        i, j = np.triu_indices(rows.size, k=1)
        ri, rj = rows[i], rows[j]
        p1 = np.stack([traj.x[ri], traj.y[ri]], -1)
        p2 = np.stack([traj.x[rj], traj.y[rj]], -1)
        near = np.hypot(*(p1 - p2).T) <= max_distance
        d1 = np.stack([traj.vx[ri], traj.vy[ri]], -1) * horizon
        d2 = np.stack([traj.vx[rj], traj.vy[rj]], -1) * horizon
        ok = near | (_segment_distance(p1, d1, p2, d2) <= reach)
        for u, v in zip(traj.uid[ri[ok]], traj.uid[rj[ok]], strict=True):
            pair = (int(min(u, v)), int(max(u, v)))
            count[pair] = count.get(pair, 0) + 1
    return sorted(pair for pair, c in count.items() if c * step * dt >= min_overlap)


def pair_series(
    traj: Trajectories,
    a: int,
    b: int,
    horizon: float = 10.0,
    index: dict[int, IntArray] | None = None,
) -> Encounter | None:
    """Indicator series of the pair ``(a, b)`` at their common time stamps (``None`` if none)."""
    idx = index if index is not None else _by_user(traj)
    ra, rb = idx.get(a), idx.get(b)
    if ra is None or rb is None:
        return None
    common, ia, ib = np.intersect1d(traj.t[ra], traj.t[rb], return_indices=True)
    if common.size == 0:
        return None
    ra, rb = ra[ia], rb[ib]
    ind = indicators_rect(
        traj.x[ra], traj.y[ra], traj.heading[ra], traj.vx[ra], traj.vy[ra],
        traj.length[ra], traj.width[ra],
        traj.x[rb], traj.y[rb], traj.heading[rb], traj.vx[rb], traj.vy[rb],
        traj.length[rb], traj.width[rb], horizon,
    )  # fmt: skip
    dh = np.abs(np.angle(np.exp(1j * (traj.heading[ra] - traj.heading[rb]))))
    return Encounter(
        a=a, b=b, t=common,
        distance=np.hypot(traj.x[ra] - traj.x[rb], traj.y[ra] - traj.y[rb]),
        ttc=ind.ttc, tadv=ind.tadv, t2=ind.t2, tg=ind.tg, state=ind.state, angle=dh,
        vel_a=np.stack([traj.vx[ra], traj.vy[ra]], -1),
        vel_b=np.stack([traj.vx[rb], traj.vy[rb]], -1),
    )  # fmt: skip


def encounters(
    traj: Trajectories,
    horizon: float = 10.0,
    max_distance: float = 30.0,
    min_overlap: float = 0.5,
    pairs: list[tuple[int, int]] | None = None,
) -> list[Encounter]:
    """Indicator series for all candidate pairs (see :func:`candidate_pairs`; ``horizon`` is used).

    Pairs of road users with zero body size are skipped (the indicators need a footprint).
    """
    idx = _by_user(traj)
    todo = (
        pairs
        if pairs is not None
        else candidate_pairs(traj, max_distance, min_overlap, horizon=horizon)
    )
    size_ok = {u: bool(traj.length[r[0]] > 0 and traj.width[r[0]] > 0) for u, r in idx.items()}
    out = []
    for a, b in todo:
        if not (size_ok.get(a) and size_ok.get(b)):
            continue
        e = pair_series(traj, a, b, horizon, idx)
        if e is not None:
            out.append(e)
    return out


# --------------------------------------------------------------------------- observed PET


def _sat_overlap(
    a_xy: FloatArray, a_h: FloatArray, a_l: float, a_w: float,
    b_xy: FloatArray, b_h: FloatArray, b_l: float, b_w: float,
) -> BoolArray:  # fmt: skip
    """Overlap matrix ``(na, nb)`` of two sets of rectangles (separating-axis test)."""
    ca = rectangle(a_h, a_l, a_w) + a_xy[:, None, :]  # (na, 4, 2)
    cb = rectangle(b_h, b_l, b_w) + b_xy[:, None, :]  # (nb, 4, 2)
    hit = np.ones((a_xy.shape[0], b_xy.shape[0]), dtype=bool)
    for ang in (a_h, a_h + np.pi / 2):  # the two face axes of each rectangle of set a
        ax = np.stack([np.cos(ang), np.sin(ang)], -1)
        pa = np.einsum("nd,nvd->nv", ax, ca)
        pb = np.einsum("nd,mvd->nmv", ax, cb)
        hit &= (pa.max(-1)[:, None] >= pb.min(-1)) & (pb.max(-1) >= pa.min(-1)[:, None])
    for ang in (b_h, b_h + np.pi / 2):  # ... and of set b
        ax = np.stack([np.cos(ang), np.sin(ang)], -1)
        pb = np.einsum("md,mvd->mv", ax, cb)
        pa = np.einsum("md,nvd->nmv", ax, ca)
        hit &= (pa.max(-1) >= pb.min(-1)[None, :]) & (pb.max(-1)[None, :] >= pa.min(-1))
    return hit


def observed_pet(traj: Trajectories, a: int, b: int) -> dict[str, float | int]:
    """Post-Encroachment Time **observed** in the realised trajectories of road users a and b.

    The bodies are rotating rectangles at their recorded poses. A frame of road user ``k`` is
    *inside the conflict area* when its footprint overlaps the footprint of the other road user at
    some frame (the conflict area is thus the set of places where the realised bodies of both
    overlap, approximated by the frames at which that happens). Road user ``k`` occupies the area
    from its first to its last such frame. If road user 1 leaves before road user 2 arrives, the
    PET is ``arrival_2 - departure_1`` (and symmetrically). If the two occupation intervals
    overlap in time the bodies were in the same place at the same time: ``pet`` is 0 and
    ``collision`` is 1 (a geometric overlap of the recorded bodies, which with drone data
    usually reflects box-size error as much as a crash).

    Resolution is one frame interval; the PET is a multiple of it up to the interval between the
    last/first frames.

    Returns:
        Dict with ``pet`` (s; NaN if the footprints never overlap), ``first`` (id that passes
        first), ``collision`` (0/1) and ``t_enter_a/b``, ``t_exit_a/b`` (s).
    """
    ta, tb = traj.track(a), traj.track(b)
    nan = float("nan")
    out: dict[str, float | int] = {
        "pet": nan, "first": -1, "collision": 0,
        "t_enter_a": nan, "t_exit_a": nan, "t_enter_b": nan, "t_exit_b": nan,
    }  # fmt: skip
    if len(ta) == 0 or len(tb) == 0:
        return out
    la, wa = float(np.median(ta.length)), float(np.median(ta.width))
    lb, wb = float(np.median(tb.length)), float(np.median(tb.width))
    if min(la, wa, lb, wb) <= 0:
        return out
    hit = _sat_overlap(
        np.stack([ta.x, ta.y], -1), ta.heading, la, wa,
        np.stack([tb.x, tb.y], -1), tb.heading, lb, wb,
    )  # fmt: skip
    in_a, in_b = hit.any(axis=1), hit.any(axis=0)
    if not in_a.any():
        return out
    ea, xa = float(np.min(ta.t[in_a])), float(np.max(ta.t[in_a]))
    eb, xb = float(np.min(tb.t[in_b])), float(np.max(tb.t[in_b]))
    out.update(t_enter_a=ea, t_exit_a=xa, t_enter_b=eb, t_exit_b=xb)
    if xa < eb:
        out.update(pet=eb - xa, first=a)
    elif xb < ea:
        out.update(pet=ea - xb, first=b)
    else:
        out.update(pet=0.0, first=a if ea <= eb else b, collision=1)
    return out


# --------------------------------------------------------------------------- aggregates


def tet_tit(t: FloatArray, value: FloatArray, threshold: float = 1.5) -> dict[str, float]:
    """Time-Exposed and Time-Integrated measures of an indicator series (Minderhoud and Bovy, 2001).

    With ``value`` a time-to-collision-type indicator and threshold ``T*``:

    * ``TET`` = total time with ``0 <= value < T*`` (s);
    * ``TIT`` = integral of ``T* - value`` over that time (s^2).

    The series is treated as piecewise constant over the sampling interval of each stamp
    (``dt = t[i+1] - t[i]``, the last one repeats the previous interval). NaN values are *not*
    exposure (the indicator is undefined: no collision course).
    """
    t = np.asarray(t, float)
    v = np.asarray(value, float)
    if t.size == 0:
        return {"tet": 0.0, "tit": 0.0}
    dt = np.diff(t)
    dt = np.r_[dt, dt[-1] if dt.size else 0.0]
    low = np.isfinite(v) & (v >= 0) & (v < threshold)
    return {
        "tet": float(np.sum(dt[low])),
        "tit": float(np.sum(dt[low] * (threshold - v[low]))),
    }


def conflict_type(angle: float, rear_end: float = 30.0, crossing: float = 85.0) -> str:
    """Conflict type from the angle between the headings (radians in, degrees for the limits).

    ``'rear-end'`` below ``rear_end``, ``'crossing'`` above ``crossing``, otherwise
    ``'lane-change'``. The limits 30 and 85 degrees are this package's convention: the FHWA
    evaluation of SSAM (FHWA-HRT-08-051, chapter 6) says the SSAM classification was first based on
    the angle alone, later refined with lane and link information, and that the appropriate angles
    "warrant further investigation"; the values used inside SSAM were not verified here, so do not
    claim agreement with SSAM's type counts. The rule does not know which sides touch.
    """
    deg = float(np.degrees(angle))
    if deg < rear_end:
        return "rear-end"
    if deg > crossing:
        return "crossing"
    return "lane-change"


def braking_onset(
    t: FloatArray, speed: FloatArray, rate: float = 1.0, window: float = 1.0, drop: float = 0.5
) -> int:
    """Index of the start of the first speed drop of at least ``rate`` (m/s^2) over ``window`` s.

    A drop is found at the first frame ``i`` whose speed is, ``window`` seconds later, lower by at
    least ``max(rate * window, drop)`` m/s. Because that test looks ahead, the onset returned is
    the last frame of the highest speed within ``[t_i, t_i + window]``, i.e. where the decline
    starts. Returns -1 if there is none. This simple speed-drop rule is **not** the
    evasive-action detector of Johnsson and Laureshyn (2022), which needs a reference set of
    unhindered trajectories.
    """
    t = np.asarray(t, float)
    s = np.asarray(speed, float)
    for i in range(t.size):
        j = int(np.searchsorted(t, t[i] + window))
        if j >= t.size:
            break
        if s[i] - s[j] >= max(rate * (t[j] - t[i]), drop):
            seg = s[i : j + 1]
            return i + int(np.flatnonzero(seg >= seg.max() - 1e-9)[-1])
    return -1


def hyden_braking_limit(
    v1: float, v2: float = 0.0, friction0: float = 0.85, g: float = 9.81
) -> float:
    """Shortest Time to Accident (s) at which braking alone can stop the vehicle (Hyden, 1987).

    The uniform severity level of the "first alternative definition" (ALT.DEF.1), section 7.1.3 of
    Hyden's thesis (read from the page images, printed pp. 117-118): ``TA_min = v1 / (2 g f)`` with
    the friction coefficient ``f = friction0 exp(-0.0137 v_m)`` of the Swedish National Road
    Administration and the mean speed during the manoeuvre ``v_m = 2 (v1 - v2) / 3 + v2`` (m/s;
    ``v2`` the final speed, 0 for a stop). The thesis prints the result as
    ``TA_min = v1 / (16.7 exp(-0.0137 v_m))``, which is ``2 g`` times 0.85: ``friction0 = 0.85`` is
    the value without a safety margin and the default here; the 0.55 of the formula quoted before it
    includes a margin (the thesis says so on p. 118). About 0.94 s at 50 km/h with 0.85 and 1.46 s
    with 0.55.

    This is one uniform level of speed-dependent severity, a physical lower bound for braking on
    dry asphalt. It is **not** Hyden's serious-conflict threshold: the thesis adopts the second
    alternative (:func:`hyden_uniform_severity_ta` with ``alternative=2``) and puts the border at
    severity zone 2 (p. 166); see :func:`hyden_severity_zone` and :func:`hyden_serious_conflict`.
    """
    v_m = 2.0 * (v1 - v2) / 3.0 + v2
    f = friction0 * float(np.exp(-0.0137 * v_m))
    return float(v1 / (2.0 * g * f))


def hyden_uniform_severity_ta(
    v1: float, alternative: int = 1, v2: float = 0.0, friction0: float = 0.85
) -> float:
    """Uniform severity level of Hyden's (1987) TA-speed graph at conflicting speed ``v1`` (m/s).

    ``alternative=1`` is ALT.DEF.1 (:func:`hyden_braking_limit`); ``alternative=2`` is ALT.DEF.2
    (Garder, 1982; thesis section 7.1.4, p. 119): the level is set so that TA equals the **time
    needed to brake to a stop**, which is twice the TA of the first alternative. The parallel
    "severity zones" and the border of a serious conflict (zone 2 of ALT.DEF.2, p. 166) are coded
    in :func:`hyden_severity_zone` and :func:`hyden_serious_conflict`. The ALT.DEF.2 curve of this
    formula was compared with Figure 7.4 by eye only and lies **above** the figure's bold curve
    (formula about 1.1 s at 30 km/h and 2.8 s at 70 km/h; the figure about 0.8 s and 2.4-2.6 s,
    read by eye, uncertainty about 0.1 s), so zone borders computed from it are approximate.
    """
    if alternative not in (1, 2):
        raise ValueError("alternative must be 1 or 2")
    return alternative * hyden_braking_limit(v1, v2, friction0)


#: Width (s, along the TA axis) of one severity zone of Hyden's ALT.DEF.2 (Figure 7.17 and 7.4).
HYDEN_ZONE_WIDTH = 0.5


def hyden_zone_offset(
    ta: ArrayLike, v1: ArrayLike, v2: float = 0.0, friction0: float = 0.85
) -> FloatArray:
    """Distance (s, along the TA axis) of a ``(TA, v1)`` point to the ALT.DEF.2 braking-time curve.

    ``offset = TA - 2 TA_min(v1)``, with ``TA_min`` of :func:`hyden_braking_limit` (vectorised;
    ``v1`` in m/s). Negative: the point lies on the severe side of the curve (less time than
    braking to a stop needs); positive: it lies on the safe side. The severity zones of Hyden's
    Figure 7.17 are parallel copies of this curve shifted along the TA axis.
    """
    ta_a, v = np.broadcast_arrays(np.asarray(ta, dtype=float), np.asarray(v1, dtype=float))
    v_m = 2.0 * (v - v2) / 3.0 + v2
    f = friction0 * np.exp(-0.0137 * v_m)
    out: FloatArray = ta_a - 2.0 * v / (2.0 * 9.81 * f)
    return out


def hyden_severity_zone(
    ta: ArrayLike, v1: ArrayLike, v2: float = 0.0, friction0: float = 0.85
) -> FloatArray:
    """Severity zone of Hyden's (1987) ALT.DEF.2 for a ``(TA, v1)`` point (vectorised).

    Read from Figures 7.4 and 7.17 (ALT.DEF.2 panel) of the thesis: the zone borders are
    parallel copies of the braking-time curve (:func:`hyden_zone_offset` = 0), shifted along the TA
    axis in steps of :data:`HYDEN_ZONE_WIDTH` = 0.5 s (each zone is halved into 'a' and 'b' of
    0.25 s). Zone 3 is the first zone on the safe side of the braking-time curve (offset 0 to 0.5
    s), zone 2 the next (0.5 to 1.0 s), zone 1 the last drawn (1.0 to 1.5 s); zones 4, 5, ... lie
    on the severe side (offset -0.5 to 0, -1.0 to -0.5, ...). ``zone = 3 - floor(offset / 0.5)``;
    offsets of 1.5 s or more are beyond zone 1 and get **0** (not drawn in the figure). NaN where
    an input is NaN.

    Limits: numbering and width were read from the printed figures by eye (the thesis is a scan),
    the braking-time curve is the formula of :func:`hyden_braking_limit` (which sits above the
    figure's curve, see :func:`hyden_uniform_severity_ta`), and no accident or conflict data were
    used to check the zones.
    """
    off = hyden_zone_offset(ta, v1, v2, friction0)
    zone = 3.0 - np.floor(off / HYDEN_ZONE_WIDTH + 1e-12)
    zone = np.where(zone < 1.0, 0.0, zone)
    out: FloatArray = np.where(np.isnan(off), np.nan, zone)
    return out


def hyden_serious_conflict(
    ta: ArrayLike, v1: ArrayLike, v2: float = 0.0, friction0: float = 0.85
) -> BoolArray:
    """Hyden's (1987) definition of a serious conflict (thesis section 7.3.9, p. 166).

    "A serious conflict is an event where the Time to Accident and Conflicting Speed for the
    relevant road-user produces a combined value that lies in severity zone 2 or higher for the
    ALT.DEF.2 of severity": ``hyden_severity_zone >= 2``, i.e. ``TA - 2 TA_min(v1) < 1.0`` s.
    ``False`` where an input is NaN. The relevant road user is the one that evades (or the less
    severe of the two); the caller chooses ``(TA, v1)`` accordingly (see :func:`swedish_pair`).
    """
    zone = hyden_severity_zone(ta, v1, v2, friction0)
    out: BoolArray = np.where(np.isnan(zone), False, zone >= 2.0).astype(bool)
    return out


def swedish_pair(
    enc: Encounter, who: int = 0, rate: float = 1.0, window: float = 1.0, basis: str = "ttc"
) -> dict[str, float]:
    """``(TA, v_conf)`` of the Swedish Traffic Conflict Technique (Hyden, 1987) for an encounter.

    ``TA`` is the time-to-accident at the start of the evasive action and ``v_conf`` the speed of
    the evading road user at that moment. The start is found with :func:`braking_onset` for road
    user ``who`` (1 or 2; 0 = the earlier of the two). TA is taken from ``basis``: ``'ttc'`` (only
    on a collision course) or ``'t2'`` (also on a crossing course). Observer-labelled conflicts
    are the original technique; this is an automatic stand-in.

    Returns:
        Dict with ``ta``, ``v_conf`` (m/s), ``evader`` (1/2), ``t_onset``; NaN when no onset or
        the basis indicator is undefined at that moment.
    """
    nan = float("nan")
    res = {"ta": nan, "v_conf": nan, "evader": 0.0, "t_onset": nan}
    onset = {
        1: braking_onset(enc.t, enc.speed_a, rate, window),
        2: braking_onset(enc.t, enc.speed_b, rate, window),
    }
    choices = [k for k in (1, 2) if onset[k] >= 0 and who in (0, k)]
    if not choices:
        return res
    k = min(choices, key=lambda q: onset[q])
    i = onset[k]
    ta = float((enc.ttc if basis == "ttc" else enc.t2)[i])
    res.update(
        ta=ta, v_conf=float((enc.speed_a if k == 1 else enc.speed_b)[i]),
        evader=float(k), t_onset=float(enc.t[i]),
    )  # fmt: skip
    return res


def summarize(enc: list[Encounter]) -> dict[str, IntArray | FloatArray]:
    """Per-encounter minima as arrays (``min_ttc``, ``min_tadv``, ``min_t2``, ``min_distance``)."""
    return {
        "min_ttc": np.array([e.min_ttc() for e in enc]),
        "min_tadv": np.array([e.min_tadv() for e in enc]),
        "min_t2": np.array([e.min_t2() for e in enc]),
        "min_distance": np.array([e.min_distance() for e in enc]),
        "a": np.array([e.a for e in enc], dtype=np.int64),
        "b": np.array([e.b for e in enc], dtype=np.int64),
    }
