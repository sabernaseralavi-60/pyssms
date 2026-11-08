"""Calibration of the prediction-error scales and the empirical hierarchy on a LevelX data set.

Usage: ``python tools/levelx_diamond.py inD [limit] [--workers N]`` (names: inD, rounD, uniD,
exiD, highD). Every recording in ``data_raw/<folder>/data`` is processed on its own and its
**aggregates** (counts per level and severity class, prediction-error scales, observed seconds)
are written at once to ``runs_local/diamond/<name>/<NN>.json`` (git-ignored). A recording whose
file already exists with the same settings is skipped, so an interrupted run can simply be started
again. At the end the files are summed into ``docs/diamond_<name>.md`` and ``.json`` (aggregates
only: counts and scales, no trajectories). Recordings are read through the bit-identical ``.npz``
cache (:func:`pyssms.io.load_levelx_fast`). Descriptive, not a hypothesis test: nothing here
validates an indicator.

``limit`` keeps the first ``limit`` recordings (numerical order); ``--workers`` sets the number of
processes (default 4).
"""

from __future__ import annotations

import glob
import json
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from pyssms import calibration, hierarchy, io, process

FOLDERS = {
    "inD": "inD-dataset-v1.1",
    "rounD": "round-dataset-v1.1",
    "uniD": "uniD-dataset-v1.1",
    "exiD": "exiD-dataset-v2.1",
    "highD": "highD-dataset-v1.0",
}
VRU = {"pedestrian", "bicycle", "animal"}
HORIZON, MAX_DIST = 10.0, 30.0
EDGES = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
TAUS = (0.5, 1.0, 2.0, 3.0, 4.0)
SETTINGS = {"horizon": HORIZON, "max_dist": MAX_DIST, "edges": list(EDGES), "taus": list(TAUS),
            "min_gap": 15.0, "severity_edges": [10.0, 30.0], "version": 2}  # fmt: skip
RUNS = Path("runs_local") / "diamond"
CHUNK = 3000  # pairs per batch of encounters (counts are additive over batches)
LICENCE_NOTE = {"NGSIM": "Data: FHWA NGSIM programme, licence CC BY 2.0 (modified; credit FHWA and NGSIM)."}


def pair_class(a: str, b: str) -> str:
    """Class of a pair: motor-motor, motor-VRU or VRU-VRU."""
    n = (a in VRU) + (b in VRU)
    return ["motor-motor", "motor-VRU", "VRU-VRU"][n]


def process_recording(tracks_csv: str, name: str) -> dict[str, Any]:
    """Aggregates of one recording (JSON-serialisable)."""
    base = tracks_csv.replace("_tracks.csv", "")
    tr = io.load_levelx_fast(tracks_csv, base + "_tracksMeta.csv", base + "_recordingMeta.csv")
    loc = str(io._read_dicts(Path(base + "_recordingMeta.csv"))[0]["locationId"])
    return process_trajectories(tr, name, Path(base).name, loc)


def process_trajectories(tr: Any, name: str, rec: str, loc: str) -> dict[str, Any]:
    """Aggregates of one set of trajectories (also used for non-LevelX sources such as NGSIM)."""
    t0 = time.time()
    first = np.unique(tr.uid, return_index=True)
    kind_of = {int(u): str(tr.kind[i]) for u, i in zip(*first, strict=True)}
    out: dict[str, Any] = {"dataset": name, "rec": rec, "loc": loc,
                           "settings": SETTINGS, "seconds": float(tr.times[-1] - tr.times[0]),
                           "classes": {}, "scale": None}  # fmt: skip
    ids = calibration.unhindered_ids(tr, min_gap=15.0)
    ids = np.array([u for u in ids if kind_of[int(u)] not in VRU], dtype=np.int64)
    if ids.size:
        sc = calibration.calibrate_scales(tr, ids, taus=TAUS)
        out["scale"] = {"n_ids": int(ids.size), "n": sc.n.tolist(), "sd": sc.sigma_delta.tolist(),
                        "se": sc.sigma_eps.tolist()}  # fmt: skip
    pairs = [
        (u, v)
        for u, v in process.candidate_pairs(tr, max_distance=MAX_DIST, horizon=HORIZON)
        if not (kind_of[u] in VRU and kind_of[v] in VRU)
    ]  # pedestrian-pedestrian pairs are not encounters of interest and dominate the cost
    acc: dict[str, np.ndarray] = {}
    meta: dict[str, tuple[list[str], list[str]]] = {}
    for s0 in range(0, len(pairs), CHUNK):  # chunks keep the memory of the encounters bounded
        by_class: dict[str, list[process.Encounter]] = defaultdict(list)
        sev: dict[str, list[float]] = defaultdict(list)
        for e in process.encounters(tr, horizon=HORIZON, pairs=pairs[s0 : s0 + CHUNK]):
            cls = pair_class(kind_of[e.a], kind_of[e.b])
            by_class[cls].append(e)
            sev[cls].append(hierarchy.closing_speed_at_minimum(e))
        for cls, enc in by_class.items():
            h = hierarchy.build_hierarchy(enc, edges=EDGES, severity=sev[cls],
                                          severity_edges=(10.0, 30.0))  # fmt: skip
            acc[cls] = acc[cls] + h.counts if cls in acc else h.counts
            meta[cls] = (h.levels, h.severity_classes)
    for cls, cnt in acc.items():
        out["classes"][cls] = {"levels": meta[cls][0], "severity_classes": meta[cls][1],
                               "counts": cnt.tolist()}  # fmt: skip
    out["elapsed_s"] = time.time() - t0
    return out


