"""Text of the SoftwareX manuscript (Original Software Publication) for pyssms, English and Persian.

Nothing numeric is typed here: tokens ``{{path/to/key:fmt}}`` are replaced from ``results.json`` (and ``fig_numbers.json``
under the key ``fig2``) by ``common.py``. Citations are ``[@key]`` or ``[@a,@b]`` and are numbered by first appearance.
Cross references: ``{fig:key}``, ``{sec:key}``. Blocks: ("p", text), ("h", run-in heading), ("code", text), ("fig", key, file, caption).
The two languages carry the same blocks in the same order and the same tokens (checked by ``check_parallel.py``).
"""

from __future__ import annotations

from pathlib import Path

VERSION = "0.1.0"
REPO = "https://github.com/sabernaseralavi-60/pyssms"
# DOI of the archived release (Zenodo). Written into zenodo_doi.txt after the release is archived; empty until then.
_zf = Path(__file__).with_name("zenodo_doi.txt")
ZENODO_DOI = _zf.read_text(encoding="utf8").strip() if _zf.exists() else ""
ARCHIVE = ("https://doi.org/" + ZENODO_DOI) if ZENODO_DOI else ""
SUPPORT_EMAIL = "saber_naseralavi@uk.ac.ir"

AFFILS = {"a": "Department of Civil Engineering, Shahid Bahonar University of Kerman, Kerman 7616914111, Iran"}
AUTHORS = [{"name": "Seyed Saber Naseralavi", "aff": "a", "email": SUPPORT_EMAIL, "corresponding": True,
            "orcid": "0000-0002-5392-910X"}]

# ----------------------------------------------------------------------------------------------------------------- references
# Formatted by hand from Crossref records (checked 2026-11-07 and earlier, see paper/paper.bib); numbered by first appearance.
REFS = {
    "arun2021": "Arun A, Haque MM, Washington S, Sayed T, Mannering F. A systematic review of traffic conflict-based safety measures with a focus on application context. Anal Methods Accid Res 2021;32:100185. https://doi.org/10.1016/j.amar.2021.100185.",
    "zheng2021": "Zheng L, Sayed T, Mannering F. Modeling traffic conflicts for use in road safety analysis: a review of analytic methods and future directions. Anal Methods Accid Res 2021;29:100142. https://doi.org/10.1016/j.amar.2020.100142.",
    "krajewski2018": "Krajewski R, Bock J, Kloeker L, Eckstein L. The highD dataset: a drone dataset of naturalistic vehicle trajectories on German highways for validation of highly automated driving systems. In: 2018 21st International Conference on Intelligent Transportation Systems (ITSC); 2018. p. 2118-25. https://doi.org/10.1109/ITSC.2018.8569552.",
    "bock2020": "Bock J, Krajewski R, Moers T, Runde S, Vater L, Eckstein L. The inD dataset: a drone dataset of naturalistic road user trajectories at German intersections. In: 2020 IEEE Intelligent Vehicles Symposium (IV); 2020. p. 1929-34. https://doi.org/10.1109/IV47402.2020.9304839.",
    "krajewski2020": "Krajewski R, Moers T, Bock J, Vater L, Eckstein L. The rounD dataset: a drone dataset of road user trajectories at roundabouts in Germany. In: 2020 IEEE 23rd International Conference on Intelligent Transportation Systems (ITSC); 2020. p. 1-6. https://doi.org/10.1109/ITSC45102.2020.9294728.",
    "moers2022": "Moers T, Vater L, Krajewski R, Bock J, Zlocki A, Eckstein L. The exiD dataset: a real-world trajectory dataset of highly interactive highway scenarios in Germany. In: 2022 IEEE Intelligent Vehicles Symposium (IV); 2022. p. 958-64. https://doi.org/10.1109/IV51971.2022.9827305.",
    "ngsim2017": "U.S. Department of Transportation, Federal Highway Administration. Next Generation Simulation (NGSIM) vehicle trajectories and supporting data [dataset]; 2017. https://doi.org/10.21949/1504477.",
    "gettman2003": "Gettman D, Head L. Surrogate safety measures from traffic simulation models. Transp Res Rec 2003;1840:104-15. https://doi.org/10.3141/1840-12.",
    "laureshyn2010": "Laureshyn A, Svensson Å, Hydén C. Evaluation of traffic safety, based on micro-level behavioural data: theoretical framework and first implementation. Accid Anal Prev 2010;42:1637-46. https://doi.org/10.1016/j.aap.2010.03.021.",
    "naseralavi2025": "Naseralavi S, Soltanirad M, Ranjbar E, Jimee K, Lucero M, Baghersad M, et al. A short-term storytelling framework for understanding surrogate safety measures in intelligent vehicle interactions. Future Transp 2025;5:86. https://doi.org/10.3390/futuretransp5030086.",
    "saunier": "Saunier N. Traffic Intelligence: tools for transportation data processing [software], MIT licence. Python Package Index. https://pypi.org/project/trafficintelligence/ (accessed 2026-11-07).",
    "jiao": "Jiao Y. Two-Dimensional-Time-To-Collision [software], MIT licence. GitHub. https://github.com/Yiru-Jiao/Two-Dimensional-Time-To-Collision (accessed 2026-11-07).",
    "odonnell1989": "O'Donnell PA, Lozano-Pérez T. Deadlock-free and collision-free coordination of two robot manipulators. In: Proceedings, 1989 International Conference on Robotics and Automation; 1989. p. 484-9. https://doi.org/10.1109/robot.1989.100033.",
    "kant1986": "Kant K, Zucker SW. Toward efficient trajectory planning: the path-velocity decomposition. Int J Robot Res 1986;5:72-89. https://doi.org/10.1177/027836498600500304.",
    "jimenez2013": "Jiménez F, Naranjo JE, García F. An improved method to calculate the time-to-collision of two vehicles. Int J Intell Transp Syst Res 2013;11:34-42. https://doi.org/10.1007/s13177-012-0054-4.",
    "laureshyn2017": "Laureshyn A, De Ceunynck T, Karlsson C, Svensson Å, Daniels S. In search of the severity dimension of traffic events: extended Delta-V as a traffic conflict indicator. Accid Anal Prev 2017;98:46-56. https://doi.org/10.1016/j.aap.2016.09.026.",
    "lubbe2022": "Lubbe N, Wu Y, Jeppsson H. Safe speeds: fatality and injury risks of pedestrians, cyclists, motorcyclists, and car drivers impacting the front of another passenger car as a function of closing speed and age. Traffic Saf Res 2022;2:000006. https://doi.org/10.55329/vfma7555.",
    "thiemann2008": "Thiemann C, Treiber M, Kesting A. Estimating acceleration and lane-changing dynamics from Next Generation Simulation trajectory data. Transp Res Rec 2008;2088:90-101. https://doi.org/10.3141/2088-10.",
    "montanino2015": "Montanino M, Punzo V. Trajectory data reconstruction and simulation-based validation against macroscopic traffic patterns. Transp Res Part B 2015;80:82-106. https://doi.org/10.1016/j.trb.2015.06.010.",
    "johnsson2022": "Johnsson C, Laureshyn A. Identification of evasive manoeuvres in traffic interactions and conflicts. Traffic Saf Res 2022;3:000012. https://doi.org/10.55329/erqd8683.",
    "westhofen2023": "Westhofen L, Neurohr C, Koopmann T, Butz M, Schütt B, Utesch F, et al. Criticality metrics for automated driving: a review and suitability analysis of the state of the art. Arch Comput Methods Eng 2023;30:1-35. https://doi.org/10.1007/s11831-022-09788-7.",
}
if ZENODO_DOI:
    REFS["pyssms_zenodo"] = (f"Naseralavi SS. pyssms: surrogate safety indicators for road-user encounters on a time-time conflict polygon [software]. "
                             f"Version {VERSION}. Zenodo; 2026. https://doi.org/{ZENODO_DOI}.")

