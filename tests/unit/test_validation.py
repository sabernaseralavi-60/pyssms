from __future__ import annotations

import pytest

from pyssms import validation as v


def _compute():
    return {"total": lambda ctx: (10.2, None), "ratio": lambda ctx: (1.62, None)}


def test_example_set_has_the_expected_statuses():
    spec = v.load_spec("example")
    rows = v.run(spec, _compute(), None)
    assert [r["status"] for r in rows] == ["reproduced", "not_reproduced"]
    assert all(r["status"] == r["expected"] for r in rows)
    assert v.to_markdown(rows).count("\n") == len(rows) + 2


def test_classify_rules():
    t = v.Target("x", "1", "x", 1.0, 2, 8.60, 0.10, "f", "reproduced")
    assert v.classify(t, 8.6022, 0.1019) == "reproduced"
    assert v.classify(t, 8.6022, 0.2) == "estimate_only"
    assert v.classify(t, 8.7, 0.1) == "not_reproduced"


def test_unknown_set_and_missing_note():
    with pytest.raises(ValueError):
        v.load_spec("nope")
