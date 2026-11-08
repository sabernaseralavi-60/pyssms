"""One report per recording or simulation run, and a comparison of several.

:func:`summarize_scenario` runs the whole chain on one :class:`~pyssms.trajectories.Trajectories`
(a simulator run read with :func:`pyssms.io.read_trj` / :func:`~pyssms.io.read_sumo_fcd`, or a
drone recording): candidate pairs -> indicator series -> per-encounter minima -> counts by state,
Time-Exposed / Time-Integrated TTC, observed PET, conflict types, the level counts of the severity
hierarchy and, for car-following pairs, the ten measures of :mod:`pyssms.ssm1d`.
:func:`compare_scenarios` puts several summaries side by side in one Markdown table.

Counts of "conflicts" depend on the thresholds (``ttc_threshold``, ``pet_threshold``) and on the
pair radius ``max_distance``; all of them are recorded in the summary and nothing is hidden in
defaults. Comparing a simulated scenario with another one is meaningful; comparing the numbers
with those of the SSAM program is not guaranteed (see :func:`pyssms.process.conflict_type`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from pyssms import ssm1d
from pyssms.geometry import FloatArray
from pyssms.hierarchy import Hierarchy, build_hierarchy, closing_speed_at_minimum
from pyssms.process import (
    Encounter,
    conflict_type,
    encounters,
    observed_pet,
    tet_tit,
)
from pyssms.trajectories import Trajectories

__all__ = ["ScenarioSummary", "compare_scenarios", "following_measures", "summarize_scenario"]


@dataclass(frozen=True)
class ScenarioSummary:
    """Summary of one scenario.

    Attributes:
        name: Label.
        metrics: Scalar results (counts, minima, TET/TIT, ...).
        settings: The thresholds and radii used.
        hierarchy: Level counts of the severity hierarchy.
        conflict_types: Number of encounters per angle-based type (at the time stamp of the
            smallest TAdv).
        encounters: The encounters analysed (their indicator series).
    """

    name: str
    metrics: dict[str, float]
    settings: dict[str, float]
    hierarchy: Hierarchy
    conflict_types: dict[str, int]
    encounters: list[Encounter] = field(repr=False, default_factory=list)

    def table(self) -> str:
        """Markdown table of the metrics."""
        rows = [f"| {k} | {_fmt(v)} |" for k, v in self.metrics.items()]
        return "\n".join(["| metric | value |", "|---|---|", *rows])


def _fmt(v: float) -> str:
    if isinstance(v, (int, np.integer)) or (
        isinstance(v, float) and v.is_integer() and abs(v) < 1e9
    ):
        return str(int(v))
    return "nan" if v != v else f"{v:.3f}"


def _angle_at_min(enc: Encounter) -> float:
    if not np.isfinite(enc.tadv).any():
        return float(enc.angle[int(np.argmin(enc.distance))])
    return float(enc.angle[int(np.nanargmin(np.where(np.isfinite(enc.tadv), enc.tadv, np.inf)))])


def summarize_scenario(
    traj: Trajectories,
    name: str = "scenario",
    horizon: float = 10.0,
    max_distance: float = 30.0,
    ttc_threshold: float = 1.5,
    pet_threshold: float = 5.0,
    decel: float = 0.0,
    edges: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0),
) -> ScenarioSummary:
    """Run the chain and collect the results of one scenario (see the module docstring).

    Args:
        traj: Trajectories of the scenario.
        name: Label used in comparisons.
        horizon: Prediction horizon (s).
        max_distance: Centre distance (m) that makes a pair a candidate.
        ttc_threshold: TTC (s) below which an encounter counts as a TTC conflict, and the
            threshold of TET/TIT (1.5 s is the maximum TTC of the SSAM program's illustrations).
        pet_threshold: Observed PET (s) at or below which an encounter counts as a PET conflict
            (no value is taken from SSAM here: choose and report it).
        decel: Braking (m/s^2) of the Extended closing speed; 0 gives the plain closing speed.
        edges: TAdv edges (s) of the hierarchy levels.

    Returns:
        :class:`ScenarioSummary`.
    """
    enc = encounters(traj, horizon=horizon, max_distance=max_distance)
    n = len(enc)
    nan = float("nan")
    min_ttc = np.array([e.min_ttc() for e in enc])
    min_tadv = np.array([e.min_tadv() for e in enc])
    any_a = np.array([bool(np.any(e.state == "A")) for e in enc], dtype=bool)
    any_b = np.array([bool(np.any(e.state == "B")) for e in enc], dtype=bool)
    tt = [tet_tit(e.t, e.ttc, ttc_threshold) for e in enc]
    pets = np.full(n, nan)
    overlap = np.zeros(n, dtype=bool)
    for k, e in enumerate(enc):
        if np.any(e.state != "C"):  # the future paths overlap at some time stamp
            r = observed_pet(traj, e.a, e.b)
            pets[k] = float(r["pet"])
            overlap[k] = bool(r["collision"])
    severity = np.array([closing_speed_at_minimum(e, decel) for e in enc])
    types: dict[str, int] = {"rear-end": 0, "lane-change": 0, "crossing": 0}
    for e in enc:
        types[conflict_type(_angle_at_min(e))] += 1
    finite_pet = pets[np.isfinite(pets)]
    metrics: dict[str, float] = {
        "road_users": float(traj.ids.size),
        "duration_s": float(traj.times[-1] - traj.times[0]) if len(traj) else 0.0,
        "encounters": float(n),
        "collision_course (any A)": float(any_a.sum()),
        "crossing_course only (B)": float((any_b & ~any_a).sum()),
        "no overlap (C)": float((~any_a & ~any_b).sum()),
        "min_ttc_s": float(np.nanmin(min_ttc)) if np.isfinite(min_ttc).any() else nan,
        "ttc_p05_s": float(np.nanpercentile(min_ttc, 5)) if np.isfinite(min_ttc).any() else nan,
        "median_min_tadv_s": float(np.nanmedian(min_tadv)) if np.isfinite(min_tadv).any() else nan,
        f"ttc_conflicts (min TTC < {ttc_threshold:g} s)": float(np.sum(min_ttc < ttc_threshold)),
        f"TET_s (TTC < {ttc_threshold:g} s)": float(sum(x["tet"] for x in tt)),
        f"TIT_s2 (TTC < {ttc_threshold:g} s)": float(sum(x["tit"] for x in tt)),
        "pairs with observed PET": float(finite_pet.size),
        "min_pet_s": float(finite_pet.min()) if finite_pet.size else nan,
        f"pet_conflicts (PET <= {pet_threshold:g} s)": float(np.sum(finite_pet <= pet_threshold)),
        "body overlaps (recorded footprints)": float(overlap.sum()),
        "median closing speed at min TAdv (km/h)": (
            float(np.nanmedian(severity)) if np.isfinite(severity).any() else nan
        ),
    }
    for kind, count in types.items():
        metrics[f"type: {kind}"] = float(count)
    hier = build_hierarchy(enc, edges=edges, severity=severity)
    settings = {
        "horizon_s": horizon, "max_distance_m": max_distance, "ttc_threshold_s": ttc_threshold,
        "pet_threshold_s": pet_threshold, "decel": decel,
    }  # fmt: skip
    return ScenarioSummary(
        name=name, metrics=metrics, settings=settings, hierarchy=hier,
        conflict_types=types, encounters=enc,
    )  # fmt: skip


def compare_scenarios(
    scenarios: Mapping[str, ScenarioSummary | Trajectories], **kwargs: float
) -> str:
    """Markdown table with one column per scenario (trajectories are summarised first).

    Extra keyword arguments go to :func:`summarize_scenario`. A scenario that was summarised with
    other settings than the first one is flagged under the table.
    """
    sums = {
        k: v if isinstance(v, ScenarioSummary) else summarize_scenario(v, name=k, **kwargs)  # type: ignore[arg-type]
        for k, v in scenarios.items()
    }
    names = list(sums)
    keys = list(next(iter(sums.values())).metrics)
    lines = ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for key in keys:
        cells = [_fmt(s.metrics.get(key, float("nan"))) for s in sums.values()]
        lines.append(f"| {key} | " + " | ".join(cells) + " |")
    first = sums[names[0]].settings
    for n in names[1:]:
        if sums[n].settings != first:
            lines.append(f"\nNote: `{n}` was summarised with different settings than `{names[0]}`.")
    lines.append("\nHierarchy (encounters per level):")
    lvl = sums[names[0]].hierarchy.levels
    lines += ["", "| level | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for i, lv in enumerate(lvl):
        cells = [str(int(s.hierarchy.totals[i])) for s in sums.values()]
        lines.append(f"| {lv} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def following_measures(
    traj: Trajectories,
    leader: int,
    follower: int,
    dec_l: float = 6.0,
    dec_f: float = 6.0,
    reaction: float = 1.0,
) -> dict[str, FloatArray]:
    """The ten car-following measures of :mod:`pyssms.ssm1d` for a leader/follower pair.

    The pair is treated as one-dimensional along the follower's heading: ``gap`` is the centre
    distance along that heading minus half the sum of the lengths; speeds are the components
    along it; accelerations and jerks are finite differences (the jerk, hence TTC3, is noisy at
    drone frame rates). ``dec_l``, ``dec_f`` and ``reaction`` are assumptions of the story, not
    data. Time stamps where the leader is not ahead of the follower give a negative ``gap`` and
    should be dropped by the caller.

    Returns:
        Dict with ``t``, ``gap``, ``v_l``, ``v_f`` and ``ttc1``, ``ttc2``, ``ttc3``, ``ttcd``,
        ``drac``, ``mdrac``, ``psd``, ``mpsd``, ``sdi``, ``dcia``.
    """
    tl, tf = traj.track(leader), traj.track(follower)
    t, il, i_f = np.intersect1d(tl.t, tf.t, return_indices=True)
    h = tf.heading[i_f]
    ux, uy = np.cos(h), np.sin(h)
    gap = (
        (tl.x[il] - tf.x[i_f]) * ux
        + (tl.y[il] - tf.y[i_f]) * uy
        - (tl.length[il] + tf.length[i_f]) / 2
    )
    v_l = tl.vx[il] * ux + tl.vy[il] * uy
    v_f = tf.vx[i_f] * ux + tf.vy[i_f] * uy
    if t.size > 2:
        a_l, a_f = np.gradient(v_l, t), np.gradient(v_f, t)
        j_l, j_f = np.gradient(a_l, t), np.gradient(a_f, t)
    else:
        a_l = a_f = j_l = j_f = np.zeros_like(t)
    dcia, _ = ssm1d.dcia(gap, v_l, v_f, a_l, a_f, reaction)
    return {
        "t": t, "gap": gap, "v_l": v_l, "v_f": v_f,
        "ttc1": ssm1d.ttc_poly(gap, v_l, v_f),
        "ttc2": ssm1d.ttc_poly(gap, v_l, v_f, a_l, a_f),
        "ttc3": ssm1d.ttc_poly(gap, v_l, v_f, a_l, a_f, j_l, j_f),
        "ttcd": ssm1d.ttcd(gap, v_l, v_f, dec_l),
        "drac": ssm1d.drac(gap, v_l, v_f),
        "mdrac": ssm1d.mdrac(gap, v_l, v_f, reaction),
        "psd": ssm1d.psd(gap, v_f, dec_f),
        "mpsd": ssm1d.mpsd(gap, v_f, dec_f, reaction),
        "sdi": ssm1d.sdi(gap, v_l, v_f, dec_l, dec_f, reaction),
        "dcia": dcia,
    }  # fmt: skip
