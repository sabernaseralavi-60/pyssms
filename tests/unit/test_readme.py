"""The README example must keep running."""

import numpy as np
import pytest

from pyssms import indicators_rect


def test_readme_example():
    k = indicators_rect(-20, 0, 0, 10, 0, 4.5, 1.8, 0, -30, np.pi / 2, 0, 10, 4.5, 1.8)
    assert list(k.state) == ["B"]
    assert np.isnan(k.ttc[0])
    assert k.tadv[0] == pytest.approx(0.37)
    assert k.t2[0] == pytest.approx(2.685)
    assert k.tg[0] == pytest.approx(2.685)
