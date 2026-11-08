"""Every number of the SoftwareX paper, read from the repository's own result files and written to results.json.

Nothing in the manuscript text is typed by hand: ``content.py`` holds tokens ``{{path/to/key:fmt}}`` only.
Sources (all produced by code in this repository; this script only reads or re-counts):

* docs/{highd,exid,ngsim}_ssm1d_descriptive.json   ten car-following measures (tools/levelx_ssm1d.py, tools/ngsim_ssm1d.py)
* docs/diamond_*.json, src/pyssms/data/summary_levelx.json   hierarchy counts (tools/levelx_diamond.py, tools/ngsim_run.py)
* docs/equivalence.json                              1,000,000-encounter comparison with the printed procedure
* docs/benchmark.md                                  timing (tools/benchmark.py); parsed from the generated table
* docs/ngsim_checks.md                               NGSIM internal consistency (tools/ngsim_checks.py); parsed
* the shipped conflict bank, counted live; the test suite, collected live (pytest --collect-only)

    python paper_softwarex/make_numbers.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = Path(__file__).resolve().parent / "results.json"
R: dict = {}


def jl(name: str) -> dict:
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- ten measures on three freeway data sets
MEAS = ["ttc1", "ttc2", "ttc3", "ttcd", "drac", "mdrac", "psd", "mpsd", "sdi", "dcia"]
for key, fn in (("highd", "highd"), ("exid", "exid"), ("ngsim", "ngsim")):
    d = jl(f"{fn}_ssm1d_descriptive.json")
    r = {
        "recordings": d["recordings"],
        "pair_frames": d["pair_frames"],
        "rows": d["sample_rows"],
        "state": {k: 100 * v for k, v in d["state_share"].items()},
        "gap_abs_max": d["checks"]["gap_minus_dataset_headway"]["abs_max"],
        "gap_p5": d["checks"]["gap_minus_dataset_headway"]["p5_p95"][0],
        "gap_p95": d["checks"]["gap_minus_dataset_headway"]["p5_p95"][1],
        "poly_ttc_maxdiff": d["checks"]["polygon_ttc_vs_ttc1"]["max_abs_diff_s"],
        "ttc1_within_h": d["checks"]["polygon_ttc_vs_ttc1"]["ttc1_within_horizon"],
        "poly_defined": d["checks"]["polygon_ttc_vs_ttc1"]["polygon_ttc_defined_there"],
        "poly_share": 100 * d["checks"]["polygon_ttc_vs_ttc1"]["polygon_ttc_defined_there"] / d["checks"]["polygon_ttc_vs_ttc1"]["ttc1_within_horizon"],
        "m": {},
        "rho": {},
    }
    for m in MEAS:
        x = d["measures"][m]
        r["m"][m] = {
            "defined": 100 * x["defined_share"],
            "p5": x["quantiles"]["5.0"], "p25": x["quantiles"]["25.0"], "p50": x["quantiles"]["50.0"],
            "p75": x["quantiles"]["75.0"], "p95": x["quantiles"]["95.0"],
            "crit": 100 * x["critical_share"] if x.get("critical_share") is not None else float("nan"),
        }
        r["rho"][m] = {c: v["rho"] for c, v in d["spearman"][m].items()}
    r["poly_missing_share"] = 100.0 - r["poly_share"]
    alt = d["alt"]
    r["alt_ttcd_crit"] = [alt["ttcd"][0][2], alt["ttcd"][1][2]]
    r["alt_sdi_crit"] = [alt["sdi"][0][2], alt["sdi"][1][2]]
    R[key] = r
    if key == "highd":  # run settings are read from the run metadata, not typed (A6 of the Opus review, 2026-11-08)
        R["params"] = {"rt": d["params"]["reaction"], "dec_l": d["params"]["dec_l"], "dec_f": d["params"]["dec_f"],
                       "rt_alt": d["alt_params"]["reaction"], "dec_alt": d["alt_params"]["dec_l"], "horizon": d["horizon"],
                       "step_frames": d["step_frames"]}
    else:
        assert d["params"] == jl("highd_ssm1d_descriptive.json")["params"], "run settings differ between data sets"
# ratio of the TTC<=3 s shares: same rows, two stories
for k in ("highd", "exid", "ngsim"):
    R[k]["ratio_ttcd_ttc1"] = R[k]["m"]["ttcd"]["crit"] / R[k]["m"]["ttc1"]["crit"]

# ---------------------------------------------------------------- hierarchy over the six data sets (motor-motor, pooled over sites)
LV = ["A: TTC 0-1.5 s", "A: TTC 1.5-3 s", "A: TTC 3-6 s", "A: TTC > 6 s", "B: TAdv 0-0.5 s", "B: TAdv 0.5-1 s", "B: TAdv 1-1.5 s",
      "B: TAdv 1.5-2 s", "B: TAdv 2-3 s", "B: TAdv 3-4 s", "B: TAdv > 4 s", "C (no overlap)"]


def pooled(block: dict) -> np.ndarray:
    tot = np.zeros(len(LV))
    for k, v in block.items():
        if k.endswith("/motor-motor"):
            assert v["levels"] == LV, k
            tot += np.array(v["counts"]).sum(axis=1)
    return tot


sets = {"inD": None, "rounD": None, "uniD": None, "exiD": None, "highD": None}
summ = jl("../src/pyssms/data/summary_levelx.json")
hier = {}
for name in sets:
    hier[name] = pooled(summ[name])
    R.setdefault("recordings", {})[name] = summ[name]["recordings"]
ng = jl("diamond_NGSIM.json")
hier["NGSIM"] = pooled(ng)
R["recordings"]["NGSIM"] = ng["recordings"]
R["hier"] = {}
for name, v in hier.items():
    tot = v.sum()
    R["hier"][name] = {
        "pairs": int(tot),
        "noC": 100 * (1 - v[-1] / tot),   # historical key: share of pairs WITH overlap (levels A or B)
        "overlap": 100 * (1 - v[-1] / tot),
        "C": 100 * v[-1] / tot,
        "A": 100 * v[:4].sum() / tot,
        "B": 100 * v[4:11].sum() / tot,
        "A_lt15": 100 * v[0] / tot,
        "A_15_3": 100 * v[1] / tot,
        "A_3_6": 100 * v[2] / tot,
        "A_gt6": 100 * v[3] / tot,
        "B_lt1": 100 * v[4:6].sum() / tot,
        "B_1_2": 100 * v[6:8].sum() / tot,
        "B_2_4": 100 * v[8:10].sum() / tot,
        "B_gt4": 100 * v[10] / tot,
        # shares among pairs whose future paths overlap (A or B): the "pyramid" shape
        "share_A_given_overlap": 100 * v[:4].sum() / v[:11].sum(),
        "share_A_lt3_given_A": 100 * v[:2].sum() / v[:4].sum(),
        "share_A36_given_A": 100 * v[2:4].sum() / v[:4].sum(),
    }
R["hier_total_pairs"] = int(sum(v.sum() for v in hier.values()))
R["hier_total_recordings"] = int(sum(R["recordings"].values()))

# NGSIM smoothing sensitivity at Peachtree (raw vs causal 5-frame mean), from the two runs
raw = jl("diamond_NGSIM_raw.json")


def peach(block: dict) -> tuple[float, float]:
    c = np.array(block["counts"]).sum(axis=1)
    return 100 * c[0] / c.sum(), 100 * c[-1] / c.sum()


sm = peach(ng["Peachtree/motor-motor"])
rw = peach(raw["Peachtree/motor-motor"])
R["smooth"] = {"smoothed_ttc15": sm[0], "raw_ttc15": rw[0], "smoothed_C": sm[1], "raw_C": rw[1]}

# ---------------------------------------------------------------- equivalence and speed
eq = jl("equivalence.json")
R["eq_raw_keys"] = list(eq.keys())[:12]
bm = (DOCS / "benchmark.md").read_text(encoding="utf-8")
rows = re.findall(r"^\| ([\d,]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", bm, flags=re.M)
last = [r for r in rows if r[0] == "1,000,000"][0]
R["bench"] = {"n": 1_000_000, "polygon_s": float(last[1]), "vector32_s": float(last[2]), "us_per": float(last[3])}
gen = re.findall(r"^\| ([\d,]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", bm.split("The general 12-row form")[1], flags=re.M)
g1m = [r for r in gen if r[0] == "1,000,000"][0]
R["bench"]["general12_s"] = float(g1m[1])
R["bench"]["ratio12_8"] = float(g1m[3])
R["bench"]["loop_us"] = float(re.search(r"takes (\d+) us per encounter", bm).group(1))
R["bench"]["vector32_us"] = 1e6 * R["bench"]["vector32_s"] / R["bench"]["n"]
R["bench"]["ratio_poly_vec"] = float(re.search(r"takes ([\d.]+) times the time", bm).group(1))

ck = (DOCS / "ngsim_checks.md").read_text(encoding="utf-8")
us = re.search(r"\| US-101 \| [\d,]+ \| ([\d.]+) \| ([\d.]+) \|", ck)
i80 = re.search(r"\| I-80 \| [\d,]+ \| ([\d.]+) \| ([\d.]+) \|", ck)
R["ngsim_acc_rms"] = {"us101": float(us.group(1)), "i80": float(i80.group(1))}

# ---------------------------------------------------------------- the equivalence file (structure read, not assumed)
em = (DOCS / "equivalence.md").read_text(encoding="utf-8")
m = re.search(r"1,000,000 random encounters .*?\(states A/B/C: ([\d,]+) / ([\d,]+) / ([\d,]+)\)\. ([\d,]+) start with overlapping.*?([\d,]+) are compared", em, flags=re.S)
R["equiv"] = {
    "n": 1_000_000,
    "stateA": int(m.group(1).replace(",", "")), "stateB": int(m.group(2).replace(",", "")), "stateC": int(m.group(3).replace(",", "")),
    "overlap_excluded": int(m.group(4).replace(",", "")), "compared": int(m.group(5).replace(",", "")),
}
dis = re.findall(r"^\| (ttc|tadv|t2|tg|first) \| (\d+) \|$", em, flags=re.M)
R["equiv"]["disagree"] = {k: int(v) for k, v in dis}
R["equiv"]["disagree_total"] = sum(R["equiv"]["disagree"].values())
tol = re.search(r"`tol=0`: compared ([\d,]+); disagreements \{'ttc': (\d+), 'tadv': (\d+), 't2': (\d+)", em)
R["equiv"]["axis_literal_ttc_misses"] = int(tol.group(2))
R["equiv"]["axis_compared"] = int(tol.group(1).replace(",", ""))

# ---------------------------------------------------------------- bank and package (counted live)
from pyssms import __version__, datasets  # noqa: E402

b = datasets.load_conflict_bank("ngsim")
lv = np.asarray(b.table["level"])
R["bank"] = {
    "windows": len(b), "A": int((lv == "A").sum()), "B": int((lv == "B").sum()), "C": int((lv == "C").sum()),
    "sites": len(set(np.asarray(b.table["site"]))), "periods": len(set(zip(np.asarray(b.table["site"]), np.asarray(b.table["period"])))),
    "mb": round((ROOT / "src" / "pyssms" / "data" / "conflict_bank_ngsim.npz").stat().st_size / 1e6, 1),
    "rows": int(b.rows.t.size),
    "min_ttc_median_A": float(np.median(np.asarray(b.table["min_ttc"])[lv == "A"])),
    "min_ttc_max_A": float(np.max(np.asarray(b.table["min_ttc"])[lv == "A"])),
    "dist_min_A": float(np.min(np.asarray(b.table["min_distance"])[lv == "A"])),
    "dist_max_A": float(np.max(np.asarray(b.table["min_distance"])[lv == "A"])),
}
R["version"] = __version__

out = subprocess.run([sys.executable, "-I", "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True).stdout
files: dict[str, int] = {}
for line in out.splitlines():
    if "::" in line:
        f = line.split("::")[0].split("/")[-1]
        files[f] = files.get(f, 0) + 1
GROUP = {
    "geometry": ["test_timetime.py", "test_appendix_a.py", "test_invariance.py", "test_propositions.py", "test_margins.py", "test_disturbance.py"],
    "stories": ["test_stories.py", "test_ssm1d.py", "test_escape.py"],
    "contact": ["test_contact.py", "test_jimenez2013.py"],
    "severity": ["test_severity.py", "test_injury_risk.py"],
    "data": ["test_io.py", "test_process.py", "test_ngsim_bank.py"],
    "other": ["test_validation.py", "test_readme.py", "test_smoke.py"],
}
R["tests"] = {g: sum(files.get(f, 0) for f in fs) for g, fs in GROUP.items()}
R["tests"]["total"] = sum(files.values())
assert R["tests"]["total"] == sum(R["tests"][g] for g in GROUP), "a test file is missing from the groups"

# modules (python files of the package, without private ones) and sub-packages
mods = sorted(p.stem for p in (ROOT / "src" / "pyssms").glob("*.py") if not p.stem.startswith("_"))
R["modules"] = {"n": len(mods), "names": mods, "subpackages": 2}
R["loc"] = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (ROOT / "src" / "pyssms").rglob("*.py"))

OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
print("wrote", OUT, "| tests", R["tests"], "| modules", R["modules"]["n"], "| bank", R["bank"])
