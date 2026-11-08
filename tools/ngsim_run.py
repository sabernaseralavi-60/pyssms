"""Empirical hierarchy and prediction-error scales on the NGSIM data (FHWA), per period, resumable.

Usage: ``python tools/ngsim_run.py [--raw] [--workers N] [--only SITE]`` (sites: US-101, I-80,
Lankershim, Peachtree). Files are read from ``data_raw/ngsim/<site>/vehicle-trajectory-data/*/``
(the unpacked FHWA archives; the licence text of each archive, CC BY 2.0 with credit to FHWA and
NGSIM, is in the same folders). By default the positions are smoothed with a **causal** trailing mean
of 5 frames (0.5 s, :func:`pyssms.preprocessing.smooth_trajectories`) before anything is computed;
``--raw`` skips the smoothing and writes to ``NGSIM_raw`` (a sensitivity check). Per period the
aggregates are written to ``runs_local/diamond/<NGSIM|NGSIM_raw>/<site>_<period>.json`` and finally
summed into ``docs/diamond_NGSIM.md`` / ``.json``. Descriptive; nothing here validates an indicator.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import levelx_diamond as ld

from pyssms import io, preprocessing

SITES = ("US-101", "I-80", "Lankershim", "Peachtree")
WINDOW = 5


def _settings(raw: bool) -> dict[str, object]:
    return dict(ld.SETTINGS, source="ngsim", window=None if raw else WINDOW, causal=True)


def run_one(args: tuple[str, str, bool]) -> str:
    txt, site, raw = args
    period = Path(txt).parent.name
    name = "NGSIM_raw" if raw else "NGSIM"
    tr = io.read_ngsim(txt)
    if not raw:
        tr = preprocessing.smooth_trajectories(tr, window=WINDOW, causal=True)
    res = ld.process_trajectories(tr, name, f"{site}_{period}", site)
    res["settings"] = _settings(raw)
    path = ld.RUNS / name / f"{site}_{period}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(res), encoding="utf-8")
    os.replace(tmp, path)
    return f"{site} {period} done ({res['elapsed_s']:.0f} s)"


def main(raw: bool, workers: int, only: str | None) -> None:
    name = "NGSIM_raw" if raw else "NGSIM"
    files: list[tuple[str, str]] = []
    for site in SITES:
        if only and site != only:
            continue
        for f in sorted(glob.glob(f"data_raw/ngsim/{site}/vehicle-trajectory-data/*/trajectories-*.txt")):
            files.append((f, site))
    ids = [f"{s}_{Path(f).parent.name}" for f, s in files]
    todo = []
    for (f, s), i in zip(files, ids, strict=True):
        p = ld.RUNS / name / f"{i}.json"
        done = p.exists() and json.loads(p.read_text(encoding="utf-8")).get("settings") == _settings(raw)
        if not done:
            todo.append((f, s, raw))
    print(f"{name}: {len(files)} periods, {len(todo)} to run, {workers} at a time", flush=True)
    t0 = time.time()
    # one child process per period 
    running: list[tuple[subprocess.Popen[bytes], str]] = []
    queue = list(todo)
    finished = 0
    while queue or running:
        while queue and len(running) < workers:
            f, s_, r_ = queue.pop(0)
            cmd = [sys.executable, __file__, "--one", f, s_] + (["--raw"] if r_ else [])
            running.append((subprocess.Popen(cmd), f"{s_} {Path(f).parent.name}"))
        for item in list(running):
            if item[0].poll() is not None:
                running.remove(item)
                finished += 1
                print(f"[{finished}/{len(todo)}] {item[1]} exit {item[0].returncode} "
                      f"total {time.time() - t0:.0f} s", flush=True)
        time.sleep(2)
    ld.aggregate(name, ids)
    print(f"written docs/diamond_{name}.md ({time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", choices=SITES, default=None)
    ap.add_argument("--one", nargs=2, metavar=("FILE", "SITE"), help="process a single file")
    a = ap.parse_args()
    if a.one:
        print(run_one((a.one[0], a.one[1], a.raw)), flush=True)
    else:
        main(a.raw, a.workers, a.only)
