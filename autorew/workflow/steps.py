"""Einzelne Workflow-Schritte mit Validierung."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from autorew.models import ProjectConfig
from autorew.rew_client import REWClient, REWClientError


@dataclass
class StepResult:
    success: bool
    message: str = ""
    warnings: list[str] | None = None


def validate_connection(client: REWClient, config: ProjectConfig) -> StepResult:
    """Prüft ob REW erreichbar und Audio konfiguriert ist."""
    if not client.is_connected():
        return StepResult(False, "Keine Verbindung zu REW")

    if not config.audio.input_device:
        return StepResult(False, "Kein Eingangsgeraet gewaehlt")

    warnings = []
    if not config.audio.mic_cal_path:
        warnings.append("Keine Mikrofon-Kalibrierung geladen - Messergebnisse koennten ungenau sein")

    config.is_pro_license = client.is_pro_license()
    if not config.is_pro_license:
        warnings.append("Standard-Lizenz erkannt - Sweeps muessen manuell in REW gestartet werden")

    return StepResult(True, "Verbindung OK", warnings)


def validate_zones(config: ProjectConfig) -> StepResult:
    if not config.zones:
        return StepResult(False, "Keine Zonen definiert")

    channels = [z.output_channel for z in config.zones]
    if len(channels) != len(set(channels)):
        return StepResult(False, "Doppelte Ausgangskanaele erkannt")

    warnings = []
    subs = [z for z in config.zones if z.is_sub]
    if subs and not any(z.crossover_freq for z in subs):
        warnings.append("Subwoofer ohne Crossover-Frequenz - Alignment koennte ungenau sein")

    return StepResult(True, f"{len(config.zones)} Zonen konfiguriert", warnings)


def validate_measurements(client: REWClient, config: ProjectConfig) -> StepResult:
    zones_with_data = [z for z in config.zones if z.measurement_ids]
    if not zones_with_data:
        return StepResult(False, "Keine Messungen vorhanden")

    warnings = []
    for zone in config.zones:
        if not zone.measurement_ids:
            warnings.append(f"Zone '{zone.name}' hat keine Messungen")
        elif len(zone.measurement_ids) < zone.positions:
            warnings.append(
                f"Zone '{zone.name}': {len(zone.measurement_ids)}/{zone.positions} Positionen gemessen"
            )

    total = sum(len(z.measurement_ids) for z in config.zones)
    return StepResult(True, f"{total} Messungen vorhanden", warnings)
