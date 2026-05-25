"""Target Curve Import und Interpolation fuer AutoREW."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


ISO_THIRD_OCTAVE: list[float] = [
    20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
    200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000,
]


@dataclass
class TargetCurveData:
    """Eine geladene Zielkurve mit Frequenz/Pegel-Paaren."""
    name: str = ""
    path: str = ""
    frequencies: list[float] = field(default_factory=list)
    levels: list[float] = field(default_factory=list)

    @property
    def is_loaded(self) -> bool:
        return len(self.frequencies) > 0 and len(self.levels) > 0

    def interpolate_at(self, freq: float) -> float:
        """Interpoliert den Pegel bei einer Frequenz (log-linear)."""
        if not self.is_loaded:
            return 0.0
        log_freqs = np.log10(np.array(self.frequencies))
        log_f = np.log10(max(freq, 1.0))
        return float(np.interp(log_f, log_freqs, np.array(self.levels)))

    def interpolate_at_many(self, freqs: list[float]) -> list[float]:
        """Interpoliert an mehreren Frequenzen."""
        return [self.interpolate_at(f) for f in freqs]


def load_target_curve(path: Path) -> TargetCurveData:
    """Laedt eine REW .targetcurve oder kompatible Textdatei.

    Format: Zeilen mit 'freq level' (Leerzeichen-getrennt).
    Kommentarzeilen beginnen mit * oder #.
    """
    frequencies: list[float] = []
    levels: list[float] = []

    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*") or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            freq = float(parts[0])
            level = float(parts[1])
            if 10.0 <= freq <= 25000.0:
                frequencies.append(freq)
                levels.append(level)
        except ValueError:
            continue

    if not frequencies:
        raise ValueError(f"Keine gueltigen Kurvendaten in '{path.name}'.")

    pairs = sorted(zip(frequencies, levels))
    freq_sorted, level_sorted = zip(*pairs)
    return TargetCurveData(
        name=path.stem,
        path=str(path),
        frequencies=list(freq_sorted),
        levels=list(level_sorted),
    )


def snap_to_iso_third_octave(freq: float) -> float:
    """Rundet auf die naechste ISO-Terzbandmitte."""
    log_f = np.log10(max(freq, 1.0))
    return float(min(ISO_THIRD_OCTAVE, key=lambda f: abs(np.log10(f) - log_f)))
