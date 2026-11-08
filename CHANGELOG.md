# Changelog

## 0.1.0 (2026-11-08): initial release

* `timetime`: one conflict polygon K in the plane of the two predicted arrival times gives TTC (state A), Time Advantage, T2 and Time Gap (state B) and
  the no-overlap state C, for two convex translating bodies at any approach angle; vectorised; 8-row and 12-row forms of K for rectangles.
* `reference.laureshyn2010`: independent implementation of Appendix A of Laureshyn et al. (2010) (32 corner-side combinations); equivalence
  report (`docs/equivalence.md`) and benchmark (`docs/benchmark.md`).
* `ssm1d`: the ten car-following measures of the 2025 framework (TTC1, TTC2, TTC3, TTCD, DRAC, MDRAC, DCIA, PSD, MPSD, SDI), tested against
  simulations of their motion stories.
* `contact`, `escape`, `stories`, `margins`, `disturbance`, `severity` (Delta-V, Extended Delta-V, injury-risk curves).
* Trajectory input and processing: `io` (SSAM, SUMO FCD, VISSIM, LevelX, NGSIM, generic table), `preprocessing`, `process`, `calibration`,
  `hierarchy`, `scenario`, `bank` and `datasets` (synthetic scenarios, a bank of NGSIM conflict windows under the FHWA licence text, aggregated
  counts and scales of the five LevelX data sets; no LevelX trajectories), `viz`.
* Tests: pytest suite in `tests/`; continuous integration on Linux and Windows with Python 3.10 and 3.13.
* Article: `paper_softwarex/` holds the sources, the number-injection scripts and the figures of the accompanying software article.

Everything reported by the tools is descriptive; no indicator is validated against observed outcomes in this release.
