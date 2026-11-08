# Search log (2026-11-08)

| # | Tool | Query or action | Result |
|---|---|---|---|
| 1 | PyPI simple index (JSON, all project names, 934,630) | regex on names: ssm, surrogate, ttc, conflict, traffic-safety, criticality, crash, collision, pet-, highd, ngsim, levelx, ssam, vissim | 1,040 name hits, almost all unrelated (AWS SSM, cssmin, crash reporters); relevant: trafficintelligence, commonroad-crime (and commonroad-reach) |
| 2 | PyPI JSON metadata | summaries of 17 plausible names (safety-metrics-lib, crashmetrics, ssam, pyssam, ttc, ...) | none is a road-safety indicator package (construction safety, crash CAE, bioinformatics, utilities) |
| 3 | GitHub repository search (language Python) | "surrogate safety measures" | EmergencyIndex, SSMsOnPlane, LibSSM (plus unrelated student projects) |
| 4 | GitHub | "time to collision trajectory", "post encroachment time", "two-dimensional time to collision", "traffic conflict analysis python", "SSAM surrogate safety assessment", "criticality metrics automated driving", "highD dataset safety metrics" | Two-Dimensional-Time-To-Collision; TrafficIntersectionSafetyMetrics (video, TTC and PET at intersections); others empty or unrelated |
| 5 | Source reading | SSMsOnPlane README and `two_dimensional_ssms.py` (function TAdv) | TAdv from corner-to-corner intersections of velocity lines (16 corner pairs), parallel threshold 3 degrees, no T2 or TG, no hierarchy, no readers |
| 6 | Source reading | LibSSM README, EmergencyIndex README, commonroad-crime and trafficintelligence PyPI descriptions | LibSSM: list of measures, licence placeholder; EI: a new measure (InDepth), CSV script; CriMe: criticality-measure toolbox for automated-vehicle scenarios; TI: trajectory tools |
| 7 | Crossref | bibliographic search and DOI lookup for the CriMe, Traffic Intelligence, EI and ACT papers | four DOIs resolved; title, authors, year and venue match |
| 8 | OpenAlex | is_retracted for the four DOIs | false for all four (Crossref: no update-to or relation) |

Excluded near-misses: LibSSM (2023, single day of commits, licence placeholder, no usable code); safety-metrics-lib (construction-site safety);
TrafficIntersectionSafetyMetrics (video-based, intersections only).
