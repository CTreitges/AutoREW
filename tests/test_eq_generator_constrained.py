"""Tests fuer device-constraint-aware EQ-Generierung."""

import pytest

from autorew.analysis.eq_generator import _apply_device_constraints
from autorew.models import EQUALIZER_PRESETS, FilterSetting


def _f(freq: float, gain: float, q: float) -> FilterSetting:
    return FilterSetting(frequency=freq, gain=gain, q=q)


def test_dsp306_passthrough():
    preset = EQUALIZER_PRESETS["t.racks DSP 306"]
    ok, nok = _apply_device_constraints([_f(1000, -3.0, 5.0)], preset)
    assert len(ok) == 1
    assert len(nok) == 0
    assert ok[0].gain == pytest.approx(-3.0)


def test_ds24_q_clamp():
    preset = EQUALIZER_PRESETS["t.racks DS 2/4"]
    ok, nok = _apply_device_constraints([_f(1000, -5.0, 27.0)], preset)
    assert ok[0].q == pytest.approx(10.0)
    assert len(nok) == 1
    assert nok[0]["adapted"] is True


def test_ds24_freq_snap():
    preset = EQUALIZER_PRESETS["t.racks DS 2/4"]
    ok, _ = _apply_device_constraints([_f(108, -3.0, 5.0)], preset)
    assert ok[0].frequency == pytest.approx(100.0)


def test_band_limit():
    preset = EQUALIZER_PRESETS["t.racks DS 2/4"]
    filters = [_f(f, -2.0, 2.0) for f in [500, 1000, 2000, 4000, 8000, 12500, 16000]]
    ok, nok = _apply_device_constraints(filters, preset)
    assert len(ok) == 5
    assert len(nok) == 2
    assert "Band-Limit" in nok[0]["reason"]


def test_generic_wide_q():
    preset = EQUALIZER_PRESETS["Generic"]
    ok, nok = _apply_device_constraints([_f(500, -10, 150)], preset)
    assert ok[0].q == pytest.approx(150.0)
    assert len(nok) == 0