# ----------------------------------------------------------------------------------------------------------------- English
EN: dict = {}
EN["title"] = "pyssms: one Python package for two-dimensional time-to-collision indicators and car-following surrogate safety measures"
EN["keywords"] = ["surrogate safety measures", "time to collision", "time advantage", "trajectory data", "traffic conflicts", "Python"]
EN["abstract"] = (
    "Surrogate safety measures turn road-user trajectories into numbers that say how close an encounter came to a collision. Two families of "
    "them have lived in separate code: two-dimensional indicators defined for any approach angle, and one-dimensional "
    "car-following measures built on short motion stories. pyssms is a Python package that puts both on common ground. Time to collision, "
    "time advantage, T2 and time gap are read exactly from one convex conflict polygon, and ten car-following measures are implemented "
    "from the motion stories they assume. The package reads SSAM, SUMO, VISSIM, LevelX and NGSIM trajectories, smooths them, finds "
    "candidate pairs, sorts encounters into a hierarchy, names the faces and corners that touch, and ships {{bank/windows}} conflict windows "
    "cut from NGSIM. It depends on NumPy and PyYAML only. Correctness is tested rather than asserted: {{tests/total}} automated tests, "
    "agreement with the printed procedure on {{equiv/compared:,}} random encounters, and independent simulations of the motion stories. "
    "Applied to {{highd/recordings}} highD, {{exid/recordings}} exiD and {{ngsim/recordings}} NGSIM freeway recordings, the share of highD rows "
    "with a time to collision of 3 s or less is {{highd/m/ttc1/crit:.2f}} % if speeds are assumed constant and {{highd/m/ttcd/crit:.0f}} % if the "
    "leader is assumed to brake to a stop. All statistics are descriptive. Version {{version}} is the initial release of the package."
)
EN["meta"] = [
    ("C1", f"v{VERSION}"),
    ("C2", ARCHIVE or REPO),
    ("C3", "BSD 3-Clause License"),
    ("C4", "git"),
    ("C5", "Python 3; NumPy, PyYAML; optional: matplotlib"),
    ("C6", "Python 3.10 or newer; continuous integration on Linux and Windows with Python 3.10 and 3.13"),
    ("C7", REPO + "/tree/main/docs"),
    ("C8", SUPPORT_EMAIL),
]
EN["sections"] = {}
EN["sections"]["motivation"] = [
    ("p", "Ask whether the car-following pairs of a freeway recording are in danger. An analyst who assumes constant speeds flags "
          "{{highd/m/ttc1/crit:.2f}} % of the sampled highD rows at a time to collision of 3 s or less; one who assumes that the leader brakes to a stop "
          "flags {{highd/m/ttcd/crit:.0f}} %. Neither has made an error: each has chosen a motion story. The number in a paper ends a chain of choices, "
          "namely a file reader, a smoothing window, a pair filter, a story and a threshold, and the chain is rarely visible. "
          "pyssms is built to make it visible."),
    ("p", "Surrogate safety measures (SSMs) describe how close road users came to a collision, without waiting for crashes [@arun2021,@zheng2021]. "
          "Drone recordings such as highD, inD, rounD and exiD [@krajewski2018,@bock2020,@krajewski2020,@moers2022] and the NGSIM vehicle "
          "trajectories [@ngsim2017] now supply trajectories at scale, and for years the FHWA Surrogate Safety Assessment Model derived "
          "measures from simulated ones [@gettman2003]. What is missing is open, tested code that applies the published definitions to such "
          "files, so that a number in a paper can be traced to a line of code."),
    ("p", "Two traditions need to meet in that code. Laureshyn, Svensson and Hydén [@laureshyn2010] defined time to collision (TTC), "
          "time advantage (TAdv), T2 and time gap (TG) for any approach angle, with road users represented as rectangles, by enumerating 32 "
          "combinations of a corner of one road user and a side of the other. Naseralavi et al. [@naseralavi2025] coded ten car-following measures by the short motion "
          "story each one assumes: constant speeds, accelerations or jerks for TTC1, TTC2 and TTC3, a braking leader for TTCD, and braking of "
          "the follower for DRAC, MDRAC, DCIA, PSD, MPSD and SDI. The first is geometric and works for crossings and merges; the second is "
          "kinematic and works along a lane. Each is usually implemented, if at all, on its own and for one data set."),
    ("p", "Related open software: Traffic Intelligence [@saunier] processes trajectories and motion predictions, and a "
          "vectorised two-dimensional TTC is published on GitHub [@jiao]. A light search on 2026-11-01 (not a systematic review) found no "
          "package that reads the two-dimensional indicators of the 2010 paper for any shape and angle together with the ten car-following "
          "measures and the file formats of the common data sets. pyssms is written to close that gap. It (i) reads trajectories, (ii) "
          "computes TTC, TAdv, T2 and TG exactly on one conflict polygon, (iii) computes the ten car-following measures, (iv) names the faces "
          "and corners that touch, (v) summarises encounters in a hierarchy, and (vi) ships a small bank of conflict windows for tests and "
          "teaching. Its numbers are checked against the printed procedure, against simulations and against the data sets' own columns."),
]
EN["sections"]["architecture"] = [
    ("p", "pyssms has {{modules/n}} modules in four layers (read, prepare, compute, report; {fig:arch}). Only NumPy and PyYAML are required; "
          "matplotlib is optional for plots. The code is typed and documented, and every module states its assumptions in its docstring."),
    ("p", "The computing core is one geometric idea. Let τ₁ and τ₂ be the predicted times at which road users 1 and 2 reach given positions on "
          "their paths. The pairs (τ₁, τ₂) at which the two bodies would overlap form a convex polygon K in the plane of the two predicted arrival "
          "times; K is the Minkowski difference of the bodies expressed in that plane ({fig:poly}, panel B). Because the bodies are convex and the "
          "velocities constant, K is the solution set of a few linear inequalities in (τ₁, τ₂): eight for two rectangles that move along their length "
          "and twelve in general. Undisturbed motion is the diagonal τ₁ = τ₂. If K meets the diagonal the road users are on a collision course (state A) "
          "and TTC is where the diagonal enters K. If K misses it (state B, a crossing course), TAdv is the smallest |τ₁ − τ₂| over K, "
          "and T2 and TG are read from the same polygon as the earliest second arrivals. If K is empty within the horizon there is no overlap "
          "(state C). The 32 combinations of the 2010 appendix become one polygon, and parallel paths, standing road users and overlapping bodies need "
          "no special case. Path-time diagrams of this kind are classical in robot motion planning [@odonnell1989,@kant1986]."),
    ("p", "Four design rules follow from the opening example. Every assumption (a reaction time, a deceleration, a horizon, a smoothing window) "
          "is a named argument; where a default exists it is visible in the signature and the docstring, and the functions of ssm1d take reaction "
          "time and decelerations without defaults. A measure that does not exist for a pair is NaN, never zero: TTC is undefined "
          "unless the pair is on a collision course. Each module is checked against an independent oracle, such as a time-stepping simulation or an "
          "implementation of the printed procedure, and not against itself. Data stay outside the package, which ships only a small NGSIM bank and "
          "counts."),
    ("fig", "arch", "fig1_architecture",
     "Structure of pyssms: four layers from file readers to reports. The decision sequence sorts every pair and frame into state A, B or C; a second "
     "lane takes the leader-follower series to the ten car-following measures, which do not need K. The dashed arrow leads to further readings of the "
     "same encounter. The bar at the bottom lists the checks of the package."),
    ("fig", "poly", "fig2_polygon",
     "One encounter in three views. (A) Plan view: dashed outlines at the start, filled bodies where they would touch if road user 1 were delayed by TAdv "
     "(each body at its own arrival time; circle: touching corners). (B) Conflict polygon K in the plane of the two predicted arrival times, with the "
     "diagonal, TAdv and T2. (C) The same construction for three encounters in one plane: the diagonal enters K in state A (TTC), K lies beside the "
     "diagonal in state B (TAdv), and K lies outside the horizon (shaded square) in state C."),
    ("h", "Software functionalities."),
    ("p", "Readers and preparation. Trajectories are read from SSAM .trj files (reading and writing), SUMO floating-car output, VISSIM .fzp, "
          "LevelX files (inD, rounD, uniD, exiD, highD), NGSIM and generic tables into one Trajectories object. The NGSIM reader converts feet to "
          "metres and moves the reference from the front centre to the body centre. Causal or centred smoothing is a separate, explicit step."),
    ("p", "Indicators. TTC, TAdv, T2 and TG are computed for arrays of encounters, with an 8-row form of the polygon for bodies that move along "
          "their length and a general 12-row form for any convex shape. Margins, a smallest-braking search (escape) and a disturbance set add "
          "readings of the same polygon. Delta-V and an extended Delta-V [@laureshyn2017] and injury-risk curves [@lubbe2022] give severity."),
    ("p", "Car-following measures. TTC1, TTC2, TTC3, TTCD, DRAC, MDRAC, DCIA, PSD, MPSD and SDI are written from their stories, not copied from "
          "printed formulas. Where a printed form differs from its own derivation the differences are listed (docs/ssm1d_notes.md); reaction "
          "time and decelerations are inputs of the functions of ssm1d, without defaults. {tab:ten} lists the measures."),
    ("table", "ten", "The ten car-following measures of ssm1d: the motion story each one assumes, its inputs besides the gap and the speeds, its unit, and the direction in which a value is more critical.",
     ["Measure", "Motion story", "Further inputs", "Unit", "More critical when"],
     [["TTC1", "constant speeds", "none", "s", "smaller"],
      ["TTC2", "constant accelerations", "none", "s", "smaller"],
      ["TTC3", "constant jerks", "none", "s", "smaller"],
      ["TTCD", "leader brakes to a stop, follower keeps its speed", "leader deceleration", "s", "smaller"],
      ["DRAC", "follower brakes at once to remove the closing speed", "none", "m/s²", "larger"],
      ["MDRAC", "as DRAC after a reaction time", "reaction time", "m/s²", "larger"],
      ["DCIA", "follower keeps its acceleration during the reaction time, then brakes to match speeds at contact", "reaction time", "m/s²", "larger"],
      ["PSD", "gap divided by the follower's stopping distance", "follower deceleration", "1", "smaller"],
      ["MPSD", "as PSD with the distance covered during the reaction time", "follower deceleration, reaction time", "1", "smaller"],
      ["SDI", "both brake; 1 if the follower cannot stop behind the stopped leader", "both decelerations, reaction time", "0 or 1", "1"]]),
    ("p", "Contact and reporting. The contact module names the face and corner that touch first on a collision course, and the pair that would touch "
          "if the road user ahead were delayed by TAdv on a crossing course; the ten corner-side configurations of Jiménez et al. [@jimenez2013] "
          "come out as classes. Further modules give observed post-encroachment time, a hierarchy of encounters, prediction-error scales, scenario "
          "summaries and comparisons, plots, and a bank of conflict windows."),
    ("h", "Verification."),
    ("p", "The suite has {{tests/total}} automated tests. The polygon was compared with an independent implementation of the printed 2010 "
          "procedure on {{equiv/n:,}} random encounters of cars, pedestrians, cyclists and trucks: {{equiv/compared:,}} are covered by the procedure "
          "({{equiv/overlap_excluded:,}} start with overlapping bodies, which it does not treat), and the two disagree on {{equiv/disagree_total}} of "
          "the {{equiv/compared:,}} for TTC, TAdv, T2, TG and the first road user ({fig:verif}). With a side parallel to an axis the printed in-section test "
          "needs an exact equality of floating-point numbers; a literal implementation misses the TTC of {{equiv/axis_literal_ttc_misses:,}} of "
          "{{equiv/axis_compared:,}} such cases. The car-following measures are tested against independent time-stepping simulations of their stories. "
          "The polygon is not faster than a vectorised enumeration of the 32 combinations ({{bench/us_per:.1f}} µs against "
          "{{bench/vector32_us:.1f}} µs per encounter, a ratio of {{bench/ratio_poly_vec:.2f}}); its value is agreement with the printed procedure and one "
          "code path for the cases the procedure does not treat (parallel paths, standing road users, overlapping bodies). The general 12-row form, "
          "which any convex shape uses, takes {{bench/ratio12_8:.2f}} times as long as the 8-row form."),
    ("fig", "verif", "fig3_verification",
     "Checks of the package. (A) The polygon against the printed procedure: no disagreement in the compared encounters, and the share of "
     "axis-parallel cases in which a literal implementation of the procedure misses the TTC. (B) Time per encounter for a million encounters, logarithmic "
     "axis; the per-encounter loop is a pure-Python reference and not a like-for-like comparison. (C) Automated tests by area."),
    ("h", "Usage."),
    ("p", "The listing reads one NGSIM period, smooths it, sorts all encounters into levels, loads the shipped bank, plots one window, and computes "
          "the ten car-following measures of a synthetic leader and follower. It ran in about {{listing/minutes:.0f}} minutes on the author's computer, "
          "most of it in the search of {{listing/n_enc:,}} encounters of the full period."),
    ("code", "from pyssms import datasets, hierarchy, io\n"
             "from pyssms import preprocessing, process, scenario, viz\n"
             "\n"
             "traj = io.read_ngsim(\"trajectories-0830am-0845am.txt\")\n"
             "traj = preprocessing.smooth_trajectories(traj, window=5)\n"
             "enc = process.encounters(traj, horizon=10.0)\n"
             "print(hierarchy.build_hierarchy(enc).table())\n"
             "\n"
             "bank = datasets.load_conflict_bank(\"ngsim\")\n"
             "w = bank.window(bank.select(\"B\")[0])\n"
             "e = process.pair_series(w, 0, 1)   # TTC, TAdv, T2, TG\n"
             "viz.plot_indicator_profile(e)\n"
             "\n"
             "m = scenario.following_measures(   # ten measures, 1-D\n"
             "    datasets.make(\"following\"), leader=0, follower=1)"),
]
EN["sections"]["examples"] = [
    ("h", "One encounter, four readings."),
    ("p", "Two cars of {{fig2/len:.1f}} × {{fig2/wid:.1f}} m cross at right angles at {{fig2/speed:.0f}} m/s, {{fig2/d1:.0f}} m and {{fig2/d2:.0f}} m from "
          "the crossing point ({fig:poly}). The polygon K does not meet the diagonal, so the encounter is a crossing course (state B): TAdv is "
          "{{fig2/tadv:.2f}} s, the horizontal distance from K to the diagonal (panel B), and T2 is {{fig2/tau2:.3f}} s. The contact module reports that, "
          "were the first road user delayed by TAdv, the two bodies would touch at corners and not overlap (panel A). Panel C puts three encounters in "
          "one plane: a collision course (state A) with a TTC of {{fig2/ttc_a:.2f}} s, an oblique crossing (state B) with a TAdv of {{fig2/tadv_b:.2f}} s, and "
          "a pair too far apart for the horizon (state C)."),
    ("h", "Ten car-following measures on freeway data."),
    ("p", "We applied the ten measures to follower-leader pairs of {{highd/recordings}} highD recordings ({{highd/pair_frames:,}} pair-frames), "
          "{{exid/recordings}} exiD recordings ({{exid/pair_frames:,}}) and {{ngsim/recordings}} NGSIM freeway periods ({{ngsim/pair_frames:,}}), sampled once per second. "
          "The leader is the vehicle ahead in the same lane. The reaction time ({{params/rt:.0f}} s) and both decelerations ({{params/dec_l:.0f}} m/s²) were fixed before the run; they "
          "are assumptions of the stories, not data. No outcome is used, so nothing here ranks a measure or validates it."),
    ("p", "The choice of story decides which rows are critical ({fig:ten}). On highD {{highd/m/ttc1/crit:.2f}} % of sampled rows have TTC1 of 3 s or less "
          "but {{highd/m/ttcd/crit:.1f}} % have TTCD of 3 s or less, a ratio of {{highd/ratio_ttcd_ttc1:.0f}}; on exiD the shares are "
          "{{exid/m/ttc1/crit:.2f}} % and {{exid/m/ttcd/crit:.1f}} %, and on NGSIM {{ngsim/m/ttc1/crit:.1f}} % and {{ngsim/m/ttcd/crit:.1f}} %. TTC1 is "
          "defined (finite and within the prediction horizon) for only {{highd/m/ttc1/defined:.0f}} % of highD rows, since it needs a closing pair, and TTCD for "
          "{{highd/m/ttcd/defined:.0f}} %. Parameters matter as well, and not always in the same direction: with a reaction time of {{params/rt_alt:.1f}} s "
          "and decelerations of {{params/dec_alt:.0f}} m/s², the share of highD rows with TTCD of 3 s or less falls from {{highd/alt_ttcd_crit/0:.1f}} % to "
          "{{highd/alt_ttcd_crit/1:.1f}} %, whereas the share with SDI equal to one rises from {{highd/alt_sdi_crit/0:.1f}} % to {{highd/alt_sdi_crit/1:.1f}} %."),
    ("fig", "ten", "fig4_ten_measures",
     "The four time measures on three data sets. (A) Range from percentile 5 to percentile 95 (thin line), interquartile range (thick bar) "
     "and median (white tick) of the defined values; the percentage is the share of sampled rows where the measure is defined (finite and within the "
     "horizon, which cuts off the largest values). (B) Share of sampled rows with the measure at 3 s or less, logarithmic axis; the bracket marks the "
     "ratio of TTCD to TTC1 on highD."),
    ("p", "The measures also order pairs differently ({fig:rho}). MPSD and the polygon's TG rank the pairs alike on all three data sets (Spearman ρ = "
          "{{highd/rho/mpsd/k_tg:.2f}}, {{exid/rho/mpsd/k_tg:.2f}} and {{ngsim/rho/mpsd/k_tg:.2f}}). TTCD and PSD follow TAdv and TG closely on the German "
          "freeways (ρ from {{exid/rho/psd/k_tadv:.2f}} to {{highd/rho/psd/k_tg:.2f}}) but less so on NGSIM (TTCD with TAdv {{ngsim/rho/ttcd/k_tadv:.2f}}, "
          "PSD with TAdv {{ngsim/rho/psd/k_tadv:.2f}}), whereas TTC1 and TAdv are nearly unrelated on highD (ρ = {{highd/rho/ttc1/k_tadv:+.2f}}). "
          "Where both are defined, TTC1 and the polygon TTC rank the pairs identically on highD (ρ = {{highd/rho/ttc1/k_ttc:.2f}}), but "
          "differ in value by up to {{highd/poly_ttc_maxdiff:.1f}} s (highD), {{exid/poly_ttc_maxdiff:.1f}} s (exiD) and {{ngsim/poly_ttc_maxdiff:.1f}} s (NGSIM), "
          "because TTC1 sees only the longitudinal geometry. The polygon TTC exists for {{highd/poly_share:.0f}} % of the highD rows where TTC1 is within the "
          "horizon; in the other {{highd/poly_missing_share:.0f}} % the two bodies miss each other in two dimensions although TTC1 is finite."),
    ("fig", "rho", "fig5_correlations",
     "Spearman rank correlation between the ten car-following measures (rows, grouped by motion story; ▲ more critical when larger, ▼ when smaller) "
     "and polygon-based indicators (columns), pairwise on defined values. Required braking is the smallest constant deceleration that avoids a contact "
     "within the horizon (module escape). Outlined cells: correlation of 0.90 or more after rounding to two decimals. TTC1 enters only where it exists, "
     "and SDI is binary."),
    ("p", "Checks guard the reading. On highD the clear gap computed by pyssms equals the data set's own headway within {{highd/gap_abs_max:.3f}} m. "
          "On exiD the difference lies between {{exid/gap_p5:.2f}} and {{exid/gap_p95:.2f}} m from percentile 5 to percentile 95 (largest {{exid/gap_abs_max:.1f}} m). "
          "On NGSIM it lies between {{ngsim/gap_p5:.2f}} and {{ngsim/gap_p95:.2f}} m, with a largest value of {{ngsim/gap_abs_max:.1f}} m (lane changes, or "
          "the preceding-vehicle column lagging behind the positions); nothing was removed."),
    ("h", "Hierarchy of encounters and the effect of preprocessing."),
    ("p", "The hierarchy sorts every candidate vehicle pair of a recording into level A (by TTC), B (by TAdv) or C (no overlap), with a split by severity. "
          "We ran it on {{hier_total_recordings}} recordings of six data sets (inD, rounD, uniD, exiD, highD and ten NGSIM periods), "
          "{{hier_total_pairs:,}} candidate pairs of motor vehicles ({fig:hier}). The collision-course share runs from {{hier/highD/A:.0f}} % of pairs on highD "
          "to {{hier/NGSIM/A:.0f}} % on NGSIM, and the shape of the hierarchy differs by site: on exiD {{hier/exiD/B:.0f}} % of pairs are crossing courses "
          "against {{hier/exiD/A:.0f}} % collision courses. The counts are descriptive and say nothing about which encounters were dangerous."),
    ("p", "Preprocessing changes the counts. NGSIM's acceleration column differs from the derivative of its speed column by {{ngsim_acc_rms/us101:.1f}} m/s² "
          "(US-101) and {{ngsim_acc_rms/i80:.1f}} m/s² (I-80) root mean square, a defect known from the literature [@thiemann2008,@montanino2015]. "
          "At Peachtree Street the share of pairs reaching TTC below 1.5 s is {{smooth/raw_ttc15:.1f}} % on the data set's own positions and speeds and "
          "{{smooth/smoothed_ttc15:.1f}} % after a causal five-frame smoothing (panel B; the two runs differ in positions and in the speed source), and the share of "
          "pairs with no overlap falls from {{smooth/raw_C:.1f}} % to {{smooth/smoothed_C:.1f}} %. "
          "The package does not choose for the user: smoothing is a visible step that must be reported."),
    ("fig", "hier", "fig6_hierarchy",
     "(A) Candidate pairs of motor vehicles whose future paths overlap, split into levels A and B (TTC and TAdv classes); the labels give the shares of "
     "all pairs in level A and in levels A or B (paths overlap), and the number of pairs. (B) Effect of smoothing on NGSIM, Peachtree Street."),
]
EN["sections"]["impact"] = [
    ("p", "What pyssms changes for a researcher is traceability. A safety indicator computed from a drone recording passes through a reader, a "
          "preprocessing choice, a pair filter, a motion story and a threshold. In pyssms each is one visible function with stated assumptions, and "
          "the numbers in this paper were produced by scripts in the repository from the result files, not typed. The examples show why this "
          "matters: the same pairs are critical in {{highd/m/ttc1/crit:.2f}} % or {{highd/m/ttcd/crit:.0f}} % of highD rows depending on a story, and an NGSIM "
          "count moves with a smoothing window."),
    ("p", "The package serves three uses. First, teaching and method comparison: the shipped bank of {{bank/windows}} NGSIM windows ({{bank/A}} chosen by "
          "smallest TTC, {{bank/B}} by smallest TAdv, {{bank/C}} by smallest distance; {{bank/mb:.1f}} MB) lets a student run every indicator without downloading a data "
          "set. The windows are chosen by the package's own indicators, so they are test material, not a sample of traffic: in the {{bank/A}} windows chosen by smallest TTC "
          "the smallest TTC has a median of {{bank/min_ttc_median_A:.3f}} s and never exceeds {{bank/min_ttc_max_A:.2f}} s, at centre distances of "
          "{{bank/dist_min_A:.1f}} to {{bank/dist_max_A:.1f}} m, so the rectangular bodies are about to touch. Second, "
          "wherever the 2010 indicators are needed for arbitrary convex shapes, one tested function replaces hand-coded enumeration of corner and side combinations. Third, a "
          "common platform on which the validation of indicators against outcomes can be done: a reader, an outcome extractor (braking onset), and "
          "counts of encounters per level are in place. Such a validation was named the most critical next step of the car-following framework [@naseralavi2025]; "
          "evasive-action onset is a candidate outcome [@johnsson2022]. It has not been done here, and the examples above must not be read as one."),
    ("p", "The software is young. Version {{version}} is the initial release of the package; it has no record of use outside the author's own work and "
          "no citations yet, and it is installed from its repository rather than from a package index. The shipped NGSIM windows carry the licence text of the Federal Highway Administration (a modified Creative "
          "Commons Attribution 2.0 licence); nothing from the LevelX data sets is shipped except counts and prediction-error scales. The "
          "limits that matter for use are the assumptions of the model. K assumes constant velocity and translation without rotation, so a turning "
          "vehicle is predicted along its current heading; the ten car-following measures are one-dimensional and need a leader and a follower "
          "along a lane; their parameters are assumptions; and no two-dimensional version of those ten measures exists yet. A companion methods "
          "manuscript on the geometry of K is in preparation. The package does not replace criticality metrics designed for automated "
          "driving [@westhofen2023]; it supplies the indicators of the 2010 and 2025 papers with tests."),
]
EN["sections"]["conclusions"] = [
    ("p", "pyssms brings the two-dimensional indicators of the 2010 framework and the ten car-following measures of the 2025 framework into one tested Python package "
          "that reads the files of the common data sets. Verification is part of the package: {{tests/total}} tests, agreement with the printed procedure "
          "on {{equiv/compared:,}} encounters, and simulations of the motion stories. The examples show that results depend on choices that code makes "
          "visible: the motion story, its parameters and the smoothing of positions. Everything reported is descriptive. The next steps are validation "
          "against observed outcomes and a two-dimensional version of the car-following measures" + ("" if ZENODO_DOI else ", and an archived release with a persistent identifier") + "."),
]
EN["ack"] = "The author thanks the providers of the highD, inD, rounD, exiD and NGSIM data for making them available for research."
EN["ai"] = ("During the preparation of this work the author used Claude (Anthropic) as an assistant for study planning, writing and running analysis code and tests, "
            "producing figures, literature screening, and drafting and editing the text. After using this tool, the author reviewed, verified and edited the material "
            "(code, results, references and text) and takes full responsibility for the content of the publication. Numbers in the text are inserted by code "
            "from the result files, and the references were checked against a bibliographic database.")