def _run_one(args: tuple[str, str]) -> str:
    tracks_csv, name = args
    res = process_recording(tracks_csv, name)
    path = RUNS / name / (Path(tracks_csv).name.split("_")[0] + ".json")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(res), encoding="utf-8")
    os.replace(tmp, path)
    return f"{res['rec']} done ({res['elapsed_s']:.0f} s)"


def _done(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(json.loads(path.read_text(encoding="utf-8"))["settings"] == SETTINGS)
    except (ValueError, KeyError):
        return False


def aggregate(name: str, ids: list[str]) -> None:
    """Sum the per-recording files into ``docs/diamond_<name>.md`` and ``.json``."""
    runs = [json.loads((RUNS / name / f"{i}.json").read_text(encoding="utf-8")) for i in ids]
    counts: dict[tuple[str, str], np.ndarray] = {}
    meta: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    seconds: dict[str, float] = defaultdict(float)
    scale_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in runs:
        loc = r["loc"]
        seconds[loc] += r["seconds"]
        if r["scale"]:
            scale_rows[loc].append(r["scale"])
        for cls, c in r["classes"].items():
            key = (loc, cls)
            arr = np.array(c["counts"], dtype=np.int64)
            counts[key] = counts[key] + arr if key in counts else arr
            meta[key] = (c["levels"], c["severity_classes"])
    lines = [f"# Empirical hierarchy and prediction-error scales: {name}", "",
             f"*Generated by `tools/levelx_diamond.py`; do not edit by hand. Recordings: {len(ids)}; "
             f"horizon {HORIZON:g} s; candidate pairs: centres within {MAX_DIST:g} m or 10 s future "
             "paths within 6 m; pedestrian/bicycle pairs among themselves are not analysed. Aggregates only. " + LICENCE_NOTE.get(name, "The data are not redistributed (licence: "
             "non-commercial research use).") + " Descriptive: nothing here validates an indicator.*", ""]  # fmt: skip
    out: dict[str, object] = {"dataset": name, "recordings": len(ids)}
    for loc in sorted({k[0] for k in counts}):
        lines += [f"## Location {loc} ({seconds[loc]:.0f} s observed)", ""]
        for cls in ("motor-motor", "motor-VRU", "VRU-VRU"):
            if (loc, cls) not in counts:
                continue
            levels, classes = meta[(loc, cls)]
            cnt = counts[(loc, cls)]
            h = hierarchy.Hierarchy(levels=levels, severity_classes=classes, counts=cnt,
                                    level_index=np.zeros(0, dtype=np.int64), edges=EDGES)  # fmt: skip
            lines += [f"### {cls}: {int(cnt.sum()):,} candidate pairs", "", h.table(), ""]
            out[f"{loc}/{cls}"] = {"levels": levels, "counts": cnt.tolist(), "classes": classes}
        if scale_rows[loc]:
            n = np.array([r["n"] for r in scale_rows[loc]], dtype=float)
            sd = np.array([r["sd"] for r in scale_rows[loc]], dtype=float)
            se = np.array([r["se"] for r in scale_rows[loc]], dtype=float)
            n_tot = n.sum(axis=0)
            w = n / np.where(n_tot > 0, n_tot, np.nan)
            lines += ["### Prediction-error scales of unhindered motor vehicles (RMS, pooled over recordings)", "",
                      "| tau (s) | sigma_delta (s) | sigma_eps (m) | samples |", "|---|---|---|---|"]  # fmt: skip
            for k, tau in enumerate(TAUS):
                pd = (
                    float(np.sqrt(np.nansum(w[:, k] * sd[:, k] ** 2)))
                    if n_tot[k] >= 100
                    else float("nan")
                )
                pe = (
                    float(np.sqrt(np.nansum(w[:, k] * se[:, k] ** 2)))
                    if n_tot[k] >= 100
                    else float("nan")
                )
                lines.append(f"| {tau:g} | {pd:.3f} | {pe:.3f} | {int(n[:, k].sum()):,} |")
            lines.append("")
            out[f"{loc}/scales"] = {"tau": list(TAUS), "sigma_delta": [float(np.sqrt(np.nansum(w[:, k] * sd[:, k] ** 2))) if n_tot[k] >= 100 else None for k in range(len(TAUS))],
                                    "sigma_eps": [float(np.sqrt(np.nansum(w[:, k] * se[:, k] ** 2))) if n_tot[k] >= 100 else None for k in range(len(TAUS))]}  # fmt: skip
    Path(f"docs/diamond_{name}.md").write_text("\n".join(lines), encoding="utf-8")
    Path(f"docs/diamond_{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def main(name: str, limit: int | None, workers: int) -> None:
    root = Path("data_raw") / FOLDERS[name] / "data"
    files = sorted(
        glob.glob(str(root / "*_tracks.csv")), key=lambda f: int(Path(f).name.split("_")[0])
    )
    files = files[: limit or len(files)]
    ids = [Path(f).name.split("_")[0] for f in files]
    (RUNS / name).mkdir(parents=True, exist_ok=True)
    todo = [
        (f, name) for f, i in zip(files, ids, strict=True) if not _done(RUNS / name / f"{i}.json")
    ]
    print(f"{name}: {len(files)} recordings, {len(files) - len(todo)} already done, "
          f"{len(todo)} to run on {workers} workers", flush=True)  # fmt: skip
    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_run_one, a) for a in todo]
            for k, fu in enumerate(as_completed(futs), 1):
                print(f"[{k}/{len(todo)}] {fu.result()} total {time.time() - t0:.0f} s", flush=True)
    aggregate(name, ids)
    print(f"written docs/diamond_{name}.md ({time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(FOLDERS))
    ap.add_argument("limit", nargs="?", type=int, default=None, help="first N recordings only")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    main(a.name, a.limit, a.workers)
