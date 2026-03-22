"""Vordefinierte Workflow-Presets für verschiedene PA-Szenarien."""

from __future__ import annotations

from autorew.models import SweepConfig, TargetSettings, Zone, ZoneType


class WorkflowPreset:
    """Ein vordefinierter Workflow mit Zonen, Sweep-Config und Target."""

    def __init__(self, name: str, description: str, zones: list[Zone],
                 sweep: SweepConfig, target: TargetSettings):
        self.name = name
        self.description = description
        self.zones = zones
        self.sweep = sweep
        self.target = target


PRESETS = {
    "speech": WorkflowPreset(
        name="Sprache (Konferenz/Theater)",
        description="Optimiert fuer Sprachverstaendlichkeit. Fokus auf 200-8000 Hz.",
        zones=[
            Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1),
            Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2),
        ],
        sweep=SweepConfig(start_freq=50, end_freq=16000, level=-15),
        target=TargetSettings(target_level=80, hf_fall=-3.0, hf_cutoff=8000),
    ),
    "music_stereo": WorkflowPreset(
        name="Musik (Stereo + Sub)",
        description="Full-Range Musik-PA mit Subwoofer.",
        zones=[
            Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1),
            Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2),
            Zone(name="Sub", zone_type=ZoneType.SUB, output_channel=3,
                 is_sub=True, crossover_freq=120),
        ],
        sweep=SweepConfig(start_freq=20, end_freq=20000, level=-12),
        target=TargetSettings(target_level=85),
    ),
    "music_multizone": WorkflowPreset(
        name="Musik (Multi-Zone)",
        description="Grosses PA-Setup mit Delays und Fills.",
        zones=[
            Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1, positions=3),
            Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2, positions=3),
            Zone(name="Sub", zone_type=ZoneType.SUB, output_channel=3,
                 is_sub=True, crossover_freq=100, positions=2),
            Zone(name="Delay L", zone_type=ZoneType.DELAY_LEFT, output_channel=4, positions=2),
            Zone(name="Delay R", zone_type=ZoneType.DELAY_RIGHT, output_channel=5, positions=2),
            Zone(name="Fill L", zone_type=ZoneType.FILL_LEFT, output_channel=6),
            Zone(name="Fill R", zone_type=ZoneType.FILL_RIGHT, output_channel=7),
        ],
        sweep=SweepConfig(start_freq=20, end_freq=20000, level=-12, repetitions=2),
        target=TargetSettings(target_level=90),
    ),
    "monitor": WorkflowPreset(
        name="Monitor/Wedge",
        description="Buehnen-Monitor Einmessung.",
        zones=[
            Zone(name="Monitor 1", zone_type=ZoneType.MONITOR, output_channel=1),
            Zone(name="Monitor 2", zone_type=ZoneType.MONITOR, output_channel=2),
        ],
        sweep=SweepConfig(start_freq=80, end_freq=16000, level=-15),
        target=TargetSettings(target_level=85, hf_fall=-2.0, hf_cutoff=12000),
    ),
}
