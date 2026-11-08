# Trajectory input, encounter processing and scenario reports

New in the unreleased 0.1.0 line (2026-11-03). Everything here is **tested on synthetic files and
on round trips only**: no real LevelX, VISSIM, Aimsun or SSAM-program file has been run through it.
The table says exactly what each reader was checked against.

## Modules

| Module | What it does |
|---|---|
| `trajectories` | `Trajectories`: long table (t, uid, x, y, heading, vx, vy, length, width, kind), SI units, centre reference |
| `io` | `read_trj`, `write_trj` (SSAM `.trj`), `read_levelx` (inD, rounD, exiD, uniD, highD), `read_sumo_fcd`, `read_vissim_fzp`, `read_table` |
| `process` | candidate pairs, indicator time series per pair (`Encounter`), observed PET, TET/TIT, braking onset and the Swedish `(TA, v_conf)` pair, angle-based conflict type |
| `calibration` | `unhindered_ids`, `calibrate_scales`: sigma_delta(tau) and sigma_eps(tau) of the constant-velocity prediction error |
| `hierarchy` | level counts of encounters (A / B bins by TAdv / C) with an optional severity split; `plot_hierarchy` (matplotlib optional) |
| `contact` | `contact_faces`: on a collision course, the face of one body and the corner of the other that touch first (rectangles: front, left, rear, right); checked against a time-stepped separating-axis search for five orientations |
| `scenario` | `summarize_scenario`, `compare_scenarios`, `following_measures` (the ten car-following measures for one leader/follower pair) |
| `datasets` | synthetic scenarios: crossing, car following, ramp merge, roundabout entry, pedestrian crossing |

## What each reader was checked against

| Reader | Source of the format | Tested with | Not tested |
|---|---|---|---|
| `read_trj` / `write_trj` | SSAM File Format Specification 1.04 (Siemens ITS 2004) and the 3.0 elevation addition (`lit/SSAM_File_Format_v1.04.pdf`, `..._v3.0.pdf`, from github.com/OSADP/SSAM); byte layout also compared with SUMO's `sumolib/output/convert/trj.py` | round trip; a file packed byte by byte as in the specification (with and without elevation); English units; garbage input | opening a file written by `write_trj` in the SSAM program; a `.trj` from VISSIM or Aimsun |
| `read_levelx` | column names of the data provider's loader (`ika-rwth-aachen/drone-dataset-tools`, `tracks_import.py`): `trackId, frame, xCenter, yCenter, heading (deg), width, length, xVelocity, yVelocity`; `frameRate` from recordingMeta; highD layout `x, y` (upper-left corner), `width` along x, `height` along y | synthetic files, **and real files (2026-11-03)**: inD 33, rounD 24, uniD 13 and 4 of 93 exiD recordings (about 27 million rows, no non-finite values, heading within 2 degrees of the velocity direction at the median) and all 60 highD recordings (39.7 million rows, 0.04 s frames, 30.6 M car and 9.1 M truck rows; position differences agree with the recorded velocity) | the remaining 89 exiD recordings; the correctness of the highD corner convention beyond the consistency checks above (sizes 7.2 x 2.1 m on average, as expected for cars and trucks) |
| `read_sumo_fcd` | SUMO `--fcd-output` XML (`timestep`, `vehicle`, `person`) and `xml2csv.py` CSV; front-bumper reference and compass angle as documented by SUMO | small synthetic XML and CSV | a real SUMO run; SUMO versions that write other attributes |
| `read_vissim_fzp` | `$VEHICLE:` header line, `;` separated; attribute names `SIMSEC, NO, COORDFRONTX/Y, COORDREARX/Y` assumed | synthetic file | a real `.fzp` (attribute names may differ: they are arguments) |
| Aimsun | no fixed trajectory file layout is known to this package | - | use `read_table` with a column map, or export `.trj` |

