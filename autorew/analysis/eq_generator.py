"""EQ-Filter Generierung — device-constraint-aware."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

import numpy as np

from autorew.models import (
    EqualizerPreset, FilterSetting,
    ProjectConfig, TargetSettings, Zone,
)
from autorew.rew_client import REWClient, REWClientError

if TYPE_CHECKING:
    from autorew.analysis.target_curve import TargetCurveData


def generate_eq_for_zone(client: REWClient, zone: Zone,
                          target: TargetSettings) -> list[FilterSetting]:
    """Generiert EQ-Filter fuer eine Zone via REW Match Target."""
    if not zone.measurement_ids:
        return []

    mid = zone.measurement_ids[-1]

    try:
        client.set_target_level(mid, target.target_level)
        filters = client.match_target(mid)
        return [f for f in filters if f.enabled]
    except REWClientError:
        return []


def generate_eq_constrained(
    client: REWClient,
    zone: Zone,
    target: TargetSettings,
    preset: EqualizerPreset,
) -> tuple[list[FilterSetting], list[dict]]:
    """Generiert PEQ-Filter und wendet Device-Constraints an.

    Returns:
        (constrained_filters, not_transferable_list)
    """
    raw = generate_eq_for_zone(client, zone, target)
    if not raw:
        return [], []
    return _apply_device_constraints(raw, preset)


def generate_all_eq(
    client: REWClient,
    config: ProjectConfig,
    preset: Optional[EqualizerPreset] = None,
) -> dict[str, list[FilterSetting]]:
    """Generiert EQ-Filter fuer alle Zonen, optional mit Device-Constraints."""
    result: dict[str, list[FilterSetting]] = {}
    warnings: dict[str, list[dict]] = {}

    for zone in config.zones:
        if preset:
            filters, not_ok = generate_eq_constrained(
                client, zone, config.target, preset
            )
            if not_ok:
                warnings[zone.name] = not_ok
        else:
            filters = generate_eq_for_zone(client, zone, config.target)

        if filters:
            result[zone.name] = filters

    config.filters = result
    config.filter_warnings = warnings
    return result


def _apply_device_constraints(
    raw_filters: list[FilterSetting],
    preset: EqualizerPreset,
) -> tuple[list[FilterSetting], list[dict]]:
    """Passt Filter an Device-Constraints an.

    Returns:
        (ok_filters, not_transferable_list)
        not_transferable items: {freq, gain, q, reason, adapted}
    """
    snap_iso = "DS 2/4" in preset.name
    round_gain = snap_iso

    ok: list[FilterSetting] = []
    not_ok: list[dict] = []

    for f in raw_filters:
        if len(ok) >= preset.peq_bands:
            not_ok.append({
                "freq": f.frequency, "gain": f.gain, "q": f.q,
                "reason": f"Band-Limit ({preset.peq_bands}) erreicht",
                "adapted": False,
            })
            continue

        clamped = f.model_copy()
        issues: list[str] = []

        if snap_iso:
            from autorew.analysis.target_curve import snap_to_iso_third_octave
            snapped = snap_to_iso_third_octave(f.frequency)
            if abs(snapped - f.frequency) / max(f.frequency, 1.0) > 0.05:
                issues.append(
                    f"F {f.frequency:.0f} -> {snapped:.0f} Hz (ISO-Terz)"
                )
            clamped.frequency = snapped

        orig_gain = clamped.gain
        clamped.gain = max(preset.gain_min, min(preset.gain_max, clamped.gain))
        if abs(clamped.gain - orig_gain) > 0.01:
            issues.append(
                f"Gain {orig_gain:.1f} -> {clamped.gain:.1f} dB "
                f"(+/-{preset.gain_max} dB max)"
            )

        if round_gain:
            clamped.gain = float(round(clamped.gain))

        orig_q = clamped.q
        clamped.q = max(preset.q_min, min(preset.q_max, clamped.q))
        if abs(clamped.q - orig_q) > 0.01:
            issues.append(
                f"Q {orig_q:.2f} -> {clamped.q:.2f} "
                f"(Bereich {preset.q_min}-{preset.q_max})"
            )

        ok.append(clamped)
        if issues:
            not_ok.append({
                "freq": f.frequency, "gain": f.gain, "q": f.q,
                "reason": "; ".join(issues),
                "adapted": True,
            })

    return ok, not_ok


def export_fir_filter(client: REWClient, measurement_id: int,
                       output_path: Path, sample_rate: int = 48000,
                       taps: int = 65536) -> bool:
    """Exportiert FIR-Filter als WAV-Datei."""
    try:
        ir = client.get_filters_impulse_response(
            measurement_id, sample_rate, taps
        )
        if not ir.data:
            return False

        samples = np.array(ir.data, dtype=np.float32)
        peak = np.max(np.abs(samples))
        if peak > 0:
            samples = samples / peak * 0.99

        import wave
        int_samples = (samples * 2147483647).astype(np.int32)
        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(4)
            wf.setframerate(sample_rate)
            wf.writeframes(int_samples.tobytes())

        return True
    except (REWClientError, Exception):
        return False
