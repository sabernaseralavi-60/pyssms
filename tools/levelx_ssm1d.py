"""Descriptive statistics of the ten car-following measures (``pyssms.ssm1d``) on LevelX data.

Usage: ``python tools/levelx_ssm1d.py highD [limit] [--workers N]`` (also ``exiD``).

For every recording the follower-leader pairs given by the data set itself are taken: ``precedingId``
(highD; the vehicle ahead in the same lane) or ``leadId`` (exiD; kept only if the leader is ahead
and within the follower's width, see ``LATERAL_MAX``). A pair-frame is kept where the clear gap
along the follower's heading is positive. Every ``SAMPLE_STEP`` frames (1 s) the ten measures are
computed with the parameters fixed below **before the run**, together with the polygon indicators
of the same pair (TTC, TAdv, T2, TG, lateral margin, signed margin beta, required braking). Per
recording the sample is stored in ``runs_local/ssm1d/<name>/NN.npz`` (git-ignored, resumable); the
report ``docs/<name>_ssm1d_descriptive.md`` (+ ``.json``) holds aggregates only. **Descriptive:
nothing here validates a measure** (no outcome variable is used).
"""

from __future__ import annotations

import glob
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from pyssms import io, rectangle, ssm1d
from pyssms.disturbance import disturbance_set
from pyssms.escape import required_braking
from pyssms.timetime import indicators

FOLDERS = {"exiD": "exiD-dataset-v2.1", "highD": "highD-dataset-v1.0"}
# ---- fixed before the run (assumptions of the stories, not data; the 2025 paper gives no values)
PARAMS = {"reaction": 1.0, "dec_l": 6.0, "dec_f": 6.0}  # s, m/s^2, m/s^2
ALT_PARAMS = {
    "reaction": 1.5,
    "dec_l": 4.0,
    "dec_f": 4.0,
}  # sensitivity: slower driver, gentler braking
HORIZON = 10.0  # s: a time-valued measure beyond this is treated as undefined (as for the polygon)
SAMPLE_STEP = 25  # frames (1 s at 25 Hz)
LATERAL_MAX = 0.5  # m beyond the half-sum of the widths (exiD leaders only)
GAP_MAX = 200.0  # m: pair-frames with a larger clear gap are not used
SCALE_TAU = 2.0  # s: the prediction-error scales used for beta
MEASURES = ("ttc1", "ttc2", "ttc3", "ttcd", "drac", "mdrac", "psd", "mpsd", "sdi", "dcia")
K_NAMES = ("k_ttc", "k_tadv", "k_t2", "k_tg", "lat_margin", "beta", "req_brake")
RUNS = Path("runs_local") / "ssm1d"
RB_BLOCK = 2000  # rows per call of the required-braking search
VERSION = 1


def _cols(path: str, names: list[str]) -> dict[str, np.ndarray]:
    return io._numeric_columns(Path(path), names)


def _load(name: str, tracks_csv: str) -> dict[str, np.ndarray]:
    """Rows sorted by (id, frame) with centre, unit direction, size, speed, acceleration, lead id."""
    if name == "highD":
        c = _cols(tracks_csv, ["id", "frame", "x", "y", "width", "height", "xVelocity",
                               "yVelocity", "xAcceleration", "yAcceleration", "dhw",
                               "precedingId"])  # fmt: skip
        length, width = c["width"], c["height"]
        cx, cy = c["x"] + length / 2.0, c["y"] + width / 2.0
        uid = c["id"].astype(np.int64)
        sign = np.sign(c["xVelocity"])
        # one travel direction per vehicle (the sign of its mean longitudinal speed)
        ids, inv = np.unique(uid, return_inverse=True)
        mean_sign = np.sign(np.bincount(inv, weights=sign) / np.maximum(np.bincount(inv), 1))
        ux, uy = mean_sign[inv], np.zeros(uid.size)
        lead, extra = c["precedingId"].astype(np.int64), c["dhw"]
    else:
        c = _cols(tracks_csv, ["trackId", "frame", "xCenter", "yCenter", "heading", "width",
                               "length", "xVelocity", "yVelocity", "xAcceleration",
                               "yAcceleration", "leadId", "leadDHW"])  # fmt: skip
        length, width = c["length"], c["width"]
        cx, cy = c["xCenter"], c["yCenter"]
        uid = c["trackId"].astype(np.int64)
        h = np.deg2rad(c["heading"])
        ux, uy = np.cos(h), np.sin(h)
        lead, extra = c["leadId"].astype(np.int64), c["leadDHW"]
    frame = c["frame"].astype(np.int64)
    order = np.lexsort((frame, uid))
    out = {"uid": uid, "frame": frame, "cx": cx, "cy": cy, "ux": ux, "uy": uy, "length": length,
           "width": width, "vx": c["xVelocity"], "vy": c["yVelocity"], "ax": c["xAcceleration"],
           "ay": c["yAcceleration"], "lead": lead, "extra": extra}  # fmt: skip
    return {k: v[order] for k, v in out.items()}


