"""EQ-Filter Generierung und FIR-Export."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from autorew.models import FilterSetting, ProjectConfig, TargetSettings, Zone
from autorew.rew_client import REWClient, REWClientError


def generate_eq_for_zone(client: REWClient, zone: Zone,
                          target: TargetSettings) -> list[FilterSetting]:
    """Generiert EQ-Filter für eine Zone via REW Match Target."""
    if not zone.measurement_ids:
        return []

    mid = zone.measurement_ids[-1]

    try:
        client.set_target_level(mid, target.target_level)
        filters = client.match_target(mid)
        return [f for f in filters if f.enabled]
    except REWClientError:
        return []


def generate_all_eq(client: REWClient, config: ProjectConfig) -> dict[str, list[FilterSetting]]:
    """Generiert EQ-Filter für alle Zonen."""
    result = {}
    for zone in config.zones:
        filters = generate_eq_for_zone(client, zone, config.target)
        if filters:
            result[zone.name] = filters
    config.filters = result
    return result


def export_fir_filter(client: REWClient, measurement_id: int,
                       output_path: Path, sample_rate: int = 48000,
                       taps: int = 65536) -> bool:
    """Exportiert FIR-Filter als WAV-Datei."""
    try:
        ir = client.get_filters_impulse_response(measurement_id, sample_rate, taps)
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
