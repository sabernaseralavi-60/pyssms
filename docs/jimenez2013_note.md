# Jimenez, Naranjo and Garcia (2013): what it does and how it relates to the polygon

Read 2026-11-03 from the PDF placed in `lit/` (sections 2 to 5); Tables 1 and 2 (the configurations A to J)
read from the page images on 2026-11-07.

* **Method.** Two rectangles moving at constant velocity along straight paths. The paper criticises
  the point method with a tolerance, `|TX1 - TX2| < delta` (its Eq. 3), and replaces it by a decision
  over **10 corner-side configurations** (A to F for an angle between the motions below 90 degrees,
  G to J above 90 degrees) out of the 32 corner-side combinations, using arrival and departure times
  of the corners at the path of the other vehicle (TA, TC, TD) and two lines in a time-distance plane
  (its Eqs. 4 and 5). The output is TTC when a collision occurs; the "no accident" label otherwise.
* **Assumptions it states.** A corner always strikes first ("the collision is perfectly parallel or
  perfectly perpendicular" is the exception it sets aside); non-uniform motion and curved paths are
  said to be treatable with numerical methods, not worked out.
* **Relation to the polygon.** Same family of question as the 2010 Appendix A (which the polygon
  reproduces); the polygon returns TTC, TAdv, T2, TG for any convex bodies and any velocity direction
  in one description, and a value for crossing courses where the paper reports "no accident". The ten
  configurations are the classes of **(struck vehicle, struck part)**: for an angle between the motions
  below 90 degrees A (corner of vehicle 2 hits the side of 1), D (corner of 1 hits the side of 2), B
  (front of 2 hits a corner of 1), E (front of 1 hits a corner of 2), C (corner of 2 hits the rear of
  1), F (corner of 1 hits the rear of 2); above 90 degrees G (corner of 2 hits the side of 1), J
  (corner of 1 hits the side of 2), H (corner of 1 hits the front of 2), I (corner of 2 hits the front
  of 1). **Checked 2026-11-07** (`tests/unit/test_contact.py::test_jimenez_2013_ten_configurations_...`):
  in 150,000 random collision courses of two 4.5 x 1.8 m vehicles moving forward, `contact_faces` gives
  exactly these classes and no others: six below 90 degrees (side, front, rear of either vehicle) and
  four above 90 degrees (side and front of either vehicle, never a rear), and no tie (face-face or
  corner-corner) occurred. This agrees with the paper's table as a set of classes; it does not check
  its time conditions, nor the paper's statements about which vehicle "hits" (in the polygon the
  struck face and the striking corner are symmetric in time).
* **State B (crossing courses).** The paper reports "no accident" there. `contact.avoided_contact_faces`
  names the faces and corners that would touch first if the road user ahead were delayed by TAdv (the
  closest point of `K` to the diagonal); tested against a time-stepped search (no overlap at a delay of
  TAdv - 3 ms, overlap at TAdv + 3 ms). In random crossing courses it is a corner-corner contact (two
  active edges) except where the prediction horizon or the clock origin limits the closest point
  (`horizon_active`, about 6 percent in the sample used).
* **Worked example (section 5).** Decoded with Fig. 4 and section 3.3.1 (roles exchanged: the 19 m/s
  vehicle is the paper's vehicle 2): TA21 = 9/19 s (front corner, 10 m - 1 m), TD11 = 9/20 s, and
  TC11 = (9 + 5)/v = 14/20 s in scenario 1, as printed. In scenario 2 the same rule gives 14/25 s = 0.56 s,
  not the printed 11/25 s = 0.44 s; with 14/25 the condition TC11 >= TA21 >= TD11 holds and there **is** a
  collision at 9/19 s, which is what the polygon and a time-stepped search give. The printed "no
  collision" rests on a slip in the numerator (11 for 14). The relayed statement "TAdv = 9/19 - 11/25 =
  0.0337 s" therefore does not describe those bodies (TAdv = 0). Test: `tests/unit/test_jimenez2013.py`.
  (An earlier version of this note read 11/25 as the front corner clearing the 2 m wide path; that
  explanation was ours and is not supported by the paper's pattern 9 + 5.)
