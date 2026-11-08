# Pitfalls found while building pyssms

* Implementing Appendix A of Laureshyn et al. (2010) from the journal's "article in press" PDF
  gives a wrong sign: Eqs. (8) and (9) lack the leading minus sign there and return minus the
  crossing time. The author's 2010 thesis (Appendix, printed p. 138) prints the minus sign, so the
  equations themselves are correct. Eq. (10) has `x2`, `y2` where `x_ln2`, `y_ln2` are meant (thesis
  and preprint alike), and a literal implementation needs a tolerance for sides parallel to an axis.
  Evidence and counts: [equivalence.md](equivalence.md); derivation: [methods.md](methods.md).
* The appendix does not cover parallel paths, standing road users or bodies that already overlap.
* Any comparison of two implementations must use the same prediction horizon (an oracle with a
  shorter horizon produced a false 2.6 s disagreement during development).
