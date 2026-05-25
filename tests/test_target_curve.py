"""Tests fuer target_curve.py."""

import tempfile
from pathlib import Path

import pytest

from autorew.analysis.target_curve import (
    TargetCurveData,
    load_target_curve,
    snap_to_iso_third_octave,
)


def _tmp_curve(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".targetcurve", delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return Path(f.name)


def test_load_simple():
    p = _tmp_curve("20 -10.0\n1000 0.0\n20000 -3.0\n")
    c = load_target_curve(p)
    assert c.is_loaded
    assert len(c.frequencies) == 3
    assert c.levels[0] == pytest.approx(-10.0)


def test_load_with_comments():
    p = _tmp_curve("* Target Curve\n# comment\n20 -5.0\n1000 2.0\n")
    c = load_target_curve(p)
    assert len(c.frequencies) == 2


def test_interpolate():
    c = TargetCurveData(frequencies=[20.0, 20000.0], levels=[-10.0, 0.0])
    assert c.interpolate_at(20.0) == pytest.approx(-10.0, abs=0.1)
    assert c.interpolate_at(20000.0) == pytest.approx(0.0, abs=0.1)


def test_snap_iso():
    assert snap_to_iso_third_octave(108.0) == pytest.approx(100.0)
    assert snap_to_iso_third_octave(494.0) == pytest.approx(500.0)
    assert snap_to_iso_third_octave(4219.0) == pytest.approx(4000.0)


def test_load_empty_raises():
    p = _tmp_curve("* no data\n# only comments\n")
    with pytest.raises(ValueError):
        load_target_curve(p)
