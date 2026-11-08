# pyssms

![status](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-BSD--3--Clause-green)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24050397.svg)](https://doi.org/10.5281/zenodo.24050397)

Continuous surrogate safety indicators for road-user encounters: Time-to-Collision (TTC), Time
Advantage (TAdv, a predicted PET), T2 and Time Gap (TG) as defined by Laureshyn, Svensson and
Hydén (2010), for any approach angle and any convex body shape, computed exactly on one
time-time conflict polygon.

> **Status.** Version 0.1.0 is the initial release of the package. It covers the four indicators of the 2010 framework for
> constant-velocity prediction of two translating convex bodies (verified against an independent implementation of the
> paper's Appendix A and a brute-force grid oracle: [docs/equivalence.md](docs/equivalence.md)), the ten car-following
> measures of the 2025 framework, trajectory readers for SSAM, SUMO, VISSIM, LevelX and NGSIM, and a bank of NGSIM
> conflict windows. All statistics produced by the tools are descriptive: the indicators are not validated against observed
> outcomes here. Install with `pip install pyssms`. The accompanying article is in [paper_softwarex/](paper_softwarex/).

## What it does

```python
import numpy as np
from pyssms import indicators_rect

# car 1 at (-20, 0) heading east at 10 m/s; car 2 at (0, -30) heading north at 10 m/s; 4.5 x 1.8 m
k = indicators_rect(-20, 0, 0, 10, 0, 4.5, 1.8,  0, -30, np.pi / 2, 0, 10, 4.5, 1.8)
k.state, k.ttc, k.tadv, k.t2, k.tg   # ['B'], [nan], [0.37], [2.685], [2.685]  (crossing course)
```

All inputs may be arrays of encounters; computation is vectorised.

## Coverage (what exists today)

| Measure | Module | Status |
|---|---|---|
| TTC, TAdv, T2, TG, state A/B/C (Laureshyn et al. 2010), any angle, any convex shape | `timetime` | verified against Appendix A (1e6 encounters) |
| Injury risk curves for pedestrians, cyclists, motorcyclists, car drivers (Lubbe et al. 2022) | `severity` | safe speeds of the paper reproduced within coefficient rounding |
| Disturbance set D, signed margin beta, Time Advantage and lateral margin as its axis readings | `disturbance` | consistent with `timetime` and `margins`; brute-force membership check; scales are inputs |
| Smallest braking that avoids a contact (shape-aware DRAC relative) | `escape` | braking curve vs conflict polygon and vs `stories`; analytic stopping case |
| Delta-V, Extended Delta-V (Laureshyn et al. 2017) | `severity` | 18 of 20 printed Table 1 rows reproduced; 2 documented gaps |
| TTC1, TTC2, TTC3, TTCD, DRAC, MDRAC, DCIA, PSD, MPSD, SDI (Naseralavi et al. 2025), car following | `ssm1d` | tested against simulations of their stories; printed-form differences in `docs/ssm1d_notes.md` |
| Motion stories (constant speed, acceleration, jerk) and first contact on straight paths | `stories` | equals `timetime` for constant speed; brute-force check for braking |
| Time margin (TAdv) and lateral margin | `timetime`, `margins` | lateral margin checked against the independent polygon code |
| Trajectory readers: SSAM `.trj` (read and write), LevelX (inD, rounD, exiD, uniD, highD), SUMO FCD, VISSIM `.fzp`, generic table | `io` | round trips on synthetic files; the LevelX readers were run on real recordings of the five LevelX data sets ([docs/io_and_scenarios.md](docs/io_and_scenarios.md)) |
| Encounter series, observed PET, TET/TIT, braking onset and (TA, v_conf), scale calibration, severity hierarchy, scenario summary and comparison, synthetic scenarios | `process`, `calibration`, `hierarchy`, `scenario`, `datasets` | unit tests on constructed cases; definitions stated in the docstrings; hierarchy and prediction-error scales computed on all recordings of inD, rounD, uniD, exiD and highD (`docs/diamond_*.md`, descriptive, nothing validated); Hyden's (1987) severity zones are approximate (see the docstrings) |
| Which face and corner touch first on a collision course, and which would touch if the road user ahead were delayed by TAdv (crossing course) | `contact` | time-stepped search; the ten corner-side configurations of Jimenez et al. (2013) come out as classes |
| NGSIM reader (US-101, I-80, Lankershim, Peachtree; feet to metres, front centre to body centre) | `io.read_ngsim` | run on all ten periods; units checked against the data set's own columns ([docs/ngsim_notes.md](docs/ngsim_notes.md)) |
| Causal or centred smoothing of trajectories | `preprocessing` | unit tests (causality, noise reduction, lag); not tuned to a data set |
| Conflict windows: `extract_conflicts`, and a bank of windows around the most severe encounters of NGSIM that ships with the package (`datasets.load_conflict_bank("ngsim")`), plus counts and scales of the five LevelX data sets (`datasets.load_summary()`) | `bank`, `datasets` | the windows are chosen by the package's own indicators: examples and test material, **not a sample** |
| Plots of the polygon K, the disturbance set D with the signed margin, the indicator profile of an encounter, the hierarchy (needs matplotlib) | `viz` | smoke tests |
| Statistically scaled margin (beta), collision physics beyond point masses, 2-D versions of the ten car-following measures, native Aimsun input | - | **not implemented** |

## The idea in one paragraph

Give each road user its own predicted arrival time at the conflict. The pairs of arrival times at which the two bodies overlap
form a convex polygon `K` (an affine preimage of the Minkowski difference of the bodies).
Undisturbed motion is the diagonal. TTC is where the diagonal enters `K`; TAdv is the distance
of `K` from the diagonal (the delay that would produce a collision); T2 and TG are the earliest
second arrivals. The 32 corner-side combinations of the 2010 appendix become one polygon, and
parallel paths, standing road users and overlapping bodies need no special cases. See
[docs/methods.md](docs/methods.md).

## Development

```
uv venv && uv pip install -e ".[dev]"
pytest
python tools/equivalence.py --n 1000000   # writes docs/equivalence.md
python tools/benchmark.py                 # writes docs/benchmark.md
```

## Citation

See [CITATION.cff](CITATION.cff). License of the code: BSD-3-Clause.

**Data shipped inside the package** (`src/pyssms/data/`): the windows in `conflict_bank_ngsim.npz` come
from the FHWA NGSIM trajectories, licensed by the Federal Highway Administration under a modified
Creative Commons Attribution 2.0 licence (not public domain). Credit FHWA and the Next Generation
Simulation (NGSIM) program; any reuse of those data is subject to that licence
(`NGSIM_LICENSE.txt`, `NGSIM_CC-BY-2.0_legalcode.html`); the data are provided as is. Nothing from the
LevelX data sets (inD, rounD, uniD, exiD, highD) is shipped except aggregated counts and scales.
