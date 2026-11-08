# NGSIM in pyssms: source, licence, decisions and checks

*Written 2026-11-07. Everything below was read from the files and run in this repository.*

## Source and licence

The user placed the FHWA archives in `D:\ReproducibleResearch_R_Projects\NGSIM\10-02-2026\data_raw\NGSIM DATA`
(`US-101-Main-Data.zip`, `I 80.rar`, `Lankershim-Main-Data.zip`, `Peachtree-Main-Data.zip`). The
trajectory files and licence texts were unpacked into `data_raw/ngsim/<site>/` (git-ignored; SHA-256
prefixes of the archives and of the ten trajectory files: `data_raw/SHA256SUMS_ngsim_prefix.txt`,
full list `data_raw/SHA256SUMS_ngsim.txt`).

**The licence is not public domain and not CC0.** `ngsim-license.htm` (the visible text of the four archives is
identical, compared by hash on 2026-11-07; the US-101 text was read in full) says the data are
"licensed under the terms specified by the modified creative commons license attribute 2.0", the
Licensor being the Federal Highway Administration. It grants free use, reproduction, distribution
and derivative works **provided that** (1) FHWA and the Next Generation Simulation (NGSIM) program
are credited, and (2) any reuse or distribution makes clear that it is subject to those licence
terms; the data are provided "as is". Either condition can be waived in writing by FHWA. The legal
code (`creative-commons-deed.html`, Attribution 2.0) is shipped with the bank.

Consequences for the package:

* windows cut from NGSIM may be redistributed inside the wheel **with** the credit and the licence
  statement: they are in `src/pyssms/data/` together with `NGSIM_LICENSE.txt` and
  `NGSIM_CC-BY-2.0_legalcode.html`, and `ConflictBank.info` names the licence;
* the package's own BSD-3-Clause licence does not apply to those data; `README.md` says so;
* a relayed claim that NGSIM is "public domain / CC0" was **not** adopted: it contradicts the
  licence text in the archives.

The German LevelX data sets are different: their terms were relayed, not read (see
`docs/data_sources.md`). Only counts and scales (no trajectories) are shipped from them, and the
repository stays private until the providers' terms for those aggregates are read in the approval
e-mails.

## What the reader does (`pyssms.io.read_ngsim`)

* Columns 1-14 of the data dictionary (id, frame, total frames, epoch ms, local X/Y, global X/Y,
  length, width, class, speed, acceleration, lane); feet to metres; 10 Hz.
* NGSIM gives the **front centre**; the body centre is the front centre moved back by half the
  length along the heading. There is no heading column: it is the direction of the front-centre
  displacement over +-5 frames (not causal), held while the displacement speed is below 1 m/s. These
  are decisions of the reader, listed in its docstring.
* Checks on the real files (first periods): vehicle lengths median 4.42 m (US-101), 4.88 m
  (Lankershim, Peachtree), widths 1.83 m and 2.13 m; speed column minus position-derived speed:
  median 0.000 m/s (units and reference agree).

## What the data set does not give consistently (measured, `docs/ngsim_checks.md`)

The acceleration column is not the derivative of the speed column (RMS difference 1.0 m/s2 on
US-101, 4.8 m/s2 on I-80), and the speed column differs from the derivative of the position by
0.2 to 0.7 m/s RMS. Literature on these defects exists (e.g. Thiemann, Treiber and Kesting, TRR 2088,
2008, doi:10.3141/2088-10; Montanino and Punzo, Transp. Res. B 80, 2015,
doi:10.1016/j.trb.2015.06.010; both found and checked in Crossref on 2026-11-07, **not read in full
here**). Hence `pyssms.preprocessing`: positions are smoothed (causally by default) and speed and
acceleration derived from them. A trailing mean of 5 frames lags the true position by 2 frames (0.2
s); that is a bias of the TTC computed from it, not a free lunch (tested in
`tests/unit/test_ngsim_bank.py`).

## Runs

* `tools/ngsim_run.py`: hierarchy and prediction-error scales per period (10 periods: US-101 x3,
  I-80 x3, Lankershim x2, Peachtree x2) -> `docs/diamond_NGSIM.md`. Positions smoothed with a causal
  5-frame mean. `--raw --only Peachtree` is a sensitivity run (`docs/diamond_NGSIM_raw.md`): it uses the data set's own positions and its speed column. At Peachtree Street the share of pairs reaching TTC <= 1.5 s is 4.4% raw against 7.0% smoothed, and 46.0% against 38.4% never overlapping, so the NGSIM counts depend on this step (the two runs differ in both positions and the speed source).
* `tools/ngsim_ssm1d.py`: ten car-following measures on the freeway files (leader = the data set's
  preceding vehicle) -> `docs/ngsim_ssm1d_descriptive.md`.
* `tools/build_conflict_bank.py`: the shipped bank (`pyssms.datasets.load_conflict_bank("ngsim")`).
  The windows are chosen by the package's own indicators, so they are examples, not a sample.

A process-pool run of the hierarchy exhausted the memory (about 5 GB per worker because every
encounter of a period was held at once, 3 workers swapped and stalled). The pairs are now processed
in batches of 3000 (counts are additive; batch sizes 500 and unbatched gave identical aggregates on
a uniD recording), and the periods run as separate processes.

## Ten car-following measures on the freeways (`docs/ngsim_ssm1d_descriptive.md`)

Six periods (US-101 x3, I-80 x3): 8,238,546 follower-leader pair-frames, 823,852 sampled rows (every
second). Descriptive only; the parameters were fixed before the run. Two things to read before
using the numbers: (1) our clear gap against the data set's own `Spacing` minus the leader length:
median -0.010 m, 5th to 95th percentile -0.55 to +0.46 m, but the largest difference is 109.5 m, so a
few pairs (lane changes, the preceding-vehicle column lagging behind the position) do not agree;
nothing was removed; (2) the beta scales come from Lankershim and Peachtree (no unhindered freeway
vehicle exists under the 15 m rule), so they are not freeway scales. The jerk, hence TTC3, comes from
smoothed positions and is noisy. A first attempt took more than 90 min per period because the
required-braking search was called on 110k rows at once; it now runs in blocks of 2000 rows
(identical output, about 12 to 23 min per period).