def _jerk_along(a: np.ndarray, run_start: np.ndarray, dt: float) -> np.ndarray:
    """Finite-difference derivative of ``a`` within runs (central inside, one-sided at the ends)."""
    n = a.size
    j = np.full(n, np.nan)
    same_next = np.zeros(n, dtype=bool)
    same_next[:-1] = ~run_start[1:]
    same_prev = np.zeros(n, dtype=bool)
    same_prev[1:] = ~run_start[1:]
    nxt = np.append(a[1:], np.nan)
    prv = np.insert(a[:-1], 0, np.nan)
    both = same_next & same_prev
    j = np.where(both, (nxt - prv) / (2 * dt), j)
    j = np.where(~both & same_next, (nxt - a) / dt, j)
    j = np.where(~both & same_prev, (a - prv) / dt, j)
    return j


def measures_of(gap, v_l, v_f, a_l, a_f, j_l, j_f, p: dict[str, float]) -> dict[str, np.ndarray]:
    """The ten measures for arrays of pair-frames (parameters ``p``)."""
    dcia, _ = ssm1d.dcia(gap, v_l, v_f, a_l, a_f, p["reaction"])
    return {
        "ttc1": ssm1d.ttc_poly(gap, v_l, v_f),
        "ttc2": ssm1d.ttc_poly(gap, v_l, v_f, a_l, a_f),
        "ttc3": ssm1d.ttc_poly(gap, v_l, v_f, a_l, a_f, j_l, j_f),
        "ttcd": ssm1d.ttcd(gap, v_l, v_f, p["dec_l"]),
        "drac": ssm1d.drac(gap, v_l, v_f),
        "mdrac": ssm1d.mdrac(gap, v_l, v_f, p["reaction"]),
        "psd": ssm1d.psd(gap, v_f, p["dec_f"]),
        "mpsd": ssm1d.mpsd(gap, v_f, p["dec_f"], p["reaction"]),
        "sdi": ssm1d.sdi(gap, v_l, v_f, p["dec_l"], p["dec_f"], p["reaction"]),
        "dcia": dcia,
    }


def load_scales(name: str) -> tuple[float, float] | None:
    """Equal-weight RMS over locations of sigma_delta, sigma_eps at tau = 2 s (diamond json)."""
    f = Path("docs") / f"diamond_{name}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    sd, se = [], []
    for k, v in d.items():
        if k.endswith("/scales") and SCALE_TAU in v["tau"]:
            i = v["tau"].index(SCALE_TAU)
            if v["sigma_delta"][i] is not None:
                sd.append(v["sigma_delta"][i] ** 2)
                se.append(v["sigma_eps"][i] ** 2)
    if not sd:
        return None
    return float(np.sqrt(np.mean(sd))), float(np.sqrt(np.mean(se)))


def step_of(name: str) -> int:
    """Sampling step in frames (1 s): 25 frames for the 25 Hz LevelX data, 10 for NGSIM."""
    return 10 if name == "NGSIM" else SAMPLE_STEP


def process_recording(tracks_csv: str, name: str) -> dict[str, Any]:
    base = tracks_csv.replace("_tracks.csv", "")
    rec = io._read_dicts(Path(base + "_recordingMeta.csv"))[0]
    dt = 1.0 / float(rec["frameRate"])
    return process_rows(_load(name, tracks_csv), name, dt, Path(base).name)


