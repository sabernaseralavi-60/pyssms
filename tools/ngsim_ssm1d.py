"""Descriptive statistics of the ten car-following measures on the NGSIM freeway data (US-101, I-80).

Usage: ``python tools/ngsim_ssm1d.py [--workers N]``. Same procedure and report as
``tools/levelx_ssm1d.py`` (parameters fixed in that file before any run; sample every second; polygon
indicators of the same pairs), with the NGSIM-specific decisions **fixed before the run**:

* leader = the data set's ``Preceding Vehicle`` (column 15; same lane), kept where the clear gap along
  the follower's heading is positive and at most ``GAP_MAX``;
* positions: front centre moved to the body centre (``pyssms.io.read_ngsim``, local coordinates),
  then a causal 5-frame trailing mean (``pyssms.preprocessing``); speed: backward difference of the
  smoothed position; acceleration: causal 5-frame mean of the backward difference of the speed;
  the data set's own speed and acceleration columns are not used for the measures (they are known to
  be inconsistent with the positions);
* the arterial sites (Lankershim, Peachtree) are not used because their preceding-vehicle column has
  another position in the file.

Per period the sample goes to ``runs_local/ssm1d/NGSIM/<site>_<period>.npz`` (git-ignored, resumable)
and the report to ``docs/ngsim_ssm1d_descriptive.md`` / ``.json`` (aggregates only). Descriptive: no
outcome is used, so nothing here validates a measure. Needs ``docs/diamond_NGSIM.json`` (the
prediction-error scales for the signed margin), i.e. ``tools/ngsim_run.py`` must have finished.
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time
from pathlib import Path

import levelx_ssm1d as L
import numpy as np

from pyssms import io, preprocessing

SITES = ("US-101", "I-80")
NAME = "NGSIM"
FT = 0.3048


def load_rows(txt: str) -> dict[str, np.ndarray]:
    """Rows sorted by (id, frame) in the layout of ``levelx_ssm1d._load``."""
    raw = np.loadtxt(txt, usecols=(0, 1, 14, 16), ndmin=2)  # id, frame, preceding id, spacing (ft)
    tr = preprocessing.smooth_trajectories(io.read_ngsim(txt, coordinates="local"), 5, causal=True)
    uid = tr.uid
    frame = np.rint(tr.t * 10).astype(np.int64)
    if not (np.array_equal(raw[:, 0].astype(np.int64), uid)):
        raise RuntimeError("row order of read_ngsim differs from the file")
    lead = raw[:, 2].astype(np.int64)
    # acceleration: causal mean (5 frames) of the backward difference of the speed, per vehicle
    order = np.lexsort((frame, uid))
    vx, vy = tr.vx[order], tr.vy[order]
    u_s = uid[order]
    new = np.r_[True, u_s[1:] != u_s[:-1]]
    ax = np.zeros_like(vx)
    ay = np.zeros_like(vy)
    ax[1:] = (vx[1:] - vx[:-1]) / 0.1
    ay[1:] = (vy[1:] - vy[:-1]) / 0.1
    ax[new], ay[new] = 0.0, 0.0
    starts = np.flatnonzero(new)
    stops = np.r_[starts[1:], u_s.size]
    for s0, s1 in zip(starts, stops, strict=True):
        ax[s0:s1] = preprocessing.moving_average(ax[s0:s1], 5, causal=True)
        ay[s0:s1] = preprocessing.moving_average(ay[s0:s1], 5, causal=True)
    ux, uy = np.cos(tr.heading), np.sin(tr.heading)
    # our clear gap equals spacing minus the leader's length; the leader's length is looked up below
    spacing = raw[:, 3] * FT
    out = {
        "uid": uid, "frame": frame, "cx": tr.x, "cy": tr.y, "ux": ux, "uy": uy,
        "length": tr.length, "width": tr.width, "vx": tr.vx, "vy": tr.vy,
        "ax": np.empty_like(tr.vx), "ay": np.empty_like(tr.vy), "lead": lead, "extra": spacing,
    }  # fmt: skip
    out["ax"][order], out["ay"][order] = ax, ay
    o = np.lexsort((frame, uid))
    out = {k: v[o] for k, v in out.items()}
    # the reference column: spacing minus the length of the leader (same frame)
    key = out["uid"] * 10_000_000 + out["frame"]
    lk = out["lead"] * 10_000_000 + out["frame"]
    pos = np.minimum(np.searchsorted(key, lk), key.size - 1)
    ok = (out["lead"] > 0) & (key[pos] == lk)
    ref = np.where(ok, out["extra"] - out["length"][pos], 0.0)
    out["extra"] = np.where(out["extra"] > 0, ref, 0.0)
    return out


def run_one(args: tuple[str, str]) -> str:
    txt, site = args
    period = Path(txt).parent.name
    r = load_rows(txt)
    res = L.process_rows(r, NAME, 0.1, f"{site}_{period}")
    path = L.RUNS / NAME / f"{site}_{period}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.npz")
    np.savez(tmp, **res)
    os.replace(tmp, path)
    import json

    m = json.loads(str(res["_meta"]))
    return f"{site} {period}: {m['n_pair_frames']:,} pair-frames, sample {m['n_sample']:,} ({m['elapsed_s']:.0f} s)"


def main(workers: int) -> None:
    files = []
    for site in SITES:
        for f in sorted(glob.glob(f"data_raw/ngsim/{site}/vehicle-trajectory-data/*/trajectories-*.txt")):
            files.append((f, site))
    ids = [f"{s}_{Path(f).parent.name}" for f, s in files]
    todo = [(f, s) for (f, s), i in zip(files, ids, strict=True)
            if not L._done(L.RUNS / NAME / f"{i}.npz")]  # fmt: skip
    print(f"NGSIM ssm1d: {len(files)} periods, {len(todo)} to run", flush=True)
    t0 = time.time()
    running: list[tuple[subprocess.Popen[bytes], str]] = []
    queue = list(todo)
    while queue or running:
        while queue and len(running) < workers:
            f, s = queue.pop(0)
            running.append((subprocess.Popen([sys.executable, __file__, "--one", f, s]), f"{s} {Path(f).parent.name}"))
        for item in list(running):
            if item[0].poll() is not None:
                running.remove(item)
                print(f"{item[1]} exit {item[0].returncode} total {time.time() - t0:.0f} s", flush=True)
        time.sleep(2)
    import levelx_ssm1d_report as R

    R.report(NAME, ids)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--one", nargs=2, metavar=("FILE", "SITE"))
    a = ap.parse_args()
    if a.one:
        print(run_one((a.one[0], a.one[1])), flush=True)
    else:
        main(a.workers)