SUMO already has its own SSM device (`sumo.dlr.de/docs/Simulation/Output/SSM_Device.html`) which
writes TTC, PET and related measures during the run; `pyssms` works on the trajectories afterwards
and adds the polygon indicators (TAdv, T2, TG, margins), so the two are complements, not rivals.

## What was run on the real data (2026-11-03)

* `docs/diamond_inD.md`, `diamond_rounD.md`, `diamond_uniD.md`, `diamond_exiD.md` and `diamond_highD.md`
  (**all recordings**: 33, 24, 13, 93 and 60; exiD and highD completed 2026-11-07, the first 12 exiD
  recordings reproduce the earlier numbers exactly): level counts of the empirical hierarchy and
  prediction-error scales, aggregates only, one file per recording in the git-ignored
  `runs_local/diamond/`, resumable (`tools/levelx_diamond.py`). On highD 82% of the motor-vehicle
  pairs never overlap (level C) and 0.02% (446 of 2,562,596) reach a collision course with TTC below 3 s.
* `docs/highd_ssm1d_descriptive.md` and `docs/exid_ssm1d_descriptive.md` (2026-11-07,
  `tools/levelx_ssm1d.py`): the ten car-following measures on the follower-leader pairs of the data sets
  themselves, with the parameters fixed beforehand, a sensitivity set, the polygon indicators of the same
  pairs and Spearman correlations. **Descriptive: no outcome variable, nothing validated.**
* `docs/validation_pilot_ind.md` and `validation_pilot_ind_diagnostic.md`: the pre-registered inD pilot
  and its post hoc diagnostic (`docs/prereg_ind_preonset.md`).
* `process.hyden_braking_limit`, `process.hyden_uniform_severity_ta`, `process.hyden_zone_offset`,
  `process.hyden_severity_zone`, `process.hyden_serious_conflict`: Hyden's (1987) speed-dependent
  severity, read from the page images of the thesis (printed pp. 115-119, 139-141, 161-166; pdf page
  = printed + 24). ALT.DEF.1 `TA_min = v1/(16.7 exp(-0.0137 v_m))` (0.94 s at 50 km/h) and ALT.DEF.2
  (Garder: twice that). The thesis adopts ALT.DEF.2 (section 7.3.5) and its Figures 7.4 and 7.17 draw the
  **severity zones as parallel copies of the braking-time curve, 0.5 s apart on the TA axis** (each zone
  halved into 'b' and 'a' of 0.25 s). We code `zone = 3 - floor(offset / 0.5)`, with `offset = TA - 2
  TA_min(v1)`: zone 3 is the first zone on the safe side of the braking-time curve, then 2, then 1
  (offset 1.0 to 1.5 s); offsets of 1.5 s or more get 0 (not drawn). A **serious conflict** is an event in
  severity zone 2 or higher (section 7.3.9, p. 166), i.e. offset < 1.0 s. What was **not** checked: (i)
  the figure's bold braking-time curve lies below the formula's (by eye: about 0.8 s at 30 km/h and
  2.4-2.6 s at 70 km/h; formula 1.1 s and 2.8 s), so zone borders are approximate; (ii) the zone
  numbering follows the labels of Figure 7.17 and the statement that accidents start near zone 3 (p.
  165), no data were used; (iii) the "perpendicular distance" wording of section 7.3.4 versus the
  horizontal shift drawn in the figures. (An earlier version of `hyden_braking_limit` used the factor
  0.55 and said "about 1.5 s at 50 km/h"; the 0.55 includes a safety margin, the printed formula uses
  0.85.)

## Binary cache for LevelX recordings

