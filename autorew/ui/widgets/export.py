"""Export Widget - PEQ, FIR, Delay, PDF Report."""

from __future__ import annotations

import csv
import json
import os
import struct
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from autorew.models import FilterSetting, ProjectConfig
from autorew.rew_client import REWClient, REWClientError
from autorew.ui.styles import COLORS as C, btn_success


class ExportWidget(QWidget):
    """Step 5: Export (PEQ/FIR/Delay/Report)."""

    def __init__(self, client: REWClient, config: ProjectConfig, parent=None):
        super().__init__(parent)
        self.client = client
        self.config = config
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        header = QLabel("Export")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(header)

        desc = QLabel("Exportiere EQ-Filter, FIR-Korrekturen, Delay-Einstellungen und einen vollstaendigen Report.")
        desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Output Directory ---
        dir_group = QGroupBox("Ausgabeverzeichnis")
        dir_layout = QHBoxLayout(dir_group)
        dir_layout.setSpacing(10)
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("Waehle ein Verzeichnis...")
        self._output_dir.setText(str(Path.home() / "Desktop" / "AutoREW_Export"))
        self._btn_browse = QPushButton("Durchsuchen...")
        self._btn_browse.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self._output_dir, 1)
        dir_layout.addWidget(self._btn_browse)
        layout.addWidget(dir_group)

        # --- PEQ Export ---
        peq_group = QGroupBox("PEQ-Filter Export")
        peq_layout = QVBoxLayout(peq_group)
        peq_layout.setSpacing(12)

        peq_desc = QLabel("Exportiert parametrische EQ-Filter als Text-Datei, kompatibel mit gaengigen DSP-Controllern.")
        peq_desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 12px;")
        peq_desc.setWordWrap(True)
        peq_layout.addWidget(peq_desc)

        self._peq_format = QComboBox()
        self._peq_format.addItems([
            "Generic (CSV)",
            "t.racks DSP 306",
            "miniDSP",
            "Behringer DEQ2496",
            "dbx DriveRack",
            "REW Filter Settings",
        ])
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Format:", self._peq_format)
        peq_layout.addLayout(form)

        self._btn_export_peq = QPushButton("PEQ exportieren")
        self._btn_export_peq.clicked.connect(self._export_peq)
        peq_layout.addWidget(self._btn_export_peq)

        layout.addWidget(peq_group)

        # --- FIR Export ---
        fir_group = QGroupBox("FIR-Filter Export")
        fir_layout = QVBoxLayout(fir_group)
        fir_layout.setSpacing(12)

        fir_desc = QLabel("Generiert FIR-Korrekturfilter als WAV-Datei fuer Convolution-Engines (z.B. Brutefir, HQPlayer).")
        fir_desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 12px;")
        fir_desc.setWordWrap(True)
        fir_layout.addWidget(fir_desc)

        fir_form = QFormLayout()
        fir_form.setSpacing(10)
        self._fir_taps = QComboBox()
        self._fir_taps.addItems(["32768", "65536", "131072"])
        self._fir_taps.setCurrentIndex(1)
        fir_form.addRow("Filter-Laenge (Taps):", self._fir_taps)

        self._fir_samplerate = QComboBox()
        self._fir_samplerate.addItems(["44100", "48000", "96000"])
        self._fir_samplerate.setCurrentIndex(1)
        fir_form.addRow("Samplerate:", self._fir_samplerate)

        fir_layout.addLayout(fir_form)

        self._btn_export_fir = QPushButton("FIR exportieren")
        self._btn_export_fir.clicked.connect(self._export_fir)
        fir_layout.addWidget(self._btn_export_fir)

        layout.addWidget(fir_group)

        # --- Delay & Level ---
        delay_group = QGroupBox("Delay & Level Empfehlungen")
        delay_layout = QVBoxLayout(delay_group)
        delay_layout.setSpacing(12)

        self._delay_preview = QTextEdit()
        self._delay_preview.setReadOnly(True)
        self._delay_preview.setMaximumHeight(150)
        delay_layout.addWidget(self._delay_preview)

        self._btn_export_delay = QPushButton("Delay/Level als CSV exportieren")
        self._btn_export_delay.clicked.connect(self._export_delay)
        delay_layout.addWidget(self._btn_export_delay)

        layout.addWidget(delay_group)

        # --- PDF Report ---
        report_group = QGroupBox("PDF Report")
        report_layout = QVBoxLayout(report_group)
        report_layout.setSpacing(12)

        report_desc = QLabel("Erstellt einen PDF-Report mit allen Messungen, Frequenzgaengen, EQ-Einstellungen und Empfehlungen.")
        report_desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 12px;")
        report_desc.setWordWrap(True)
        report_layout.addWidget(report_desc)

        self._btn_export_report = QPushButton("PDF Report generieren")
        self._btn_export_report.setStyleSheet(btn_success())
        self._btn_export_report.setFixedHeight(42)
        self._btn_export_report.clicked.connect(self._export_report)
        report_layout.addWidget(self._btn_export_report)

        layout.addWidget(report_group)

        # --- Status ---
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {C['success']}; font-weight: bold; font-size: 13px;")
        layout.addWidget(self._status)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def on_activated(self):
        self._update_delay_preview()

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Ausgabeverzeichnis waehlen")
        if path:
            self._output_dir.setText(path)

    def _ensure_output_dir(self) -> Path:
        path = Path(self._output_dir.text())
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _update_delay_preview(self):
        lines = []
        for d in self.config.delays:
            lines.append(
                f"{d.zone_name:20s}  Delay: {d.delay_ms:8.3f} ms  "
                f"({d.delay_meters:.2f} m)  Level: {d.level_db:+.1f} dB"
            )
        self._delay_preview.setText("\n".join(lines) if lines else "Keine Delay-Daten vorhanden.")

    def _export_peq(self):
        out_dir = self._ensure_output_dir()
        fmt = self._peq_format.currentText()

        for zone_name, filters in self.config.filters.items():
            safe_name = zone_name.replace(" ", "_").replace("/", "-")
            enabled_filters = [f for f in filters if f.enabled]

            if fmt == "Generic (CSV)":
                self._write_peq_csv(out_dir / f"PEQ_{safe_name}.csv", zone_name, enabled_filters)
            elif fmt == "REW Filter Settings":
                self._write_peq_rew(out_dir / f"PEQ_{safe_name}.txt", zone_name, enabled_filters)
            else:
                self._write_peq_generic(out_dir / f"PEQ_{safe_name}.txt", zone_name, enabled_filters, fmt)

        self._status.setText(f"PEQ exportiert nach: {out_dir}")

    def _write_peq_csv(self, path: Path, zone: str, filters: list[FilterSetting]):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Zone", "Filter", "Type", "Frequency_Hz", "Gain_dB", "Q"])
            for i, flt in enumerate(filters, 1):
                writer.writerow([zone, i, flt.filter_type.value, f"{flt.frequency:.1f}",
                                 f"{flt.gain:.1f}", f"{flt.q:.2f}"])

    def _write_peq_rew(self, path: Path, zone: str, filters: list[FilterSetting]):
        with open(path, "w") as f:
            f.write(f"# REW Filter Settings - {zone}\n")
            f.write(f"# Generated by AutoREW {datetime.now():%Y-%m-%d %H:%M}\n\n")
            for i, flt in enumerate(filters, 1):
                f.write(f"Filter {i:2d}: ON  {flt.filter_type.value}  "
                        f"Fc {flt.frequency:8.1f} Hz  "
                        f"Gain {flt.gain:+6.1f} dB  "
                        f"Q {flt.q:.4f}\n")

    def _write_peq_generic(self, path: Path, zone: str, filters: list[FilterSetting], fmt: str):
        with open(path, "w") as f:
            f.write(f"# {fmt} - {zone}\n")
            f.write(f"# Generated by AutoREW {datetime.now():%Y-%m-%d %H:%M}\n\n")
            for i, flt in enumerate(filters, 1):
                f.write(f"Band {i}: {flt.filter_type.value}  "
                        f"{flt.frequency:.1f} Hz  "
                        f"{flt.gain:+.1f} dB  "
                        f"Q={flt.q:.2f}\n")

    def _export_fir(self):
        out_dir = self._ensure_output_dir()
        taps = int(self._fir_taps.currentText())
        sr = int(self._fir_samplerate.currentText())

        for zone in self.config.zones:
            if not zone.measurement_ids:
                continue
            mid = zone.measurement_ids[-1]
            safe_name = zone.name.replace(" ", "_").replace("/", "-")

            try:
                ir = self.client.get_filters_impulse_response(mid, sample_rate=sr, length=taps)
                if ir.data:
                    self._write_wav(out_dir / f"FIR_{safe_name}.wav", ir.data, sr)
            except REWClientError:
                data = [0.0] * taps
                data[0] = 1.0
                self._write_wav(out_dir / f"FIR_{safe_name}_dirac.wav", data, sr)

        self._status.setText(f"FIR exportiert nach: {out_dir}")

    def _write_wav(self, path: Path, data: list[float], sample_rate: int):
        samples = np.array(data, dtype=np.float32)
        peak = np.max(np.abs(samples))
        if peak > 0:
            samples = samples / peak * 0.99

        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(4)
            wf.setframerate(sample_rate)
            int_samples = (samples * 2147483647).astype(np.int32)
            wf.writeframes(int_samples.tobytes())

    def _export_delay(self):
        out_dir = self._ensure_output_dir()
        path = out_dir / "Delay_Level.csv"

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Zone", "Delay_ms", "Delay_m", "Level_dB"])
            for d in self.config.delays:
                writer.writerow([d.zone_name, f"{d.delay_ms:.3f}",
                                 f"{d.delay_meters:.2f}", f"{d.level_db:+.1f}"])

        self._status.setText(f"Delay/Level exportiert nach: {path}")

    def _export_report(self):
        out_dir = self._ensure_output_dir()
        path = out_dir / f"AutoREW_Report_{datetime.now():%Y%m%d_%H%M}.pdf"

        try:
            from autorew.analysis.report import generate_report
            generate_report(self.client, self.config, path)
            self._status.setText(f"Report erstellt: {path}")
        except ImportError:
            self._export_report_simple(path)
        except Exception as e:
            self._status.setText(f"Report-Fehler: {e}")

    def _export_report_simple(self, path: Path):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 15, "AutoREW - PA Einmessungs-Report", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Erstellt: {datetime.now():%Y-%m-%d %H:%M}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Projekt: {self.config.name}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Zonen", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for zone in self.config.zones:
            xo = f", Crossover: {zone.crossover_freq} Hz" if zone.crossover_freq else ""
            pdf.cell(0, 7, f"  {zone.name} - Kanal {zone.output_channel}{xo}",
                     new_x="LMARGIN", new_y="NEXT")

        if self.config.delays:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Delay & Level Empfehlungen", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for d in self.config.delays:
                pdf.cell(0, 7,
                         f"  {d.zone_name}: {d.delay_ms:.3f} ms ({d.delay_meters:.2f} m), "
                         f"Level: {d.level_db:+.1f} dB",
                         new_x="LMARGIN", new_y="NEXT")

        if self.config.filters:
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "EQ-Filter", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for zone_name, filters in self.config.filters.items():
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, f"  {zone_name}:", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Courier", "", 9)
                for i, f in enumerate(filters, 1):
                    if f.enabled:
                        pdf.cell(0, 6,
                                 f"    #{i:2d} {f.filter_type.value}  "
                                 f"{f.frequency:8.1f} Hz  {f.gain:+6.1f} dB  Q={f.q:.2f}",
                                 new_x="LMARGIN", new_y="NEXT")

        pdf.output(str(path))
        self._status.setText(f"Report erstellt: {path}")
