"""Build the conflict bank shipped with the package from the unpacked NGSIM archives.

Usage: ``python tools/build_conflict_bank.py [--workers N]`` (after the archives were unpacked to
``data_raw/ngsim/<site>/``; see ``docs/ngsim_notes.md``). Every period is processed in its own child
process (windows of the period go to ``runs_local/bank/<site>_<period>.npz``, resumable), then the
parts are joined. Writes into ``src/pyssms/data/``:

* ``conflict_bank_ngsim.npz``: windows around the most severe encounters of every period of
  US-101, I-80, Lankershim and Peachtree (causal smoothing, 5 frames; see ``pyssms.bank`` for what
  that bank is and is not);
* ``NGSIM_LICENSE.txt`` and ``NGSIM_CC-BY-2.0_legalcode.html``: the licence text of the archives,
  copied unchanged (the plain text is only the visible text of ``ngsim-license.htm``);
* ``summary_levelx.json``: counts and scales of the five German data sets, copied from
  ``docs/diamond_*.json`` (aggregates only).
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from pyssms import bank, io, preprocessing

SITES = ("US-101", "I-80", "Lankershim", "Peachtree")
OUT = Path("src/pyssms/data")
PARTS = Path("runs_local") / "bank"


def plain(path: Path) -> str:
    t = path.read_text(encoding="latin-1")
    t = re.sub(r"(?is)<(script|style).*?</\1>", "", t)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()


def one(txt: str, site: str) -> None:
    period = Path(txt).parent.name
    tr = preprocessing.smooth_trajectories(io.read_ngsim(txt), window=5, causal=True)
    b = bank.extract_conflicts(tr, name="ngsim", site=site, period=period)
    PARTS.mkdir(parents=True, exist_ok=True)
    bank.save_bank(b, PARTS / f"{site}_{period}.npz")
    print(site, period, len(b), {lv: len(b.select(lv)) for lv in "ABC"}, flush=True)


def main(workers: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    for site in SITES:
        pat = f"data_raw/ngsim/{site}/vehicle-trajectory-data/*/trajectories-*.txt"
        files += [(f, site) for f in sorted(glob.glob(pat))]
    todo = [(f, s) for f, s in files if not (PARTS / f"{s}_{Path(f).parent.name}.npz").exists()]
    print(f"{len(files)} periods, {len(todo)} to extract", flush=True)
    running: list[subprocess.Popen[bytes]] = []
    queue = list(todo)
    while queue or running:
        while queue and len(running) < workers:
            f, s = queue.pop(0)
            running.append(subprocess.Popen([sys.executable, __file__, "--one", f, s]))
        running = [p for p in running if p.poll() is None]
        time.sleep(2)
    parts = []
    for f, s in files:
        with np.load(PARTS / f"{s}_{Path(f).parent.name}.npz", allow_pickle=False) as z:
            parts.append(bank._read_bank(z))
    info = (
        "NGSIM (FHWA Next Generation Simulation program), licence: modified Creative Commons "
        "Attribution 2.0, credit FHWA and NGSIM, reuse subject to the same licence (see "
        "NGSIM_LICENSE.txt). Windows of +-5 s around the most severe encounters of each period "
        "(not a random sample). Feet converted to metres, front-centre reference moved to the "
        "body centre, positions smoothed with a causal 5-frame trailing mean, local origin."
    )
    merged = bank.concat_banks(parts, "ngsim", info)
    path = bank.save_bank(merged, OUT / "conflict_bank_ngsim.npz")
    print("windows", len(merged), "file", path, f"{path.stat().st_size / 1e6:.2f} MB")

    first = Path("data_raw/ngsim/US-101")
    text = plain(first / "ngsim-license.htm")
    (OUT / "NGSIM_LICENSE.txt").write_text(
        "NGSIM data licence, copied from ngsim-license.htm of the FHWA archives "
        "(US-101, I-80, Lankershim, Peachtree carry the same text):\n\n" + text + "\n\n"
        "The windows in conflict_bank_ngsim.npz are derived from these data: feet converted to "
        "metres, reference point moved from the front centre to the body centre, positions "
        "smoothed and shifted to a local origin. Any reuse or distribution of them is subject to "
        "the licence above.\n",
        encoding="utf-8",
    )
    shutil.copyfile(first / "creative-commons-deed.html", OUT / "NGSIM_CC-BY-2.0_legalcode.html")

    summary = {}
    for name in ("inD", "rounD", "uniD", "exiD", "highD"):
        summary[name] = json.loads(Path(f"docs/diamond_{name}.json").read_text(encoding="utf-8"))
    summary["_note"] = (
        "Counts of candidate pairs per hierarchy level and RMS prediction-error scales of the "
        "five LevelX data sets (RWTH Aachen / fka); aggregates only, produced by "
        "tools/levelx_diamond.py with the settings in docs/diamond_*.md."
    )
    (OUT / "summary_levelx.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print("summary written")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--one", nargs=2, metavar=("FILE", "SITE"))
    a = ap.parse_args()
    if a.one:
        one(a.one[0], a.one[1])
    else:
        main(a.workers)
