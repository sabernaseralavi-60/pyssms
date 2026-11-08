"""Report of ``tools/levelx_ssm1d.py``: pools the per-recording files into aggregates.

Writes ``docs/<name>_ssm1d_descriptive.md`` and ``.json`` (aggregates only). Called at the end of
``levelx_ssm1d.py``; can also be run alone: ``python tools/levelx_ssm1d_report.py highD``.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from typing import Any

import levelx_ssm1d as L
import numpy as np

TIME_MEASURES = ("ttc1", "ttc2", "ttc3", "ttcd")
LABEL = {
    "ttc1": "TTC1 (constant speeds)", "ttc2": "TTC2 (constant accelerations)",
    "ttc3": "TTC3 (constant jerks)", "ttcd": "TTCD (leader brakes to a stop)",
    "drac": "DRAC", "mdrac": "MDRAC", "psd": "PSD", "mpsd": "MPSD", "sdi": "SDI",
    "dcia": "DCIA",
}  # fmt: skip
UNIT = {"ttc1": "s", "ttc2": "s", "ttc3": "s", "ttcd": "s", "drac": "m/s2", "mdrac": "m/s2",
        "psd": "-", "mpsd": "-", "sdi": "0/1", "dcia": "m/s2"}  # fmt: skip
K_LABEL = {"k_ttc": "TTC (polygon)", "k_tadv": "TAdv", "k_t2": "T2", "k_tg": "TG",
           "lat_margin": "lateral margin (m)", "beta": "signed margin beta",
           "req_brake": "required braking of the follower (m/s2)"}  # fmt: skip


def defined(m: str, v: np.ndarray) -> np.ndarray:
    """Values of measure ``m`` that count as defined (NaN elsewhere); see the report text."""
    v = v.astype(float)
    if m in TIME_MEASURES:
        return np.where(np.isfinite(v) & (v > 0) & (v <= L.HORIZON), v, np.nan)
    if m in ("drac", "mdrac"):
        return np.where(np.isfinite(v) & (v > 0), v, np.nan)  # closing pairs; inf dropped
    if m == "sdi":
        return v
    return np.where(np.isfinite(v), v, np.nan)


def _rank(x: np.ndarray) -> np.ndarray:
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts)
    avg = (cum - counts + 1 + cum) / 2.0
    out: np.ndarray = avg[inv]
    return out


def spearman(x: np.ndarray, y: np.ndarray, min_n: int = 200) -> tuple[float, int]:
    """Spearman rank correlation of the pairwise complete cases (NaN if fewer than ``min_n``)."""
    ok = np.isfinite(x) & np.isfinite(y)
    n = int(ok.sum())
    if n < min_n:
        return float("nan"), n
    rx, ry = _rank(x[ok]), _rank(y[ok])
    if rx.std() == 0 or ry.std() == 0:
        return float("nan"), n
    return float(np.corrcoef(rx, ry)[0, 1]), n


def INFO(name: str) -> dict[str, str]:
    """Text blocks that differ between data sources."""
    if name == "NGSIM":
        return {
            "tool": "tools/ngsim_ssm1d.py",
            "licence": "the data are the FHWA NGSIM trajectories (modified CC BY 2.0, credit FHWA "
            "and NGSIM; US-101 and I-80 only).",
            "pairs": "* Pairs: the data set's `Preceding Vehicle` column (the vehicle ahead in the "
            "same lane); positions are smoothed with a causal 5-frame mean first, the speed is the "
            "backward difference of the smoothed position, the acceleration the causal 5-frame "
            "mean of its backward difference (decision fixed before the run; the data set's own "
            "acceleration column is not used).",
            "kin": "speeds and accelerations (derived as just described)",
            "scale_note": "taken from the NGSIM sites that have unhindered vehicles under the 15 m "
            "rule (Lankershim and Peachtree; US-101 and I-80 have none, because of dense traffic) "
            "and applied to the freeway pairs, so they are not scales of freeway traffic.",
            "note": "* The reference column here is the data set's own `Spacing` (front centre to "
            "front centre) minus the length of the leader, which equals our clear gap by "
            "construction of the definition; the check below tests the units and the reader. "
            "This report is the **descriptive step only** (no outcome).",
        }
    return {
        "tool": f"tools/levelx_ssm1d.py {name}",
        "licence": "the data are not redistributed (licence: non-commercial research use).",
        "pairs": "* Pairs: `precedingId` (highD: the vehicle ahead in the same lane) or `leadId` "
        "(exiD, kept only if the leader is ahead and laterally within the follower's width plus "
        f"{L.LATERAL_MAX:g} m).",
        "kin": "speeds and accelerations (data set values)",
        "scale_note": "which are small on straight roads, so beta takes large values;",
        "note": "* The 2025 paper (Future Transportation 5:86, pp. 17-19) names highD among the "
        "datasets for the validation it calls the most critical next step and sketches a "
        "scenario-based validation against conflict outcomes; this report is the **descriptive "
        "first step only** (no outcome).",
    }


def pooled(name: str, ids: list[str]) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    """Concatenate the per-recording files; return the columns and the meta records."""
    cols: dict[str, list[np.ndarray]] = {}
    metas = []
    for i in ids:
        with np.load(L.RUNS / name / f"{i}.npz") as z:
            metas.append(json.loads(str(z["_meta"])))
            for k in z.files:
                if k != "_meta":
                    cols.setdefault(k, []).append(z[k])
    return {k: np.concatenate(v) for k, v in cols.items()}, metas


def _q(v: np.ndarray, qs: tuple[float, ...]) -> list[float]:
    v = v[np.isfinite(v)]
    return [float(np.percentile(v, q)) for q in qs] if v.size else [float("nan")] * len(qs)


def _f(x: float | None, nd: int = 2) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.{nd}f}"


def _critical(m: str, v: np.ndarray) -> float:
    fin = np.isfinite(v)
    if m in TIME_MEASURES:
        return float(np.mean(fin & (v <= 3)))
    if m in ("psd", "mpsd"):
        return float(np.mean(fin & (v < 1)))
    if m == "sdi":
        return float(np.mean(v == 1))
    return float("nan")


def report(name: str, ids: list[str]) -> None:
    d, metas = pooled(name, ids)
    n = int(d["gap"].size)
    qs = (5.0, 25.0, 50.0, 75.0, 95.0)
    pf = int(sum(m["n_pair_frames"] for m in metas))
    res: dict[str, Any] = {
        "dataset": name, "recordings": len(ids), "sample_rows": n, "pair_frames": pf,
        "params": L.PARAMS, "alt_params": L.ALT_PARAMS, "horizon": L.HORIZON,
        "step_frames": L.step_of(name), "measures": {}, "alt": {}, "spearman": {}, "checks": {},
    }  # fmt: skip
    ref = d["ref_dhw"].astype(float)
    okr = ref > 0
    diff = d["gap"][okr].astype(float) - ref[okr]
    res["checks"]["gap_minus_dataset_headway"] = {
        "n": int(okr.sum()), "median": float(np.median(diff)) if diff.size else None,
        "p5_p95": _q(diff, (5.0, 95.0)), "abs_max": float(np.abs(diff).max()) if diff.size else None,
    }  # fmt: skip
    t1 = d["ttc1"].astype(float)
    kk = d["k_ttc"].astype(float)
    near = np.isfinite(t1) & (t1 > 0) & (t1 <= L.HORIZON)
    both = near & np.isfinite(kk)
    res["checks"]["polygon_ttc_vs_ttc1"] = {
        "ttc1_within_horizon": int(near.sum()), "polygon_ttc_defined_there": int(both.sum()),
        "max_abs_diff_s": float(np.abs(kk[both] - t1[both]).max()) if both.any() else None,
    }  # fmt: skip
    st = d["k_state"].astype(int)
    res["state_share"] = {"A": float((st == 1).mean()), "B": float((st == 2).mean()),
                          "C": float((st == 0).mean())}  # fmt: skip
    scales = metas[0]["beta_scales"]
    lines = [
        f"# Ten car-following measures on {name}: descriptive statistics", "",
        f"*Generated by `{INFO(name)['tool']}`; do not edit by hand. Aggregates only; "
        f"{INFO(name)['licence']} **Descriptive: no outcome "
        "(conflict, crash, braking) is used, so nothing here validates or ranks a measure.***", "",
        "## What was computed", "",
        f"* Data: {len(ids)} recordings of {name}; {pf:,} follower-leader pair-frames with a positive "
        f"clear gap of at most {L.GAP_MAX:g} m; the statistics are on every {L.step_of(name)}th frame "
        f"(1 s) of a pair, {n:,} rows.",
        INFO(name)["pairs"] + " Gap = centre distance along the follower's heading minus half the sum of the lengths; "
        f"{INFO(name)['kin']} are projected on that heading; the jerk is the "
        "central difference of the acceleration along the consecutive frames of the pair (rows "
        "without a neighbouring frame are dropped; the jerk, hence TTC3, is noisy).",
        f"* Parameters of the stories, **fixed before the run** (the 2025 paper gives no values; "
        f"assumptions, not data): reaction time {L.PARAMS['reaction']:g} s, leader deceleration "
        f"{L.PARAMS['dec_l']:g} m/s2, follower deceleration {L.PARAMS['dec_f']:g} m/s2. Printed-form "
        "differences are as in `docs/ssm1d_notes.md` (the code uses the derived forms). A second set "
        f"({L.ALT_PARAMS['reaction']:g} s, {L.ALT_PARAMS['dec_l']:g}, {L.ALT_PARAMS['dec_f']:g} m/s2) "
        "shows the sensitivity.",
        f"* Defined values: time measures (TTC1, TTC2, TTC3, TTCD): a positive root within "
        f"{L.HORIZON:g} s; DRAC, MDRAC: closing pairs (positive, finite); PSD, MPSD, DCIA: finite; SDI "
        "is 0 or 1 for every row. The polygon indicators (TTC, TAdv, T2, TG) use the horizon "
        f"{L.HORIZON:g} s with rectangular bodies of the follower's heading and constant velocity.",
        INFO(name)["note"],
        "",
    ]  # fmt: skip
    chk = res["checks"]["gap_minus_dataset_headway"]
    if chk["n"]:
        lines.append(
            f"* Check of the gap: our clear gap minus the data set's own headway column "
            f"({chk['n']:,} rows): median {_f(chk['median'], 3)} m, 5th to 95th percentile "
            f"{_f(chk['p5_p95'][0], 3)} to {_f(chk['p5_p95'][1], 3)} m, largest absolute "
            f"{_f(chk['abs_max'], 3)} m."
        )
    c2 = res["checks"]["polygon_ttc_vs_ttc1"]
    lines += [
        f"* Check of the polygon: of {c2['ttc1_within_horizon']:,} rows with TTC1 within the horizon, "
        f"the polygon TTC is defined in {c2['polygon_ttc_defined_there']:,}; where both are defined the "
        f"largest absolute difference is {_f(c2['max_abs_diff_s'], 6)} s. TTC1 sees only the "
        "distance and the speeds along the heading, the polygon also the lateral separation and the "
        "lateral velocities of the bodies, so the two differ where the vehicles move sideways "
        "relative to each other or pass side by side (the polygon then has no TTC).",
        f"* State of the polygon over all sampled rows: collision course (A) "
        f"{100 * res['state_share']['A']:.1f} %, crossing course (B) "
        f"{100 * res['state_share']['B']:.1f} %, no overlap within the horizon (C) "
        f"{100 * res['state_share']['C']:.1f} %.",
        "", "## Distribution of each measure (defined values only)", "",
        "| measure | unit | defined, % of rows | p5 | p25 | median | p75 | p95 | critical, % of rows |",
        "|---|---|---|---|---|---|---|---|---|",
    ]  # fmt: skip
    for m in L.MEASURES:
        v = defined(m, d[m])
        fin = np.isfinite(v)
        q = _q(v, qs)
        c = _critical(m, v)
        crit = "-" if not np.isfinite(c) else (
            f"TTC <= 3 s: {100 * c:.2f}" if m in TIME_MEASURES else
            f"< 1: {100 * c:.2f}" if m in ("psd", "mpsd") else f"= 1: {100 * c:.2f}")  # fmt: skip
        res["measures"][m] = {"defined_share": float(fin.mean()), "quantiles": dict(zip(qs, q, strict=True)),
                              "critical_share": c}  # fmt: skip
        lines.append(f"| {LABEL[m]} | {UNIT[m]} | {100 * fin.mean():.1f} | "
                     + " | ".join(_f(x, 3) for x in q) + f" | {crit} |")  # fmt: skip
    lines += [
        "", "## Sensitivity to the story parameters", "",
        f"Reaction time {L.ALT_PARAMS['reaction']:g} s, decelerations {L.ALT_PARAMS['dec_l']:g} m/s2 "
        f"(first set: {L.PARAMS['reaction']:g} s, {L.PARAMS['dec_l']:g} m/s2). Measures that do not "
        "depend on these parameters (TTC1-3, DRAC) are not repeated.", "",
        "| measure | defined, % (set 1 / set 2) | median (set 1 / set 2) | critical, % (set 1 / set 2) |",
        "|---|---|---|---|",
    ]  # fmt: skip
    for m in ("ttcd", "mdrac", "psd", "mpsd", "sdi", "dcia"):
        row = []
        for key in (m, "alt_" + m):
            v = defined(m, d[key])
            row.append(
                (float(np.isfinite(v).mean()) * 100, _q(v, (50.0,))[0], _critical(m, v) * 100)
            )
        res["alt"][m] = row
        lines.append(f"| {LABEL[m]} | {row[0][0]:.1f} / {row[1][0]:.1f} | "
                     f"{_f(row[0][1], 3)} / {_f(row[1][1], 3)} | {_f(row[0][2])} / {_f(row[1][2])} |")  # fmt: skip
    lines += [
        "", "## Spearman rank correlation with the polygon indicators", "",
        "Pairwise complete cases of the defined values (`n` below 200 is not reported). Time measures, "
        "TAdv, T2, TG, the lateral margin and beta are larger when safer; DRAC, MDRAC, DCIA, SDI and "
        "the required braking are larger when more critical, so expect negative signs between the two "
        "families. Descriptive: a "
        "high correlation says two readings order the same pairs alike, not that either is right.", "",
        "| measure | " + " | ".join(K_LABEL[k] for k in L.K_NAMES) + " |",
        "|---|" + "---|" * len(L.K_NAMES),
    ]  # fmt: skip
    kvals = {
        k: np.where(np.isfinite(d[k].astype(float)), d[k].astype(float), np.nan) for k in L.K_NAMES
    }
    for m in L.MEASURES:
        v = defined(m, d[m])
        cells, rec = [], {}
        for k in L.K_NAMES:
            rho, nn = spearman(v, kvals[k])
            rec[k] = {"rho": rho, "n": nn}
            cells.append("n/a" if not np.isfinite(rho) else f"{rho:+.2f} (n={nn:,})")
        res["spearman"][m] = rec
        lines.append(f"| {LABEL[m]} | " + " | ".join(cells) + " |")
    sd, se = (scales[0], scales[1]) if scales else (None, None)
    lines += [
        "", "Note on the signed margin beta: it uses the prediction-error scales of this data set "
        f"(`docs/diamond_{name}.md`, tau = {L.SCALE_TAU:g} s; sigma_delta = {_f(sd, 4)} s, sigma_eps = "
        f"{_f(se, 4)} m), {INFO(name)['scale_note']} only its ordering is used here.", "",
    ]  # fmt: skip
    stem = f"docs/{name.lower()}_ssm1d_descriptive"
    Path(stem + ".md").write_text("\n".join(lines), encoding="utf-8")
    Path(stem + ".json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"written {stem}.md", flush=True)


if __name__ == "__main__":
    nm = sys.argv[1]
    files = sorted(glob.glob(str(L.RUNS / nm / "*.npz")), key=lambda f: int(Path(f).stem))
    report(nm, [Path(f).stem for f in files])