def process_rows(r: dict[str, np.ndarray], name: str, dt: float, rec_name: str) -> dict[str, Any]:
    """Measures of every follower-leader pair-frame of rows given as in :func:`_load`."""
    t0 = time.time()
    n = r["uid"].size
    key = r["uid"] * 10_000_000 + r["frame"]  # sorted ascending (rows are sorted by id, frame)
    has_lead = r["lead"] > 0
    lkey = r["lead"] * 10_000_000 + r["frame"]
    pos = np.searchsorted(key, lkey)
    pos = np.minimum(pos, n - 1)
    ok = has_lead & (key[pos] == lkey)
    f_idx = np.flatnonzero(ok)
    l_idx = pos[ok]
    ux, uy = r["ux"][f_idx], r["uy"][f_idx]
    dx, dy = r["cx"][l_idx] - r["cx"][f_idx], r["cy"][l_idx] - r["cy"][f_idx]
    along = dx * ux + dy * uy
    lat = np.abs(-dx * uy + dy * ux)
    gap = along - (r["length"][l_idx] + r["length"][f_idx]) / 2.0
    half_w = (r["width"][l_idx] + r["width"][f_idx]) / 2.0
    keep = (gap > 0) & (gap <= GAP_MAX)
    if name == "exiD":
        keep &= lat <= half_w + LATERAL_MAX
    n_leader_rows = int(ok.sum())
    f_idx, l_idx, ux, uy, gap, lat = (x[keep] for x in (f_idx, l_idx, ux, uy, gap, lat))
    # runs of one (follower, leader) pair on consecutive frames, for the jerk by differences
    fr_f, id_f, id_l = r["frame"][f_idx], r["uid"][f_idx], r["lead"][f_idx]
    run_start = np.ones(f_idx.size, dtype=bool)
    run_start[1:] = (id_f[1:] != id_f[:-1]) | (id_l[1:] != id_l[:-1]) | (fr_f[1:] != fr_f[:-1] + 1)
    v_f = r["vx"][f_idx] * ux + r["vy"][f_idx] * uy
    v_l = r["vx"][l_idx] * ux + r["vy"][l_idx] * uy
    a_f = r["ax"][f_idx] * ux + r["ay"][f_idx] * uy
    a_l = r["ax"][l_idx] * ux + r["ay"][l_idx] * uy
    j_f, j_l = _jerk_along(a_f, run_start, dt), _jerk_along(a_l, run_start, dt)
    sel = (fr_f % step_of(name)) == 0
    sel &= np.isfinite(j_f) & np.isfinite(j_l)  # the jerk needs a neighbouring frame of the pair
    f_idx, l_idx, ux, uy, gap, lat, v_f, v_l, a_f, a_l, j_f, j_l = (
        x[sel] for x in (f_idx, l_idx, ux, uy, gap, lat, v_f, v_l, a_f, a_l, j_f, j_l)
    )
    out: dict[str, np.ndarray] = {
        "frame": r["frame"][f_idx], "follower": r["uid"][f_idx], "leader": r["uid"][l_idx],
        "gap": gap, "v_f": v_f, "v_l": v_l, "a_f": a_f, "a_l": a_l, "lat": lat,
        "ref_dhw": r["extra"][f_idx],
    }  # fmt: skip
    for k, v in measures_of(gap, v_l, v_f, a_l, a_f, j_l, j_f, PARAMS).items():
        out[k] = v
    for k, v in measures_of(gap, v_l, v_f, a_l, a_f, j_l, j_f, ALT_PARAMS).items():
        out["alt_" + k] = v
    # ---- polygon indicators of the same pairs (follower = road user 1, leader = road user 2)
    m = f_idx.size
    h1 = np.arctan2(uy, ux)
    s1 = rectangle(h1, r["length"][f_idx], r["width"][f_idx])
    s2 = rectangle(h1, r["length"][l_idx], r["width"][l_idx])
    p1 = np.stack([r["cx"][f_idx], r["cy"][f_idx]], -1)
    p2 = np.stack([r["cx"][l_idx], r["cy"][l_idx]], -1)
    u1 = np.stack([r["vx"][f_idx], r["vy"][f_idx]], -1)
    u2 = np.stack([r["vx"][l_idx], r["vy"][l_idx]], -1)
    if m:
        k = indicators(s1, p1, u1, s2, p2, u2, horizon=HORIZON)
        out.update(k_ttc=k.ttc, k_tadv=k.tadv, k_t2=k.t2, k_tg=k.tg)
        out["k_state"] = (k.state == "A").astype(np.int8) + 2 * (k.state == "B").astype(np.int8)
        normal2 = np.stack([-uy, ux], -1)
        d = disturbance_set(s1, p1, u1, s2, p2, u2, normal2, horizon=HORIZON)
        out["lat_margin"] = d.lateral_margin()
        sc = load_scales(name)
        out["beta"] = d.signed_margin(*sc) if sc else np.full(m, np.nan)
        # required braking in blocks: the story search iterates until the slowest row converges,
        # so one huge call is superlinear (a 110k-row NGSIM period did not finish in 90 min)
        dirs = np.stack([ux, uy], -1)
        sp1, sp2 = np.hypot(*u1.T), np.hypot(*u2.T)
        rb = np.empty(m)
        for b0 in range(0, m, RB_BLOCK):
            b = slice(b0, b0 + RB_BLOCK)
            rb[b] = required_braking(
                s1[b], p1[b], dirs[b], sp1[b], s2[b], p2[b], dirs[b], sp2[b], 1, horizon=HORIZON
            )
        out["req_brake"] = rb
    else:
        for kk in (*K_NAMES, "k_state"):
            out[kk] = np.zeros(0)
    out = {
        k: np.asarray(v, dtype=np.float32 if v.dtype.kind == "f" else v.dtype)
        for k, v in out.items()
    }
    out["_meta"] = np.array(json.dumps({
        "version": VERSION, "rec": rec_name, "n_rows": n, "n_leader_rows": n_leader_rows,
        "n_pair_frames": int(keep.sum()), "n_sample": int(m), "params": PARAMS,
        "alt_params": ALT_PARAMS, "horizon": HORIZON, "step": step_of(name), "elapsed_s": time.time() - t0,
        "beta_scales": load_scales(name),
    }))  # fmt: skip
    return out