EN["credit"] = ("Seyed Saber Naseralavi: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, "
                "Writing – original draft, Writing – review & editing, Visualization.")
EN["funding"] = "This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors."
EN["competing"] = "The author declares that he has no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper."
EN["data"] = ("The code is available at " + REPO + " (BSD 3-Clause licence)" + (", and version " + VERSION + " is archived on Zenodo [@pyssms_zenodo]" if ZENODO_DOI else "") + ". The shipped NGSIM windows come from the Federal Highway Administration "
              "NGSIM data under a modified Creative Commons Attribution 2.0 licence (credit FHWA and NGSIM). The LevelX data sets are available from their "
              "providers on request; only aggregated counts are shipped. The numbers of this paper are reproduced by paper_softwarex/make_numbers.py.")
EN["exec_version"] = f"v{VERSION}, installed from the repository ({REPO})."
EN["highlights"] = [
    "One package for 2-D TTC indicators and ten car-following measures",
    "One exact conflict polygon replaces 32 corner-side combinations",
    "Readers for SSAM, SUMO, VISSIM, LevelX and NGSIM trajectories",
    "{{tests/total}} tests; {{equiv/compared:,}} random encounters compared",
    "Critical share depends on the story: {{highd/m/ttc1/crit:.2f}} % or {{highd/m/ttcd/crit:.0f}} %",
]