`io.build_levelx_cache` / `io.load_levelx_fast` store a recording as a NumPy `.npz` file next to the CSV
files (`<folder>/_pyssms_cache`, inside the git-ignored `data_raw`); the cache is rebuilt when the
source file or the settings change. Measured on three real recordings (2026-11-03): reading the CSV
takes 0.8 to 1.8 s per 40 to 107 MB; the plain cache loads 10 to 13 times faster (0.08 to 0.18 s) and is
about 0.55 to 0.85 times the CSV size; the compressed cache loads 5 to 7 times faster and is about a
tenth of the CSV size (4 to 11 MB). Values are bit-identical to the CSV reader. (The reader was
already fast; the gain is a factor of 5 to 13, not 50 to 100.) **The cache is the data set in another
format: do not distribute it.** The licence of the LevelX data sets (as printed in the `LICENSE` file of
the data folders) forbids distributing the data set or modified versions; it allows derivative works
that are abstract representations and do not allow the data to be recovered. Aggregates such as
`docs/diamond_*.md` are of that kind; per-event catalogues (pair ids and times) were **not** put in the
package: ask the providers (levelxdata@fka.de) first.

## Definitions chosen here (all configurable, all stated in the docstrings)

* **Observed PET** (`process.observed_pet`): the bodies are rotating rectangles at their recorded
  poses; a road user occupies the conflict area from its first to its last frame whose footprint
  overlaps the other road user's footprint at *any* frame. PET = arrival of the second minus
  departure of the first. Overlapping occupation intervals give PET 0 and `collision = 1`, which
  with drone data often reflects box-size error.
* **TET / TIT** (`process.tet_tit`): Minderhoud and Bovy (2001) for any series; applied to TTC.
  Undefined TTC (no collision course) is not exposure.
* **Braking onset** (`process.braking_onset`): first speed drop of at least 1 m/s^2 over 1 s,
  reported at the start of the decline. A simple stand-in, **not** the evasive-action detector of
  Johnsson and Laureshyn (2022).
* **`(TA, v_conf)`** (`process.swedish_pair`): TA = TTC (or T2) at the braking onset, v_conf =
  speed then. Hyden's (1987) severity zones are coded separately (`process.hyden_severity_zone`,
  `hyden_serious_conflict`) and can be applied to these pairs; the zone border is approximate (see above).
* **Conflict type** (`process.conflict_type`): angle between headings, limits 30 and 85 degrees by
  convention. The FHWA evaluation of SSAM (FHWA-HRT-08-051, chapter 6) states that the SSAM
  classification started from the angle alone, was later refined with lane and link information,
  and that appropriate angles "warrant further investigation"; the values inside SSAM were not
  verified. Do not claim agreement with SSAM's type counts.
* **Candidate pairs** (`process.candidate_pairs`): centres within `max_distance` **or** the 10 s
  straight future paths within 6 m. The second rule keeps pairs that pass the same point seconds
  apart.
* **Scales** (`calibration`): timing error = -(error along the heading)/speed, sideways error =
  error across the heading, for the constant-velocity prediction `p + v tau`; RMS or MAD. With
  velocities estimated by finite differences the noise of the velocity enters the prediction error
  (the tests show this); use the data provider's velocities where they exist. Whether this is the
  right standardiser for beta is the open question of [beta_proposal.md](beta_proposal.md).
* **Hierarchy** (`hierarchy`): level of an encounter = smallest TAdv it reached; "diamond" or
  "pyramid" is a finding of the data, not imposed.

## Not done

* Which sides touch (done 2026-11-07): `contact.contact_faces` gives the face and the corner of the first
  contact on a collision course (state A), from the half-plane that the diagonal crosses first;
  face-to-face and corner-to-corner contacts are ties (`n_active > 1`). For crossing courses (state B)
  nothing touches, so `contact.avoided_contact_faces` (own result type `AvoidedContact`) names the
  faces and corners that would touch first if the road user ahead were delayed by TAdv (the active edges
  of `K` at its closest point to the diagonal; a graze, not a contact). Tested against a time-stepped
  search; see `docs/jimenez2013_note.md` for the comparison with the ten configurations.
* Two-dimensional versions of the ten car-following measures; `following_measures` is
  one-dimensional along the follower's heading.
* Native Aimsun input; reading `.trj` files written by VISSIM or Aimsun has not been tried.
