# Margin beta: what is decided and what is not (2026-11-01)

Status: **not implemented.** The 2010 paper only says that a near miss "has less of a safety margin
to endure an additional unlucky factor" (Section 2). Turning that sentence into a number needs a
disturbance model, which is a scientific decision. Facts that constrain it, read from the papers:

* The 2017 paper (Section 5.2) lists what a disturbance model must not ignore: braking force
  depends on friction and vehicle; cyclists swerve and pedestrians can jump back; four masses only;
  the collision is a completely inelastic point-mass collision.
* Prior art on disturbance-based margins exists (Astarita & Giofre 2019; Kuang et al. 2015; Xie et
  al. 2019 for TTCD in the 2025 paper), so novelty must come from the formulation, not the idea.

Candidate definitions, from simplest to richest (none validated):

1. **Time margin** = TAdv (already implemented): the smallest delay of one road user that creates a
   collision course. No new parameter.
2. **Lateral margin** (needed for state C): the smallest sideways shift of one path that makes the
   bodies overlap at the same time; exact on the overlap polygon R for straight paths.
3. **Combined margin**: smallest norm of (delay, lateral shift) after scaling each by a standard
   deviation estimated from undisturbed passages at the same site (a Hasofer-Lind style distance).
   Scales are data, not constants; the choice of norm and of the scales is the open decision.

## Update 2026-11-01: option 3 as a geometric object (implemented, scales still open)

`pyssms.disturbance` computes the disturbance set D in the plane of the clock shift delta (s) and a
sideways shift eps (m) of one path: the pairs for which the disturbed straight-line encounter
overlaps within the horizon. D is a convex polygon (projection of a convex polytope; exact
Fourier-Motzkin elimination). Then:

* the undisturbed encounter is the origin; it lies in D exactly on a collision course (state A);
* Time Advantage (option 1) and the lateral margin (option 2) are the shortest distances to D along
  the two axes (checked against `pyssms.timetime` and `pyssms.margins`);
* the signed distance `beta` from the origin to D in the scaled coordinates
  `(delta/sigma_delta, eps/sigma_eps)` is continuous through A, B and C; `Phi(-beta)` is the
  Hasofer-Lind approximation of a collision-course probability (exact for a half-plane D).

What this does not settle: (a) `sigma_delta` and `sigma_eps` (data, not constants; the error of a
constant-velocity prediction grows with the horizon), (b) whether a shift of the clock is the right
disturbance for a braking road user (braking is not a time shift), (c) at a perpendicular crossing
the lateral margin of the second road user equals `|v1| * TAdv`, so it adds no information there;
it matters for diverging or parallel paths, (d) when a passage is over (D empty) `beta` is
undefined. Prior art for the idea of a margin: Hyden (1987) hypothesises a safety margin used by
road users when judging whether they are on a collision course (as cited in the 2010 thesis,
Section 4.1); Svensson (1998) discusses enlarging the road users' footprints so that near misses register as collision courses (read in her thesis, Section 4 and the closing chapter: discussed, not applied)
(same source; neither read in the original); Astarita & Giofre (2019) and Kuang et al. (2015) are in
`literature_step0.md`. The contribution to claim is the formulation and its checks, not the idea.

Question for the 2010 paper's authors: which of these matches the intuition in Section 2?
