"""Time/Phase Alignment Berechnungen."""

from __future__ import annotations

from autorew.models import AlignmentResult, DelayRecommendation, ProjectConfig, Zone
from autorew.rew_client import REWClient, REWClientError

SPEED_OF_SOUND = 343.0  # m/s bei 20°C


def calculate_delays(client: REWClient, config: ProjectConfig) -> list[DelayRecommendation]:
    """Berechnet Delay-Empfehlungen für alle Zonen relativ zur Referenz-Zone."""
    if len(config.zones) < 2:
        return []

    ref_zone = config.zones[0]
    if not ref_zone.measurement_ids:
        return []

    ref_id = ref_zone.measurement_ids[0]
    recommendations = []

    for zone in config.zones[1:]:
        if not zone.measurement_ids:
            continue

        zone_id = zone.measurement_ids[0]
        freq = zone.crossover_freq or 1000.0

        try:
            client.configure_alignment(ref_id, zone_id, frequency=freq)
            result = client.run_alignment()

            delay_ms = float(result.get("delay-b", 0))
            delay_m = delay_ms / 1000.0 * SPEED_OF_SOUND
            gain_diff = float(result.get("gain-b", 0))

            recommendations.append(DelayRecommendation(
                zone_name=zone.name,
                delay_ms=round(delay_ms, 3),
                delay_meters=round(delay_m, 2),
                level_db=round(gain_diff, 1),
            ))
        except REWClientError:
            recommendations.append(DelayRecommendation(
                zone_name=zone.name,
            ))

    return recommendations


def find_optimal_crossover(client: REWClient, sub_id: int, top_id: int,
                            search_range: tuple[float, float] = (60, 200),
                            step_hz: float = 10) -> float:
    """Sucht die optimale Crossover-Frequenz zwischen Sub und Top.

    Kriterium: Minimale SPL-Differenz bei der Crossover-Frequenz.
    """
    best_freq = search_range[0]
    best_diff = float("inf")

    freq = search_range[0]
    while freq <= search_range[1]:
        try:
            client.configure_alignment(sub_id, top_id, frequency=freq)
            resp = client.get_aligned_response()
            if resp.data:
                # Finde den Punkt nächst an freq
                closest = min(resp.data, key=lambda p: abs(p.frequency - freq))
                # Ideal: möglichst flacher Übergang
                diff = abs(closest.magnitude - 0)  # 0 dB = ideal
                if diff < best_diff:
                    best_diff = diff
                    best_freq = freq
        except REWClientError:
            pass
        freq += step_hz

    return best_freq