def _run_one(args: tuple[str, str]) -> str:
    tracks_csv, name = args
    res = process_recording(tracks_csv, name)
    path = RUNS / name / (Path(tracks_csv).name.split("_")[0] + ".npz")
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez(tmp, **res)
    os.replace(tmp, path)
    meta = json.loads(str(res["_meta"]))
    return f"{meta['rec']}: {meta['n_pair_frames']:,} pair-frames, sample {meta['n_sample']:,} ({meta['elapsed_s']:.0f} s)"


def _done(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with np.load(path) as z:
            m = json.loads(str(z["_meta"]))
        return bool(m["version"] == VERSION and m["params"] == PARAMS and m["step"] in (SAMPLE_STEP, step_of("NGSIM")))
    except (ValueError, KeyError, OSError):
        return False


def main(name: str, limit: int | None, workers: int) -> None:
    root = Path("data_raw") / FOLDERS[name] / "data"
    files = sorted(
        glob.glob(str(root / "*_tracks.csv")), key=lambda f: int(Path(f).name.split("_")[0])
    )
    files = files[: limit or len(files)]
    ids = [Path(f).name.split("_")[0] for f in files]
    (RUNS / name).mkdir(parents=True, exist_ok=True)
    todo = [
        (f, name) for f, i in zip(files, ids, strict=True) if not _done(RUNS / name / f"{i}.npz")
    ]
    print(f"{name}: {len(files)} recordings, {len(files) - len(todo)} done, {len(todo)} to run; "
          f"beta scales: {load_scales(name)}", flush=True)  # fmt: skip
    t0 = time.time()
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_run_one, a) for a in todo]
            for k, fu in enumerate(as_completed(futs), 1):
                print(f"[{k}/{len(todo)}] {fu.result()} total {time.time() - t0:.0f} s", flush=True)
    print("per-recording files done", flush=True)
    import levelx_ssm1d_report  # noqa: PLC0415 (imports this module; kept lazy)

    levelx_ssm1d_report.report(name, ids)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(FOLDERS))
    ap.add_argument("limit", nargs="?", type=int, default=None, help="first N recordings only")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    main(a.name, a.limit, a.workers)