# ----------------------------------------------------------------------------------------------------------------- Persian
FA: dict = {}
FA["title"] = "pyssms: یک بستهٔ پایتون برای شاخص‌های دوبعدی زمان تا برخورد و سنجه‌های جانشین ایمنی دنباله‌روی"
FA["keywords"] = ["سنجه‌های جانشین ایمنی", "زمان تا برخورد", "مزیت زمانی", "داده‌های مسیر", "تداخل‌های ترافیکی", "پایتون"]
FA["abstract"] = (
    "سنجه‌های جانشین ایمنی مسیر کاربران راه را به عددهایی تبدیل می‌کنند که نشان می‌دهند یک رویارویی چقدر به برخورد نزدیک شده است. "
    "دو خانوادهٔ این سنجه‌ها تاکنون در کدهای جدا زندگی کرده‌اند: شاخص‌های دوبعدی که برای هر زاویهٔ رویکرد تعریف می‌شوند، "
    "و سنجه‌های یک‌بعدی دنباله‌روی که بر داستان‌های کوتاه حرکت بنا شده‌اند. pyssms بسته‌ای پایتونی است که هر دو را بر یک پایه می‌نشاند. "
    "زمان تا برخورد، مزیت زمانی، T2 و فاصلهٔ زمانی دقیقاً از یک چندضلعی محدب تداخل خوانده می‌شوند و ده سنجهٔ دنباله‌روی از روی داستان‌های حرکتی که "
    "فرض می‌کنند پیاده شده‌اند. بسته مسیرهای SSAM، SUMO، VISSIM، LevelX و NGSIM را می‌خواند، هموار می‌کند، جفت‌های نامزد را می‌یابد، رویارویی‌ها را "
    "در یک سلسله‌مراتب مرتب می‌کند، وجه‌ها و گوشه‌های در تماس را نام می‌برد و {{bank/windows}} پنجرهٔ تداخل بریده‌شده از NGSIM را همراه خود دارد. "
    "تنها به NumPy و PyYAML وابسته است. درستی آزموده می‌شود، نه ادعا: {{tests/total}} آزمون خودکار، "
    "هم‌خوانی با روش چاپ‌شده روی {{equiv/compared:,}} رویارویی تصادفی و شبیه‌سازی‌های مستقل داستان‌های حرکتی. "
    "با اجرا روی {{highd/recordings}} ضبط highD، {{exid/recordings}} ضبط exiD و {{ngsim/recordings}} ضبط بزرگراهی NGSIM، سهم ردیف‌های highD "
    "با زمان تا برخورد ۳ ثانیه یا کمتر {{highd/m/ttc1/crit:.2f}} % است اگر سرعت‌ها ثابت فرض شوند و {{highd/m/ttcd/crit:.0f}} % اگر فرض شود "
    "پیشرو تا ایستادن ترمز می‌کند. همهٔ آمارها توصیفی‌اند. نسخهٔ {{version}} نخستین انتشار بسته است."
)
FA["meta"] = EN["meta"]
FA["sections"] = {}
FA["sections"]["motivation"] = [
    ("p", "بپرسید آیا جفت‌های دنباله‌روی یک ضبط بزرگراهی در خطرند. تحلیلگری که سرعت‌های ثابت را فرض می‌کند "
          "{{highd/m/ttc1/crit:.2f}} % ردیف‌های نمونهٔ highD را در زمان تا برخورد ۳ ثانیه یا کمتر برچسب می‌زند؛ آن‌که فرض می‌کند پیشرو تا ایستادن ترمز می‌کند "
          "{{highd/m/ttcd/crit:.0f}} %. هیچ‌یک اشتباه نکرده است: هر یک داستان حرکتی‌ای برگزیده است. عددِ یک مقاله پایان زنجیره‌ای از انتخاب‌هاست، "
          "یعنی خوانندهٔ پرونده، پنجرهٔ هموارسازی، پالایهٔ جفت، داستان و آستانه، و این زنجیره کمتر دیده می‌شود. "
          "pyssms ساخته شده است تا آن را دیدنی کند."),
    ("p", "سنجه‌های جانشین ایمنی (SSM) نشان می‌دهند کاربران راه چقدر به برخورد نزدیک شده‌اند، بی‌آنکه منتظر تصادف بمانیم [@arun2021,@zheng2021]. "
          "ضبط‌های پهپادی مانند highD، inD، rounD و exiD [@krajewski2018,@bock2020,@krajewski2020,@moers2022] و مسیرهای خودرویی NGSIM [@ngsim2017] اکنون "
          "مسیرها را در مقیاس بزرگ فراهم می‌کنند، و سال‌هاست که مدل ارزیابی ایمنی جانشین FHWA سنجه‌ها را از مسیرهای شبیه‌سازی‌شده به دست می‌آورد "
          "[@gettman2003]. آنچه کم است کد باز و آزموده‌ای است که تعریف‌های منتشرشده را روی چنین پرونده‌هایی به کار ببندد تا عددِ یک مقاله به یک "
          "خط کد برسد."),
    ("p", "دو سنت باید در این کد به هم برسند. لارشین، سونسون و هیدن [@laureshyn2010] زمان تا برخورد (TTC)، مزیت زمانی (TAdv)، T2 و فاصلهٔ زمانی (TG) را برای هر زاویهٔ "
          "رویکرد، با نمایش کاربران راه به‌صورت مستطیل، با شمارش ۳۲ ترکیب از یک گوشهٔ یک کاربر و یک ضلع دیگری تعریف کردند. ناصرعلوی و همکاران [@naseralavi2025] ده سنجهٔ دنباله‌روی را "
          "بر پایهٔ داستان کوتاه حرکتی هر یک کدگذاری کردند: سرعت، شتاب یا جرک ثابت برای TTC1، TTC2 و TTC3، پیشروی ترمزگیر برای TTCD و ترمز تعقیب‌کننده برای "
          "DRAC، MDRAC، DCIA، PSD، MPSD و SDI. اولی هندسی است و برای تقاطع و ادغام کار می‌کند؛ دومی سینماتیکی است و در امتداد یک خط عبور. هر کدام معمولاً، "
          "اگر اصلاً پیاده شود، جداگانه و برای یک مجموعه‌داده پیاده می‌شود."),
    ("p", "نرم‌افزارهای باز مرتبط: Traffic Intelligence [@saunier] مسیرها و پیش‌بینی حرکت را پردازش می‌کند و یک TTC دوبعدیِ برداری روی GitHub "
          "منتشر شده است [@jiao]. جست‌وجوی سبک در 2026-11-01 (مرور نظام‌مند نیست) بسته‌ای نیافت که شاخص‌های دوبعدیِ مقالهٔ ۲۰۱۰ را برای هر شکل و زاویه "
          "همراه با ده سنجهٔ دنباله‌روی و قالب‌های پرونده‌های مجموعه‌داده‌های رایج بخواند. pyssms برای پر کردن همین شکاف نوشته شده است. این بسته (الف) مسیرها را می‌خواند، "
          "(ب) TTC، TAdv، T2 و TG را دقیقاً روی یک چندضلعی تداخل حساب می‌کند، (پ) ده سنجهٔ دنباله‌روی را حساب می‌کند، (ت) وجه‌ها و گوشه‌های در تماس را نام می‌برد، "
          "(ث) رویارویی‌ها را در یک سلسله‌مراتب خلاصه می‌کند و (ج) بانک کوچکی از پنجره‌های تداخل برای آزمون و آموزش همراه دارد. عددهایش با روش چاپ‌شده، با "
          "شبیه‌سازی‌ها و با ستون‌های خود مجموعه‌داده‌ها سنجیده شده‌اند."),
]
FA["sections"]["architecture"] = [
    ("p", "pyssms دارای {{modules/n}} ماژول در چهار لایه است (خواندن، آماده‌سازی، محاسبه، گزارش؛ {fig:arch}). فقط NumPy و PyYAML لازم است؛ "
          "matplotlib برای رسم اختیاری است. کد نوع‌دار و مستند است و هر ماژول در docstring خود فرض‌هایش را می‌گوید."),
    ("p", "هستهٔ محاسبه یک ایدهٔ هندسی است. فرض کنید τ₁ و τ₂ زمان‌های پیش‌بینی‌شدهٔ رسیدن کاربران ۱ و ۲ به مکان‌های داده‌شده روی مسیرهایشان باشند. جفت‌های (τ₁, τ₂) "
          "که در آن‌ها دو بدنه هم‌پوشانی می‌کنند یک چندضلعی محدب K در صفحهٔ دو زمان رسیدن پیش‌بینی‌شده می‌سازند؛ K تفاضل مینکوفسکی دو بدنه در همان صفحه است "
          "({fig:poly}، پنل B). چون بدنه‌ها محدب و سرعت‌ها ثابت‌اند، K مجموعهٔ جواب چند نابرابری خطی در (τ₁, τ₂) است: هشت نابرابری برای دو مستطیل که در امتداد طول خود حرکت می‌کنند "
          "و دوازده نابرابری در حالت کلی. حرکت بدون اختلال قطر τ₁ = τ₂ است. اگر K قطر را قطع کند، "
          "کاربران در مسیر برخورد هستند (حالت A) و TTC جایی است که قطر وارد K می‌شود. اگر K قطر را قطع نکند (حالت B، مسیر متقاطع)، TAdv کوچک‌ترین |τ₁ − τ₂| روی K است "
          "و T2 و TG از همان چندضلعی به‌عنوان زودترین رسیدن‌های دوم خوانده می‌شوند. اگر K در افق پیش‌بینی تهی باشد هم‌پوشانی نیست (حالت C). "
          "۳۲ ترکیب پیوست مقالهٔ ۲۰۱۰ یک چندضلعی می‌شود و مسیرهای موازی، کاربران ایستاده و بدنه‌های هم‌پوشان به حالت ویژه نیاز ندارند. "
          "نمودارهای مسیر-زمان از این دست در برنامه‌ریزی حرکت ربات‌ها کلاسیک‌اند [@odonnell1989,@kant1986]."),
    ("p", "چهار قاعدهٔ طراحی از مثال آغازین برمی‌آید. هر فرض (زمان واکنش، کاهش سرعت، افق، پنجرهٔ هموارسازی) آرگومانی نام‌دار است؛ هر جا پیش‌فرضی هست در امضای تابع و "
          "docstring دیدنی است و توابع ssm1d زمان واکنش و کاهش سرعت‌ها را بدون پیش‌فرض می‌گیرند. "
          "سنجه‌ای که برای یک جفت وجود ندارد NaN است، نه صفر: TTC تا وقتی جفت روی مسیر برخورد نباشد تعریف نشده است. هر ماژول با یک مرجع مستقل سنجیده می‌شود، "
          "مانند شبیه‌سازی گام‌به‌گام یا پیاده‌سازی روش چاپ‌شده، نه با خودش. داده بیرون از بسته می‌ماند و بسته فقط یک بانک کوچک NGSIM و شمارش‌ها را همراه دارد."),
    ("fig", "arch", "fig1_architecture",
     "ساختار pyssms: چهار لایه از خواننده‌های پرونده تا گزارش‌ها. دنبالهٔ تصمیم هر جفت و هر قاب را به حالت A، B یا C می‌فرستد؛ مسیر دوم سری پیشرو-تعقیب‌کننده را "
     "به ده سنجهٔ دنباله‌روی می‌برد که به K نیاز ندارند. پیکان خط‌چین به خوانش‌های دیگر همان رویارویی می‌رود. نوار پایین بررسی‌های بسته را نام می‌برد."),
    ("fig", "poly", "fig2_polygon",
     "یک رویارویی در سه نما. (A) نمای بالا: طرح خط‌چین در آغاز، بدنه‌های پُر در جایی که اگر کاربر ۱ به‌اندازهٔ TAdv دیر می‌رسید تماس می‌گرفتند "
     "(هر بدنه در زمان رسیدن خودش؛ دایره: گوشه‌های در تماس). (B) چندضلعی تداخل K در صفحهٔ دو زمان رسیدن پیش‌بینی‌شده، با قطر، TAdv و T2. "
     "(C) همین ساختار برای سه رویارویی در یک صفحه: قطر در حالت A وارد K می‌شود (TTC)، K در حالت B کنار قطر است (TAdv) و در حالت C K بیرون افق (مربع سایه‌خورده) است."),
    ("h", "قابلیت‌های نرم‌افزار."),
    ("p", "خواننده‌ها و آماده‌سازی. مسیرها از پرونده‌های .trj نرم‌افزار SSAM (خواندن و نوشتن)، خروجی خودروی شناور SUMO، VISSIM .fzp، پرونده‌های LevelX "
          "(inD، rounD، uniD، exiD، highD)، NGSIM و جدول‌های عمومی در یک شیء Trajectories خوانده می‌شوند. خوانندهٔ NGSIM فوت را به متر تبدیل می‌کند و مرجع را از مرکز "
          "جلو به مرکز بدنه می‌برد. هموارسازی علّی یا مرکزی گامی جدا و آشکار است."),
    ("p", "شاخص‌ها. TTC، TAdv، T2 و TG برای آرایه‌هایی از رویارویی‌ها حساب می‌شوند، با شکل ۸ ردیفی چندضلعی برای بدنه‌هایی که در امتداد طول خود حرکت می‌کنند و شکل ۱۲ ردیفی عمومی "
          "برای هر شکل محدب. حاشیه‌ها، جست‌وجوی کمترین ترمز (escape) و مجموعهٔ اختلال خوانش‌های دیگری از همان چندضلعی می‌افزایند. دلتا-وی، دلتا-وی گسترش‌یافته [@laureshyn2017] "
          "و منحنی‌های خطر جراحت [@lubbe2022] شدت را می‌دهند."),
    ("p", "سنجه‌های دنباله‌روی. TTC1، TTC2، TTC3، TTCD، DRAC، MDRAC، DCIA، PSD، MPSD و SDI از روی داستان‌هایشان نوشته شده‌اند، نه کپی فرمول‌های چاپی. "
          "هر جا شکل چاپی با استنتاج خودش فرق دارد تفاوت‌ها فهرست شده است (docs/ssm1d_notes.md)؛ زمان واکنش و کاهش سرعت‌ها ورودی توابع ssm1d هستند و پیش‌فرض ندارند. {tab:ten} سنجه‌ها را فهرست می‌کند."),
    ("table", "ten", "ده سنجهٔ دنباله‌روی در ssm1d: داستان حرکتی هر یک، ورودی‌های آن جز فاصله و سرعت‌ها، یکا و جهتی که در آن مقدار بحرانی‌تر است.",
     ["سنجه", "داستان حرکتی", "ورودی‌های دیگر", "یکا", "بحرانی‌تر وقتی"],
     [["TTC1", "سرعت‌های ثابت", "ندارد", "s", "کوچک‌تر"],
      ["TTC2", "شتاب‌های ثابت", "ندارد", "s", "کوچک‌تر"],
      ["TTC3", "جرک‌های ثابت", "ندارد", "s", "کوچک‌تر"],
      ["TTCD", "پیشرو تا ایستادن ترمز می‌کند و تعقیب‌کننده سرعتش را نگه می‌دارد", "کاهش سرعت پیشرو", "s", "کوچک‌تر"],
      ["DRAC", "تعقیب‌کننده بی‌درنگ ترمز می‌کند تا سرعت نزدیک‌شدن را بردارد", "ندارد", "m/s²", "بزرگ‌تر"],
      ["MDRAC", "مانند DRAC پس از یک زمان واکنش", "زمان واکنش", "m/s²", "بزرگ‌تر"],
      ["DCIA", "تعقیب‌کننده در زمان واکنش شتابش را نگه می‌دارد، سپس ترمز می‌کند تا سرعت‌ها در تماس برابر شوند", "زمان واکنش", "m/s²", "بزرگ‌تر"],
      ["PSD", "فاصله تقسیم بر مسافت توقف تعقیب‌کننده", "کاهش سرعت تعقیب‌کننده", "1", "کوچک‌تر"],
      ["MPSD", "مانند PSD با مسافت پیموده‌شده در زمان واکنش", "کاهش سرعت تعقیب‌کننده، زمان واکنش", "1", "کوچک‌تر"],
      ["SDI", "هر دو ترمز می‌کنند؛ 1 اگر تعقیب‌کننده پشت پیشروی ایستاده نتواند بایستد", "هر دو کاهش سرعت، زمان واکنش", "0 یا 1", "1"]]),
    ("p", "تماس و گزارش. ماژول تماس وجه و گوشه‌ای را که روی مسیر برخورد اول تماس می‌گیرند، و جفتی را که اگر کاربر جلویی به‌اندازهٔ TAdv دیر می‌رسید در مسیر متقاطع "
          "تماس می‌گرفت، نام می‌برد؛ ده پیکربندی گوشه-ضلع خیمنز و همکاران [@jimenez2013] به‌صورت رده بیرون می‌آیند. ماژول‌های دیگر زمان پس از تجاوز مشاهده‌شده، سلسله‌مراتب رویارویی‌ها، "
          "مقیاس‌های خطای پیش‌بینی، خلاصه و مقایسهٔ سناریو، رسم‌ها و بانک پنجره‌های تداخل را می‌دهند."),
    ("h", "راستی‌آزمایی."),
    ("p", "مجموعهٔ آزمون {{tests/total}} آزمون خودکار دارد. چندضلعی با پیاده‌سازی مستقلِ روش چاپ‌شدهٔ ۲۰۱۰ روی {{equiv/n:,}} رویارویی تصادفی خودرو، عابر، دوچرخه‌سوار و کامیون "
          "سنجیده شد: {{equiv/compared:,}} مورد را روش پوشش می‌دهد ({{equiv/overlap_excluded:,}} با بدنه‌های هم‌پوشان در آغاز شروع می‌شوند که روش آن را بررسی نمی‌کند) و "
          "این دو در {{equiv/disagree_total}} مورد از {{equiv/compared:,}} برای TTC، TAdv، T2، TG و کاربر نخست ناهم‌خوانی دارند ({fig:verif}). وقتی ضلعی موازی محور باشد، آزمون درون‌بخشِ چاپی "
          "برابری دقیق اعداد ممیز شناور می‌خواهد؛ پیاده‌سازی تحت‌اللفظی TTC را در {{equiv/axis_literal_ttc_misses:,}} مورد از {{equiv/axis_compared:,}} مورد چنین از دست می‌دهد. "
          "سنجه‌های دنباله‌روی با شبیه‌سازی‌های گام‌به‌گام مستقلِ داستان‌هایشان آزموده می‌شوند. چندضلعی از شمارش برداری ۳۲ ترکیب سریع‌تر نیست "
          "({{bench/us_per:.1f}} میکروثانیه در برابر {{bench/vector32_us:.1f}} میکروثانیه برای هر رویارویی، نسبت {{bench/ratio_poly_vec:.2f}})؛ ارزش آن هم‌خوانی با روش چاپ‌شده و "
          "یک مسیر کد برای حالت‌هایی است که روش چاپ‌شده بررسی نمی‌کند (مسیرهای موازی، کاربران ایستاده، بدنه‌های هم‌پوشان). شکل عمومی ۱۲ ردیفی، که هر شکل محدب از آن استفاده می‌کند، "
          "{{bench/ratio12_8:.2f}} برابر شکل ۸ ردیفی زمان می‌برد."),
    ("fig", "verif", "fig3_verification",
     "بررسی‌های بسته. (A) چندضلعی در برابر روش چاپ‌شده: هیچ ناهم‌خوانی در رویارویی‌های سنجیده‌شده، و سهم حالت‌های موازی محور که پیاده‌سازی تحت‌اللفظی روش TTC آن‌ها را از دست می‌دهد. "
     "(B) زمان هر رویارویی برای یک میلیون رویارویی، محور لگاریتمی؛ حلقهٔ هر-رویارویی یک مرجع پایتون خالص است و مقایسهٔ هم‌سنگ نیست. (C) آزمون‌های خودکار به تفکیک بخش."),
    ("h", "کاربرد."),
    ("p", "فهرست زیر یک دورهٔ NGSIM را می‌خواند، هموار می‌کند، همهٔ رویارویی‌ها را در سطح‌ها مرتب می‌کند، بانک همراه را بار می‌کند، یک پنجره را رسم می‌کند و "
          "ده سنجهٔ دنباله‌روی یک پیشرو و تعقیب‌کنندهٔ مصنوعی را حساب می‌کند. اجرای آن روی رایانهٔ نویسنده حدود {{listing/minutes:.0f}} دقیقه طول کشید، "
          "بیشتر آن در جست‌وجوی {{listing/n_enc:,}} رویارویی کل دوره."),
    ("code", EN["sections"]["architecture"][-1][1]),
]
FA["sections"]["examples"] = [
    ("h", "یک رویارویی، چهار خوانش."),
    ("p", "دو خودروی {{fig2/len:.1f}} × {{fig2/wid:.1f}} متری با سرعت {{fig2/speed:.0f}} متر بر ثانیه، در {{fig2/d1:.0f}} و {{fig2/d2:.0f}} متری نقطهٔ تقاطع، با زاویهٔ قائم از هم می‌گذرند "
          "({fig:poly}). چندضلعی K قطر را قطع نمی‌کند، پس رویارویی مسیر متقاطع است (حالت B): TAdv برابر {{fig2/tadv:.2f}} ثانیه است، یعنی فاصلهٔ افقی K تا قطر (پنل B)، "
          "و T2 برابر {{fig2/tau2:.3f}} ثانیه. ماژول تماس گزارش می‌دهد که اگر کاربر نخست به‌اندازهٔ TAdv دیر می‌رسید، دو بدنه در گوشه‌ها تماس می‌گرفتند و هم‌پوشانی نمی‌کردند (پنل A). "
          "پنل C سه رویارویی را در یک صفحه می‌گذارد: مسیر برخورد (حالت A) با TTC برابر {{fig2/ttc_a:.2f}} ثانیه، تقاطع مایل (حالت B) با TAdv برابر {{fig2/tadv_b:.2f}} ثانیه، "
          "و جفتی که برای افق بیش از حد دور است (حالت C)."),
    ("h", "ده سنجهٔ دنباله‌روی روی داده‌های بزرگراهی."),
    ("p", "ده سنجه را روی جفت‌های پیشرو و تعقیب‌کنندهٔ {{highd/recordings}} ضبط highD ({{highd/pair_frames:,}} جفت-قاب)، {{exid/recordings}} ضبط exiD ({{exid/pair_frames:,}}) و {{ngsim/recordings}} دورهٔ "
          "بزرگراهی NGSIM ({{ngsim/pair_frames:,}}) به کار بردیم، با نمونه‌برداری یک‌بار در ثانیه. پیشرو خودروی جلویی در همان خط است. زمان واکنش ({{params/rt:.0f}} ثانیه) و هر دو کاهش سرعت "
          "({{params/dec_l:.0f}} متر بر مجذور ثانیه) پیش از اجرا ثابت شدند؛ آن‌ها فرض داستان‌اند، نه داده. هیچ پیامدی به کار نرفته است، پس هیچ‌چیز اینجا سنجه‌ای را رتبه نمی‌دهد یا اعتبارسنجی نمی‌کند."),
    ("p", "انتخاب داستان تعیین می‌کند کدام ردیف‌ها بحرانی‌اند ({fig:ten}). در highD {{highd/m/ttc1/crit:.2f}} % ردیف‌های نمونه TTC1 برابر ۳ ثانیه یا کمتر دارند "
          "اما {{highd/m/ttcd/crit:.1f}} % TTCD برابر ۳ ثانیه یا کمتر، نسبتی برابر {{highd/ratio_ttcd_ttc1:.0f}}؛ در exiD سهم‌ها "
          "{{exid/m/ttc1/crit:.2f}} % و {{exid/m/ttcd/crit:.1f}} % و در NGSIM {{ngsim/m/ttc1/crit:.1f}} % و {{ngsim/m/ttcd/crit:.1f}} % است. TTC1 فقط برای "
          "{{highd/m/ttc1/defined:.0f}} % ردیف‌های highD تعریف می‌شود (متناهی و درون افق پیش‌بینی) زیرا جفت نزدیک‌شونده می‌خواهد، و TTCD برای {{highd/m/ttcd/defined:.0f}} %. "
          "پارامترها هم اهمیت دارند و نه همیشه در یک جهت: با زمان واکنش {{params/rt_alt:.1f}} ثانیه و کاهش سرعت {{params/dec_alt:.0f}} متر بر مجذور ثانیه، سهم ردیف‌های highD با TTCD برابر ۳ ثانیه یا کمتر از "
          "{{highd/alt_ttcd_crit/0:.1f}} % به {{highd/alt_ttcd_crit/1:.1f}} % کاهش می‌یابد، در حالی که سهم ردیف‌ها با SDI برابر یک از {{highd/alt_sdi_crit/0:.1f}} % به {{highd/alt_sdi_crit/1:.1f}} % می‌رسد."),
    ("fig", "ten", "fig4_ten_measures",
     "چهار سنجهٔ زمانی روی سه مجموعه‌داده. (A) دامنهٔ صدک ۵ تا ۹۵ (خط نازک)، دامنهٔ میان‌چارکی (نوار ضخیم) و میانه (خط سفید) مقدارهای تعریف‌شده؛ درصد سهم ردیف‌های نمونه است که سنجه در آن‌ها تعریف می‌شود "
     "(متناهی و درون افق، که بزرگ‌ترین مقدارها را می‌برد). (B) سهم ردیف‌های نمونه با سنجه برابر ۳ ثانیه یا کمتر، محور لگاریتمی؛ کمانک نسبت TTCD به TTC1 را در highD نشان می‌دهد."),
    ("p", "سنجه‌ها جفت‌ها را هم به ترتیب متفاوتی مرتب می‌کنند ({fig:rho}). MPSD و TG چندضلعی جفت‌ها را در هر سه مجموعه‌داده همسان رتبه می‌دهند (ρ اسپیرمن = "
          "{{highd/rho/mpsd/k_tg:.2f}}، {{exid/rho/mpsd/k_tg:.2f}} و {{ngsim/rho/mpsd/k_tg:.2f}}). TTCD و PSD در بزرگراه‌های آلمان از نزدیک TAdv و TG را دنبال می‌کنند "
          "(ρ از {{exid/rho/psd/k_tadv:.2f}} تا {{highd/rho/psd/k_tg:.2f}}) اما در NGSIM کمتر (TTCD با TAdv {{ngsim/rho/ttcd/k_tadv:.2f}}، PSD با TAdv {{ngsim/rho/psd/k_tadv:.2f}})، "
          "در حالی که TTC1 و TAdv روی highD تقریباً بی‌ارتباط‌اند (ρ = {{highd/rho/ttc1/k_tadv:+.2f}}). "
          "جایی که هر دو تعریف شده‌اند، TTC1 و TTC چندضلعی در highD جفت‌ها را یکسان رتبه می‌دهند (ρ = {{highd/rho/ttc1/k_ttc:.2f}}) اما در مقدار تا "
          "{{highd/poly_ttc_maxdiff:.1f}} ثانیه (highD)، {{exid/poly_ttc_maxdiff:.1f}} ثانیه (exiD) و {{ngsim/poly_ttc_maxdiff:.1f}} ثانیه (NGSIM) فرق دارند، "
          "چون TTC1 فقط هندسهٔ طولی را می‌بیند. TTC چندضلعی برای {{highd/poly_share:.0f}} % ردیف‌های highD که TTC1 درون افق دارند وجود دارد؛ "
          "در {{highd/poly_missing_share:.0f}} % دیگر دو بدنه در دو بعد از هم می‌گذرند هرچند TTC1 متناهی است."),
    ("fig", "rho", "fig5_correlations",
     "هم‌بستگی رتبه‌ای اسپیرمن میان ده سنجهٔ دنباله‌روی (ردیف‌ها، گروه‌بندی‌شده بر پایهٔ داستان حرکتی؛ ▲ بحرانی‌تر وقتی بزرگ‌تر، ▼ وقتی کوچک‌تر) "
     "و شاخص‌های چندضلعی (ستون‌ها)، دوبه‌دو روی مقدارهای تعریف‌شده. ترمز لازم کوچک‌ترین کاهش سرعت ثابتی است که در افق تماس را پرهیز می‌دهد (ماژول escape). "
     "خانه‌های کادردار: هم‌بستگی ۰٫۹۰ یا بیشتر پس از گرد کردن به دو رقم اعشار. TTC1 فقط جایی که وجود دارد وارد می‌شود و SDI دودویی است."),
    ("p", "بررسی‌هایی از خوانش پاسداری می‌کنند. روی highD فاصلهٔ آزادی که pyssms حساب می‌کند با ستون headway خود مجموعه‌داده تا {{highd/gap_abs_max:.3f}} متر برابر است. "
          "روی exiD تفاوت از صدک ۵ تا صدک ۹۵ میان {{exid/gap_p5:.2f}} و {{exid/gap_p95:.2f}} متر است (بزرگ‌ترین {{exid/gap_abs_max:.1f}} متر). "
          "روی NGSIM میان {{ngsim/gap_p5:.2f}} و {{ngsim/gap_p95:.2f}} متر است، با بزرگ‌ترین مقدار {{ngsim/gap_abs_max:.1f}} متر (تغییر خط، یا ستون خودروی پیشین که از موقعیت‌ها عقب می‌ماند)؛ چیزی حذف نشد."),
    ("h", "سلسله‌مراتب رویارویی‌ها و اثر پیش‌پردازش."),
    ("p", "سلسله‌مراتب هر جفت خودروی نامزد یک ضبط را در سطح A (با TTC)، B (با TAdv) یا C (بدون هم‌پوشانی) می‌گذارد، با تفکیک شدت. "
          "آن را روی {{hier_total_recordings}} ضبط از شش مجموعه‌داده (inD، rounD، uniD، exiD، highD و ده دورهٔ NGSIM)، "
          "{{hier_total_pairs:,}} جفت نامزد خودروی موتوری اجرا کردیم ({fig:hier}). سهم مسیر برخورد از {{hier/highD/A:.0f}} % جفت‌ها در highD "
          "تا {{hier/NGSIM/A:.0f}} % در NGSIM است و شکل سلسله‌مراتب بسته به محل فرق می‌کند: در exiD {{hier/exiD/B:.0f}} % جفت‌ها مسیر متقاطع‌اند "
          "در برابر {{hier/exiD/A:.0f}} % مسیر برخورد. شمارش‌ها توصیفی‌اند و دربارهٔ اینکه کدام رویارویی خطرناک بود چیزی نمی‌گویند."),
    ("p", "پیش‌پردازش شمارش‌ها را تغییر می‌دهد. ستون شتاب NGSIM با مشتق ستون سرعتش به‌اندازهٔ {{ngsim_acc_rms/us101:.1f}} متر بر مجذور ثانیه "
          "(US-101) و {{ngsim_acc_rms/i80:.1f}} متر بر مجذور ثانیه (I-80) جذر میانگین مربعات فرق دارد، نقصی که در ادبیات شناخته است [@thiemann2008,@montanino2015]. "
          "در خیابان Peachtree سهم جفت‌هایی که به TTC کمتر از ۱٫۵ ثانیه می‌رسند روی موقعیت‌ها و سرعت‌های خود مجموعه‌داده {{smooth/raw_ttc15:.1f}} % است و پس از هموارسازی علّی پنج‌قابی "
          "{{smooth/smoothed_ttc15:.1f}} % (پنل B؛ دو اجرا در موقعیت‌ها و در منبع سرعت فرق دارند)، و سهم جفت‌های بدون هم‌پوشانی از {{smooth/raw_C:.1f}} % به {{smooth/smoothed_C:.1f}} % کاهش می‌یابد. "
          "بسته به‌جای کاربر انتخاب نمی‌کند: هموارسازی گامی آشکار است که باید گزارش شود."),
    ("fig", "hier", "fig6_hierarchy",
     "(A) جفت‌های نامزد خودروهای موتوری که مسیرهای آیندهٔ آن‌ها هم‌پوشان است، تقسیم‌شده به سطح‌های A و B (ردهٔ TTC و TAdv)؛ برچسب‌ها سهم سطح A و سهم سطح‌های A یا B (مسیرها هم‌پوشان) از همهٔ جفت‌ها و تعداد جفت‌ها را می‌دهند. "
     "(B) اثر هموارسازی روی NGSIM، خیابان Peachtree."),
]
FA["sections"]["impact"] = [
    ("p", "آنچه pyssms برای پژوهشگر تغییر می‌دهد ردیابی‌پذیری است. یک شاخص ایمنی که از ضبط پهپادی حساب می‌شود از یک خواننده، یک انتخاب پیش‌پردازش، یک پالایهٔ جفت، یک داستان حرکتی و یک آستانه می‌گذرد. "
          "در pyssms هر کدام یک تابع آشکار با فرض‌های گفته‌شده است و عددهای این مقاله را اسکریپت‌های مخزن از پرونده‌های نتیجه تولید کرده‌اند، نه دست. مثال‌ها نشان می‌دهند چرا مهم است: "
          "همان جفت‌ها بسته به داستان در {{highd/m/ttc1/crit:.2f}} % یا {{highd/m/ttcd/crit:.0f}} % ردیف‌های highD بحرانی‌اند و شمارش NGSIM با پنجرهٔ هموارسازی جابه‌جا می‌شود."),
    ("p", "بسته سه کاربرد دارد. نخست آموزش و مقایسهٔ روش‌ها: بانک همراهِ {{bank/windows}} پنجرهٔ NGSIM ({{bank/A}} با کمترین TTC، {{bank/B}} با کمترین TAdv، {{bank/C}} با کمترین فاصله؛ {{bank/mb:.1f}} مگابایت) "
          "به دانشجو اجازه می‌دهد هر شاخص را بی‌دانلود مجموعه‌داده اجرا کند. پنجره‌ها با شاخص‌های خود بسته انتخاب شده‌اند، پس مواد آزمون‌اند، نمونهٔ ترافیک نیستند: در {{bank/A}} پنجرهٔ برگزیده با کمترین TTC "
          "کمترین TTC میانه‌ای برابر {{bank/min_ttc_median_A:.3f}} ثانیه دارد و از {{bank/min_ttc_max_A:.2f}} ثانیه فراتر نمی‌رود، با فاصلهٔ مرکزهای "
          "{{bank/dist_min_A:.1f}} تا {{bank/dist_max_A:.1f}} متر، پس بدنه‌های مستطیلی در آستانهٔ تماس‌اند. دوم، "
          "هر جا شاخص‌های ۲۰۱۰ برای شکل‌های محدب دلخواه لازم‌اند، یک تابع آزموده جای شمارش دستی ترکیب‌های گوشه و ضلع را می‌گیرد. سوم، سکویی مشترک که اعتبارسنجی شاخص‌ها در برابر پیامدها روی آن شدنی است: "
          "خواننده، استخراج‌گر پیامد (شروع ترمز) و شمارش رویارویی‌ها در هر سطح آماده‌اند. چنین اعتبارسنجی مهم‌ترین گام بعدی چارچوب دنباله‌روی دانسته شده است [@naseralavi2025]؛ "
          "شروع کنش گریز پیامدی نامزد است [@johnsson2022]. اینجا انجام نشده و مثال‌های بالا را نباید چنین خواند."),
    ("p", "نرم‌افزار جوان است. نسخهٔ {{version}} نخستین انتشار بسته است؛ سابقهٔ کاربردی بیرون از کار خود نویسنده و استنادی ندارد و از مخزن نصب می‌شود، نه از نمایهٔ بسته‌ها. پنجره‌های همراه NGSIM متن مجوز اداره فدرال بزرگراه‌ها "
          "(مجوز اصلاح‌شدهٔ Creative Commons Attribution 2.0) را دارند؛ از مجموعه‌داده‌های LevelX جز شمارش‌ها و مقیاس‌های خطای پیش‌بینی چیزی همراه نیست. "
          "محدودیت‌های مهم برای کاربرد فرض‌های مدل است. K سرعت ثابت و انتقال بدون چرخش را فرض می‌کند، پس خودروی در حال پیچیدن در امتداد سمت فعلی‌اش پیش‌بینی می‌شود؛ ده سنجهٔ دنباله‌روی "
          "یک‌بعدی‌اند و پیشرو و تعقیب‌کننده در امتداد یک خط می‌خواهند؛ پارامترهایشان فرض‌اند؛ و هنوز نسخهٔ دوبعدی این ده سنجه وجود ندارد. مقالهٔ روش‌شناختی همراه دربارهٔ هندسهٔ K در دست تهیه است. "
          "بسته جایگزین سنجه‌های بحرانی‌بودن طراحی‌شده برای رانندگی خودکار نیست [@westhofen2023]؛ شاخص‌های مقاله‌های ۲۰۱۰ و ۲۰۲۵ را همراه آزمون ارائه می‌دهد."),
]
FA["sections"]["conclusions"] = [
    ("p", "pyssms شاخص‌های دوبعدی چارچوب ۲۰۱۰ و ده سنجهٔ دنباله‌روی چارچوب ۲۰۲۵ را در یک بستهٔ پایتونِ آزموده گرد می‌آورد که پرونده‌های مجموعه‌داده‌های رایج را می‌خواند. راستی‌آزمایی بخشی از بسته است: "
          "{{tests/total}} آزمون، هم‌خوانی با روش چاپ‌شده روی {{equiv/compared:,}} رویارویی و شبیه‌سازی داستان‌های حرکتی. مثال‌ها نشان می‌دهند نتیجه‌ها به انتخاب‌هایی بستگی دارند که کد آشکارشان می‌کند: "
          "داستان حرکتی، پارامترهای آن و هموارسازی موقعیت‌ها. همهٔ آنچه گزارش شده توصیفی است. گام‌های بعدی اعتبارسنجی در برابر پیامدهای مشاهده‌شده، نسخهٔ دوبعدی سنجه‌های دنباله‌روی" + ("" if ZENODO_DOI else " و انتشار بایگانی‌شده با شناسهٔ پایدار") + " است."),
]
FA["ack"] = "نویسنده از فراهم‌کنندگان داده‌های highD، inD، rounD، exiD و NGSIM که آن‌ها را برای پژوهش در دسترس گذاشته‌اند سپاسگزار است."
FA["ai"] = ("در تهیهٔ این اثر نویسنده از Claude (Anthropic) به‌عنوان دستیار برای برنامه‌ریزی مطالعه، نوشتن و اجرای کد تحلیل و آزمون، تولید شکل‌ها، غربالگری منابع، و پیش‌نویس و ویرایش متن استفاده کرد. "
            "پس از استفاده از این ابزار، نویسنده مواد تولیدشده (کد، نتایج، منابع و متن) را بازبینی، راستی‌آزمایی و ویرایش کرد و مسئولیت کامل محتوای اثر را می‌پذیرد. "
            "عددهای متن را کد از پرونده‌های نتیجه وارد می‌کند و ارجاع‌ها با یک پایگاه کتابشناختی سنجیده شده‌اند.")
