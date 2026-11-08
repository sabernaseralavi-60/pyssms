# Notes on the ten car-following measures (module `pyssms.ssm1d`)

Source: Naseralavi, Soltanirad, Ranjbar, Jimee, Lucero, Baghersad, Mazaheri (2025), *Future Transportation*
5(3), 86, Table 1 (the ten measures), Table 3 and Eqs. (1)-(9). Each measure is written from the
motion story its code (L/F/T of Table 4) assumes, and **tested against an independent time-stepping
simulation of that story** (`tests/unit/test_ssm1d.py`), not against the printed equations.

## Where the implementation and a printed form differ (to be checked in the source files)

Readings come from the PDF text layer or the page image; the test `test_ssm1d.py` records the
numerical consequences where they are testable.

1. **Table 3, TTC1/2/3 rows.** The text layer prints the last term as `(x_Of + x_Ol - l_f)`: a plus
   between the two positions and a subscript `f` on the length. The position equations above it
   (`x_l = x_Ol + v_l t`, `x_f = x_Of + v_f t`) and Eq. (1) give `(x_Ol - x_Of - l_l)`. Possibly a
   typesetting error; the code uses the gap.
2. **Eq. (9) / DCIA contact time `T`.** As read from the page image:
   `T = (v_f R - v_l R - 2D) / (v_l - a_l R - v_f + a_f R)`. Deriving it from the definition (speeds
   equal when the gap closes; the follower keeps its acceleration during the reaction time)
   gives `T = (2D - (v_f - v_l) R) / ((v_f - v_l) + (a_f - a_l) R)`. They coincide when
   `a_f = a_l`, and differ in the sign of the acceleration term otherwise. The printed numerator of
   DCIA itself is consistent with the derivation. Tested in `test_printed_dcia_contact_time_...`.
3. **Eq. (8) / MPSD.** The printed form `TTC / (R + v_f / (2 a_f))` equals `gap / (v_f R + v_f^2 /
   (2 a_f))` only if "TTC" means `gap / v_f`; with the usual TTC1 (relative speed in the denominator)
   they differ. The code uses the second form (follower's own speed as approach speed).
4. **Eq. (4) / SDI.** The condition is written with the time headway `h` and a `+ l_l` term. The code
   takes the clear gap as input and compares stopping positions; converting `h` to a gap
   depends on the headway definition (front-to-front or front-to-rear), which the paper does not
   fix here.
5. **Eq. (3) / TTCD.** The symbol in the denominator of the first branch is not legible in the text
   layer and the two branches use `a_l` with opposite sign conventions as read. The code uses
   positive deceleration magnitudes and was checked against a simulation including the leader stopping.

## Choices not fixed by the paper

* `gap` is the clear distance between the rear of L and the front of F.
* PSD and MPSD use the follower's own speed as approach speed.
* The polynomial TTCs ignore that a road user cannot reverse (as in the paper's stories).
* No measure here is two-dimensional; the extension along the path coordinate `sigma` of
  `pyssms.stories` is a proposal, not implemented.
