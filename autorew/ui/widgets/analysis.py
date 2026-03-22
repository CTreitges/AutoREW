"""Analysis Widget - Alignment, EQ, Visualisierung."""

from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autorew.models import (
    AlignmentResult,
    DelayRecommendation,
    EQCommand,
    EqualizerPreset,
    EQUALIZER_PRESETS,
    FilterSetting,
    ProcessCommand,
    ProjectConfig,
    TargetSettings,
)
from autorew.rew_client import REWClient, REWClientError
from autorew.ui.styles import COLORS as C, btn_primary, btn_success, btn_ghost, card_info


class FreqResponseCanvas(FigureCanvas):
    """Matplotlib-Canvas fuer Frequenzgang-Darstellung."""

    def __init__(self, parent=None, width=8, height=4):
        self.fig = Figure(figsize=(width, height), facecolor=C["bg_surface"])
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self._style_axes()

    def _style_axes(self):
        self.ax.set_facecolor(C["bg_dark"])
        self.ax.set_xlabel("Frequenz (Hz)", color=C["text_secondary"], fontsize=10)
        self.ax.set_ylabel("SPL (dB)", color=C["text_secondary"], fontsize=10)
        self.ax.tick_params(colors=C["text_muted"], labelsize=9)
        self.ax.grid(True, alpha=0.15, color=C["text_muted"], linestyle="--")
        self.ax.set_xscale("log")
        self.ax.set_xlim(20, 20000)
        for spine in self.ax.spines.values():
            spine.set_color(C["border"])
        self.fig.tight_layout(pad=1.5)

    def plot_response(self, freqs, mags, label="", color="#58a6ff", linestyle="-"):
        self.ax.plot(freqs, mags, label=label, color=color, linewidth=1.5, linestyle=linestyle)
        if label:
            legend = self.ax.legend(
                facecolor=C["bg_card"], edgecolor=C["border"],
                labelcolor=C["text_primary"], fontsize=9, framealpha=0.9
            )
        self.draw()

    def clear_plot(self):
        self.ax.clear()
        self._style_axes()
        self.draw()


