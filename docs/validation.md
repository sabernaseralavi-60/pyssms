# Validation

The 2010 paper prints no numeric tables to reproduce, so validation of the indicators means agreement
with an independent implementation of its Appendix A, with hand-derived analytic cases (Eqs. 1-3) and
with a brute-force grid oracle: [equivalence.md](equivalence.md) (generated; do not edit).

## Injury risk curves (Lubbe, Wu and Jeppsson, 2022)

The logistic coefficients of Tables 2-5 were read from the paper (`lit/Lubbe2022_safe_speeds.pdf`).
The check is the paper's own summary: the closing speed at 10% MAIS3+F risk is stated as 29 km/h
(pedestrians, age 46), 44 km/h (cyclists, age 39), 48 km/h (motorcyclists, age 37) and 112 km/h (car
drivers, age 39); the printed coefficients give 28.8, 43.5, 48.8 and 113.0 km/h, which is within the
rounding of three-decimal coefficients (`tests/unit/test_injury_risk.py`, tolerance 1.5 km/h). The
curves are fitted separately for the three levels, so they cross outside the data range (cyclists
above about 90 km/h). A coefficient formula quoted in a collaborator's message (a single logistic
curve with `6.9 - 0.090 v`) is **not** in this paper and was not used. The curves describe crashes
that happened (German in-depth data, front impacts by a passenger car); they are not validated for
conflicts.

## Delta-V (Laureshyn et al., 2017, Table 1)

The 20 rows of Table 1 (the most severe Extended Delta-V8 situations) print the relative speed, the
mass ratio and Delta-V0. `Delta-V0 = heavy / (heavy + light) * relative speed` is reproduced within the
rounding of the printed numbers for **18 of 20 rows**. Two gaps are documented, not tuned away:

| row | printed Delta-V0 | formula | note |
|---|---|---|---|
| 5 (car-car) | 6.9 | 7.05 | -0.15 m/s; outside rounding; cause unknown |
| 9 (car-HGV, ratio 3.85) | 15.2 | 13.65 | a mass ratio of about 7.6 would be needed; possible typo or other mass class |

Extended Delta-V4/V8 cannot be reproduced from the table (the individual speeds and the approach angle
are not printed); only a necessary condition is tested (`|dV_a - dV_0| <= mu * 2 a T2`), which all 20
rows meet. Tests: `tests/unit/test_severity.py`; target values: `validation/data/laureshyn2017_table1.yaml`.