FA["credit"] = ("سید صابر ناصرعلوی: مفهوم‌پردازی، روش‌شناسی، نرم‌افزار، اعتبارسنجی، تحلیل رسمی، پژوهش، نگهداری داده، نگارش پیش‌نویس، نگارش بازبینی و ویرایش، تصویرسازی.")
FA["funding"] = "این پژوهش هیچ کمک مالی ویژه‌ای از نهادهای تأمین مالی در بخش دولتی، تجاری یا غیرانتفاعی دریافت نکرده است."
FA["competing"] = "نویسنده اعلام می‌کند هیچ منافع مالی یا روابط شخصی شناخته‌شده‌ای که بتواند بر کار گزارش‌شده در این مقاله اثر گذاشته باشد ندارد."
FA["data"] = ("کد در " + REPO + " (مجوز BSD 3-Clause) در دسترس است" + (" و نسخهٔ " + VERSION + " در Zenodo بایگانی شده است [@pyssms_zenodo]" if ZENODO_DOI else "") + ". پنجره‌های همراه NGSIM از داده‌های NGSIM اداره فدرال بزرگراه‌ها با مجوز اصلاح‌شدهٔ Creative Commons Attribution 2.0 آمده‌اند "
              "(ذکر FHWA و NGSIM). مجموعه‌داده‌های LevelX از فراهم‌کنندگانشان با درخواست در دسترس‌اند؛ فقط شمارش‌های تجمیعی همراه بسته است. عددهای این مقاله را paper_softwarex/make_numbers.py بازتولید می‌کند.")
FA["exec_version"] = EN["exec_version"]
FA["highlights"] = EN["highlights"]