class AnalysisWidget(QWidget):
    """Step 4: Analyse, Alignment, EQ-Generierung."""

    def __init__(self, client: REWClient, config: ProjectConfig, parent=None):
        super().__init__(parent)
        self.client = client
        self.config = config
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # --- Top: Graph ---
        graph_widget = QWidget()
        graph_layout = QVBoxLayout(graph_widget)
        graph_layout.setContentsMargins(32, 24, 32, 8)

        header = QLabel("Analyse & EQ")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        graph_layout.addWidget(header)

        self._canvas = FreqResponseCanvas()
        graph_layout.addWidget(self._canvas, 1)

        splitter.addWidget(graph_widget)

        # --- Bottom: Controls ---
        controls = QWidget()
        ctrl_layout = QVBoxLayout(controls)
        ctrl_layout.setContentsMargins(32, 8, 32, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)

        # --- Processing ---
        proc_group = QGroupBox("Verarbeitung")
        proc_layout = QHBoxLayout(proc_group)
        proc_layout.setSpacing(10)

        self._btn_align_spl = QPushButton("SPL angleichen")
        self._btn_align_spl.clicked.connect(self._align_spl)
        self._btn_time_align = QPushButton("Time-Alignment")
        self._btn_time_align.clicked.connect(self._time_align)
        self._btn_average = QPushButton("Messungen mitteln")
        self._btn_average.clicked.connect(self._average)
        self._btn_show_all = QPushButton("Alle anzeigen")
        self._btn_show_all.clicked.connect(self._show_all_responses)

        proc_layout.addWidget(self._btn_align_spl)
        proc_layout.addWidget(self._btn_time_align)
        proc_layout.addWidget(self._btn_average)
        proc_layout.addWidget(self._btn_show_all)
        proc_layout.addStretch()
        scroll_layout.addWidget(proc_group)

        # --- Alignment Results ---
        align_group = QGroupBox("Delay-Empfehlungen")
        align_layout = QVBoxLayout(align_group)

        self._delay_table = QTableWidget(0, 4)
        self._delay_table.setHorizontalHeaderLabels(["Zone", "Delay (ms)", "Delay (m)", "Level (dB)"])
        self._delay_table.setMaximumHeight(160)
        self._delay_table.verticalHeader().setVisible(False)
        self._delay_table.setShowGrid(False)
        self._delay_table.setAlternatingRowColors(True)
        self._delay_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {C['bg_card']}; }}")
        align_layout.addWidget(self._delay_table)
        scroll_layout.addWidget(align_group)

        # --- EQ ---
        eq_group = QGroupBox("EQ-Generierung")
        eq_form = QFormLayout(eq_group)
        eq_form.setSpacing(12)

        self._target_level = QDoubleSpinBox()
        self._target_level.setRange(40, 120)
        self._target_level.setValue(75)
        self._target_level.setSuffix(" dB")
        eq_form.addRow("Target Level:", self._target_level)

        self._eq_combo = QComboBox()
        for preset_name in EQUALIZER_PRESETS:
            self._eq_combo.addItem(preset_name)
        self._eq_combo.currentTextChanged.connect(self._on_eq_preset_changed)
        eq_form.addRow("Equaliser:", self._eq_combo)

        self._eq_info = QLabel("")
        self._eq_info.setWordWrap(True)
        self._eq_info.setStyleSheet(card_info())
        self._eq_info.setVisible(False)
        eq_form.addRow(self._eq_info)

        self._on_eq_preset_changed(self._eq_combo.currentText())

        eq_btn_row = QHBoxLayout()
        eq_btn_row.setSpacing(10)
        self._btn_match_target = QPushButton("EQ berechnen (Match Target)")
        self._btn_match_target.setStyleSheet(btn_success())
        self._btn_match_target.clicked.connect(self._match_target)

        self._btn_show_predicted = QPushButton("Predicted anzeigen")
        self._btn_show_predicted.clicked.connect(self._show_predicted)

        eq_btn_row.addWidget(self._btn_match_target)
        eq_btn_row.addWidget(self._btn_show_predicted)
        eq_btn_row.addStretch()
        eq_form.addRow(eq_btn_row)

        scroll_layout.addWidget(eq_group)

        # --- Filter Table ---
        filter_group = QGroupBox("Generierte Filter")
        filter_layout = QVBoxLayout(filter_group)

        self._filter_table = QTableWidget(0, 5)
        self._filter_table.setHorizontalHeaderLabels(["Zone", "Typ", "Frequenz (Hz)", "Gain (dB)", "Q"])
        self._filter_table.setMaximumHeight(200)
        self._filter_table.verticalHeader().setVisible(False)
        self._filter_table.setShowGrid(False)
        self._filter_table.setAlternatingRowColors(True)
        self._filter_table.setStyleSheet(f"QTableWidget {{ alternate-background-color: {C['bg_card']}; }}")
        filter_layout.addWidget(self._filter_table)
        scroll_layout.addWidget(filter_group)

        scroll.setWidget(scroll_content)
        ctrl_layout.addWidget(scroll)

        splitter.addWidget(controls)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

    def _get_active_preset(self) -> Optional[EqualizerPreset]:
        name = self._eq_combo.currentText()
        return EQUALIZER_PRESETS.get(name)

    def _on_eq_preset_changed(self, name: str):
        preset = EQUALIZER_PRESETS.get(name)
        if preset and name != "Generic":
            types = ", ".join(ft.value for ft in preset.filter_types)
            lines = [f"{preset.peq_bands} PEQ-Baender  |  Filter: {types}"]
            lines.append(f"Gain: {preset.gain_min:+.0f} ... {preset.gain_max:+.0f} dB  |  "
                         f"Q: {preset.q_min} ... {preset.q_max}")
            if preset.has_crossover:
                xo_types = ", ".join(ct.value for ct in preset.crossover_types)
                xo_slopes = "/".join(f"{s}" for s in preset.crossover_slopes)
                lines.append(f"Crossover: {xo_types} ({xo_slopes} dB/Oct)")
            extras = []
            if preset.has_delay:
                extras.append(f"Delay bis {preset.delay_max_ms:.0f}ms")
            if preset.has_limiter:
                extras.append("Limiter")
            if preset.has_compressor:
                extras.append("Kompressor")
            if preset.has_geq:
                extras.append(f"{preset.geq_bands}-Band GEQ")
            if extras:
                lines.append(" | ".join(extras))
            self._eq_info.setText("\n".join(lines))
            self._eq_info.setVisible(True)
        else:
            self._eq_info.setVisible(False)

    def on_activated(self):
        self._show_all_responses()

    def _get_all_measurement_ids(self) -> list[int]:
        ids = []
        for zone in self.config.zones:
            ids.extend(zone.measurement_ids)
        return ids

    def _show_all_responses(self):
        self._canvas.clear_plot()
        colors = ["#58a6ff", "#3fb950", "#d29922", "#f778ba", "#bc8cff", "#56d4dd", "#f0883e"]

        for i, zone in enumerate(self.config.zones):
            color = colors[i % len(colors)]
            for mid in zone.measurement_ids:
                try:
                    resp = self.client.get_frequency_response(mid, smoothing="1/6")
                    freqs = [p.frequency for p in resp.data]
                    mags = [p.magnitude for p in resp.data]
                    if freqs:
                        self._canvas.plot_response(
                            freqs, mags,
                            label=f"{zone.name} [{mid}]",
                            color=color,
                        )
                except REWClientError:
                    pass

    def _align_spl(self):
        ids = self._get_all_measurement_ids()
        if len(ids) < 2:
            return
        try:
            self.client.align_spl(ids, target_db=self._target_level.value())
            self._show_all_responses()
        except REWClientError:
            pass

    def _time_align(self):
        if len(self.config.zones) < 2:
            return

        self.config.delays.clear()
        self._delay_table.setRowCount(0)

        ref_zone = self.config.zones[0]
        if not ref_zone.measurement_ids:
            return

        ref_id = ref_zone.measurement_ids[0]

        for zone in self.config.zones[1:]:
            if not zone.measurement_ids:
                continue
            zone_id = zone.measurement_ids[0]

            try:
                freq = zone.crossover_freq or 1000.0
                self.client.configure_alignment(ref_id, zone_id, frequency=freq)
                result = self.client.run_alignment()

                delay_ms = float(result.get("delay-b", 0))
                delay_m = delay_ms * 0.343
                gain_diff = float(result.get("gain-b", 0))

                rec = DelayRecommendation(
                    zone_name=zone.name,
                    delay_ms=round(delay_ms, 3),
                    delay_meters=round(delay_m, 2),
                    level_db=round(gain_diff, 1),
                )
                self.config.delays.append(rec)

                row = self._delay_table.rowCount()
                self._delay_table.insertRow(row)
                self._delay_table.setItem(row, 0, QTableWidgetItem(zone.name))
                self._delay_table.setItem(row, 1, QTableWidgetItem(f"{rec.delay_ms:.3f}"))
                self._delay_table.setItem(row, 2, QTableWidgetItem(f"{rec.delay_meters:.2f}"))
                self._delay_table.setItem(row, 3, QTableWidgetItem(f"{rec.level_db:+.1f}"))

            except REWClientError:
                pass

    def _average(self):
        for zone in self.config.zones:
            if len(zone.measurement_ids) > 1:
                try:
                    self.client.average_measurements(zone.measurement_ids)
                except REWClientError:
                    pass
        self._show_all_responses()

    def _clamp_filters_to_preset(self, filters: list[FilterSetting]) -> list[FilterSetting]:
        """Begrenzt Filter auf die Faehigkeiten des gewaehlten Equalizer-Presets."""
        preset = self._get_active_preset()
        if not preset:
            return filters

        clamped = []
        for f in filters[:preset.peq_bands]:
            if f.filter_type not in preset.filter_types:
                f.filter_type = FilterType.PK
            f.frequency = max(preset.freq_min, min(preset.freq_max, f.frequency))
            f.gain = max(preset.gain_min, min(preset.gain_max, f.gain))
            f.q = max(preset.q_min, min(preset.q_max, f.q))
            clamped.append(f)
        return clamped

    def _match_target(self):
        self.config.filters.clear()
        self._filter_table.setRowCount(0)
        preset = self._get_active_preset()

        for zone in self.config.zones:
            if not zone.measurement_ids:
                continue
            mid = zone.measurement_ids[-1]

            try:
                self.client.set_target_level(mid, self._target_level.value())
                filters = self.client.match_target(mid)
                filters = self._clamp_filters_to_preset(filters)
                self.config.filters[zone.name] = filters

                for f in filters:
                    if not f.enabled:
                        continue
                    row = self._filter_table.rowCount()
                    self._filter_table.insertRow(row)
                    self._filter_table.setItem(row, 0, QTableWidgetItem(f"{zone.name}"))
                    self._filter_table.setItem(row, 1, QTableWidgetItem(f.filter_type.value))
                    self._filter_table.setItem(row, 2, QTableWidgetItem(f"{f.frequency:.1f}"))
                    self._filter_table.setItem(row, 3, QTableWidgetItem(f"{f.gain:+.1f}"))
                    self._filter_table.setItem(row, 4, QTableWidgetItem(f"{f.q:.2f}"))

            except REWClientError:
                pass

    def _show_predicted(self):
        self._canvas.clear_plot()
        colors_orig = ["#58a6ff", "#3fb950", "#d29922", "#f778ba"]
        colors_pred = ["#a5d6ff", "#7ee787", "#e3b341", "#ffadda"]

        for i, zone in enumerate(self.config.zones):
            if not zone.measurement_ids:
                continue
            mid = zone.measurement_ids[-1]

            try:
                resp = self.client.get_frequency_response(mid, smoothing="1/6")
                freqs = [p.frequency for p in resp.data]
                mags = [p.magnitude for p in resp.data]
                if freqs:
                    self._canvas.plot_response(
                        freqs, mags,
                        label=f"{zone.name} (Original)",
                        color=colors_orig[i % len(colors_orig)],
                        linestyle="--",
                    )

                pred = self.client.get_predicted_response(mid)
                freqs_p = [p.frequency for p in pred.data]
                mags_p = [p.magnitude for p in pred.data]
                if freqs_p:
                    self._canvas.plot_response(
                        freqs_p, mags_p,
                        label=f"{zone.name} (Predicted)",
                        color=colors_pred[i % len(colors_pred)],
                    )

                target = self.client.get_target_response(mid)
                freqs_t = [p.frequency for p in target.data]
                mags_t = [p.magnitude for p in target.data]
                if freqs_t:
                    self._canvas.plot_response(
                        freqs_t, mags_t,
                        label="Target",
                        color="#f0f6fc",
                        linestyle=":",
                    )

            except REWClientError:
                pass
