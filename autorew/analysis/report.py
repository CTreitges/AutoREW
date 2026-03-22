"""PDF Report Generierung mit Frequenzgang-Grafiken."""

from __future__ import annotations

import io
import tempfile
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF

from autorew.models import ProjectConfig
from autorew.rew_client import REWClient, REWClientError


def _plot_zone_response(client: REWClient, zone_name: str,
                         measurement_ids: list[int]) -> bytes | None:
    """Erstellt einen Frequenzgang-Plot und gibt PNG-Bytes zurück."""
    fig, ax = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor("#f8f8f8")
    ax.set_facecolor("white")
    ax.set_xlabel("Frequenz (Hz)")
    ax.set_ylabel("SPL (dB)")
    ax.set_title(zone_name, fontweight="bold")
    ax.set_xscale("log")
    ax.set_xlim(20, 20000)
    ax.grid(True, alpha=0.3)

    has_data = False
    colors = ["#1e88e5", "#43a047", "#fb8c00", "#e53935"]

    for i, mid in enumerate(measurement_ids):
        try:
            resp = client.get_frequency_response(mid, smoothing="1/6")
            freqs = [p.frequency for p in resp.data]
            mags = [p.magnitude for p in resp.data]
            if freqs:
                ax.plot(freqs, mags, color=colors[i % len(colors)],
                        linewidth=1.2, label=f"Messung {mid}")
                has_data = True
        except REWClientError:
            pass

    if not has_data:
        plt.close(fig)
        return None

    ax.legend(fontsize=8)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_report(client: REWClient, config: ProjectConfig, output_path: Path) -> None:
    """Generiert einen vollständigen PDF-Report."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Titelseite
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 20, "AutoREW", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 16)
    pdf.cell(0, 12, "PA Einmessungs-Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Projekt: {config.name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Datum: {datetime.now():%d.%m.%Y %H:%M}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Zonen: {len(config.zones)}", new_x="LMARGIN", new_y="NEXT")

    total_measurements = sum(len(z.measurement_ids) for z in config.zones)
    pdf.cell(0, 8, f"Messungen: {total_measurements}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Zonen-Übersicht
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Zonen-Konfiguration", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    for zone in config.zones:
        xo = f" | Crossover: {zone.crossover_freq:.0f} Hz" if zone.crossover_freq else ""
        pdf.cell(0, 7,
                 f"  {zone.name} ({zone.zone_type.value}) - "
                 f"Kanal {zone.output_channel}, {zone.positions} Position(en){xo}",
                 new_x="LMARGIN", new_y="NEXT")

    # Frequenzgänge pro Zone
    for zone in config.zones:
        if not zone.measurement_ids:
            continue

        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Zone: {zone.name}", new_x="LMARGIN", new_y="NEXT")

        png_data = _plot_zone_response(client, zone.name, zone.measurement_ids)
        if png_data:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png_data)
                tmp_path = tmp.name
            pdf.image(tmp_path, x=10, w=190)
            Path(tmp_path).unlink(missing_ok=True)

        # EQ-Filter für diese Zone
        filters = config.filters.get(zone.name, [])
        if filters:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, "EQ-Filter:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Courier", "", 9)
            for i, f in enumerate(filters, 1):
                if f.enabled:
                    pdf.cell(0, 5,
                             f"  #{i:2d} {f.filter_type.value}  "
                             f"{f.frequency:8.1f} Hz  {f.gain:+6.1f} dB  Q={f.q:.2f}",
                             new_x="LMARGIN", new_y="NEXT")

    # Delay & Level
    if config.delays:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Delay & Level Empfehlungen", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 8, "Zone", border=1)
        pdf.cell(35, 8, "Delay (ms)", border=1, align="R")
        pdf.cell(30, 8, "Delay (m)", border=1, align="R")
        pdf.cell(30, 8, "Level (dB)", border=1, align="R")
        pdf.ln()

        pdf.set_font("Helvetica", "", 10)
        for d in config.delays:
            pdf.cell(60, 7, d.zone_name, border=1)
            pdf.cell(35, 7, f"{d.delay_ms:.3f}", border=1, align="R")
            pdf.cell(30, 7, f"{d.delay_meters:.2f}", border=1, align="R")
            pdf.cell(30, 7, f"{d.level_db:+.1f}", border=1, align="R")
            pdf.ln()

    pdf.output(str(output_path))
