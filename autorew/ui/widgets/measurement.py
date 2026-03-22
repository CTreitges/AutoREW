"""Measurement Widget - Sweep-Steuerung und Guided Mode."""

from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from autorew.models import MeasurementSummary, ProjectConfig, SweepConfig, Zone
from autorew.rew_client import REWClient, REWClientError
from autorew.ui.styles import COLORS as C, btn_primary, btn_success, btn_danger, btn_ghost, card_info


class SweepWorker(QThread):
    """Fuehrt Sweep-Messungen im Hintergrund aus."""

    progress = pyqtSignal(str)
    measurement_done = pyqtSignal(str, int)
    error = pyqtSignal(str)
    finished_all = pyqtSignal()

    def __init__(self, client: REWClient, zone: Zone, position: int,
                 sweep_config: SweepConfig):
        super().__init__()
        self.client = client
        self.zone = zone
        self.position = position
        self.sweep_config = sweep_config
        self._cancelled = False

    def run(self):
        try:
            self.progress.emit(f"Setze Ausgangskanal {self.zone.output_channel}...")
            self.client.set_output_channel(self.zone.output_channel)

            self.progress.emit("Konfiguriere Sweep...")
            self.client.configure_sweep(self.sweep_config)

            name = f"{self.zone.name} - Pos {self.position}"
            self.client.set_measurement_notes(name)

            before = len(self.client.get_measurements())

            self.progress.emit(f"Starte Messung: {name}...")
            self.client.start_sweep()

            self.progress.emit("Messe...")
            for _ in range(300):
                if self._cancelled:
                    return
                time.sleep(1)
                current = len(self.client.get_measurements())
                if current > before:
                    new_index = current - 1
                    self.client.set_measurement_name(new_index, name)
                    self.measurement_done.emit(self.zone.name, new_index)
                    self.progress.emit(f"Messung abgeschlossen: {name}")
                    break
            else:
                self.error.emit("Timeout: Messung hat zu lange gedauert")

        except REWClientError as e:
            self.error.emit(str(e))
        finally:
            self.finished_all.emit()

    def cancel(self):
        self._cancelled = True


# Routing-Modi
MODE_MULTI_OUTPUT = "multi_output"
MODE_SINGLE_OUTPUT = "single_output"


class MeasurementWidget(QWidget):
    """Step 3: Messungen durchfuehren (Pro: automatisch, Standard: guided)."""

    def __init__(self, client: REWClient, config: ProjectConfig, parent=None):
        super().__init__(parent)
        self.client = client
        self.config = config
        self._worker: Optional[SweepWorker] = None
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_new_measurements)
        self._last_measurement_count = 0
        self._current_zone_idx = 0
        self._current_position = 1
        self._routing_mode = MODE_MULTI_OUTPUT
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        header = QLabel("Messungen")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(header)

        # --- Routing Mode ---
        routing_group = QGroupBox("Signal-Routing")
        routing_layout = QVBoxLayout(routing_group)
        routing_layout.setSpacing(10)

        routing_desc = QLabel(
            "Wie wird das Messsignal an die einzelnen Zonen geroutet?"
        )
        routing_desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 12px;")
        routing_desc.setWordWrap(True)
        routing_layout.addWidget(routing_desc)

        self._radio_multi = QRadioButton("Mehrere Ausgaenge (REW schaltet Kanaele)")
        self._radio_multi.setStyleSheet(f"color: {C['text_primary']}; spacing: 8px;")
        self._radio_multi.setChecked(True)

        multi_desc = QLabel(
            "REW wechselt automatisch den Ausgangskanal pro Zone. "
            "Jede Zone hat ihren eigenen physischen Ausgang."
        )
        multi_desc.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; margin-left: 24px;")
        multi_desc.setWordWrap(True)

        self._radio_single = QRadioButton("Ein Ausgang + DSP-Muting (z.B. t.racks DSP 306)")
        self._radio_single.setStyleSheet(f"color: {C['text_primary']}; spacing: 8px;")

        single_desc = QLabel(
            "Das Messsignal geht immer ueber den gleichen Ausgang. "
            "Du mutest die Zonen manuell am DSP-Controller. "
            "Der Assistent fuehrt dich Schritt fuer Schritt."
        )
        single_desc.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; margin-left: 24px;")
        single_desc.setWordWrap(True)

        self._radio_group = QButtonGroup(self)
        self._radio_group.addButton(self._radio_multi, 0)
        self._radio_group.addButton(self._radio_single, 1)
        self._radio_group.idToggled.connect(self._on_routing_changed)

        routing_layout.addWidget(self._radio_multi)
        routing_layout.addWidget(multi_desc)
        routing_layout.addSpacing(4)
        routing_layout.addWidget(self._radio_single)
        routing_layout.addWidget(single_desc)

        layout.addWidget(routing_group)

        # --- Sweep Config ---
        sweep_group = QGroupBox("Sweep-Einstellungen")
        sweep_layout = QFormLayout(sweep_group)
        sweep_layout.setSpacing(12)

        self._start_freq = QDoubleSpinBox()
        self._start_freq.setRange(1, 1000)
        self._start_freq.setValue(20)
        self._start_freq.setSuffix(" Hz")
        sweep_layout.addRow("Startfrequenz:", self._start_freq)

        self._end_freq = QDoubleSpinBox()
        self._end_freq.setRange(1000, 24000)
        self._end_freq.setValue(20000)
        self._end_freq.setSuffix(" Hz")
        sweep_layout.addRow("Endfrequenz:", self._end_freq)

        self._level = QDoubleSpinBox()
        self._level.setRange(-60, 0)
        self._level.setValue(-12)
        self._level.setSuffix(" dBFS")
        sweep_layout.addRow("Pegel:", self._level)

        self._repetitions = QSpinBox()
        self._repetitions.setRange(1, 10)
        self._repetitions.setValue(1)
        sweep_layout.addRow("Wiederholungen:", self._repetitions)

        layout.addWidget(sweep_group)

        # --- Guide Panel ---
        guide_group = QGroupBox("Mess-Assistent")
        guide_layout = QVBoxLayout(guide_group)
        guide_layout.setSpacing(12)

        # Step counter
        self._step_header = QLabel("")
        self._step_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._step_header.setStyleSheet(f"color: {C['accent']};")
        guide_layout.addWidget(self._step_header)

        self._guide_label = QLabel("Druecke 'Messung starten' um zu beginnen.")
        self._guide_label.setWordWrap(True)
        self._guide_label.setFont(QFont("Segoe UI", 13))
        self._guide_label.setStyleSheet(card_info())
        self._guide_label.setMinimumHeight(80)
        guide_layout.addWidget(self._guide_label)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        guide_layout.addWidget(self._progress)

        # Mute-Checklist (nur im Single-Output-Modus sichtbar)
        self._mute_info = QLabel("")
        self._mute_info.setWordWrap(True)
        self._mute_info.setStyleSheet(f"""
            QLabel {{
                background: {C['bg_card']};
                border: 1px solid {C['warning']};
                border-left: 3px solid {C['warning']};
                border-radius: 8px;
                padding: 12px 16px;
                color: {C['text_primary']};
                font-size: 12px;
            }}
        """)
        self._mute_info.setVisible(False)
        guide_layout.addWidget(self._mute_info)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_ready = QPushButton("Bereit - weiter")
        self._btn_ready.setFixedHeight(42)
        self._btn_ready.setStyleSheet(btn_primary())
        self._btn_ready.clicked.connect(self._on_ready_confirmed)
        self._btn_ready.setVisible(False)

        self._btn_start = QPushButton("Messung starten")
        self._btn_start.setFixedHeight(42)
        self._btn_start.setStyleSheet(btn_success())
        self._btn_start.clicked.connect(self._start_measurement)

        self._btn_skip = QPushButton("Ueberspringen")
        self._btn_skip.setStyleSheet(btn_ghost())
        self._btn_skip.clicked.connect(self._skip_position)

        self._btn_cancel = QPushButton("Abbrechen")
        self._btn_cancel.setStyleSheet(btn_danger())
        self._btn_cancel.clicked.connect(self._cancel_measurement)
        self._btn_cancel.setEnabled(False)

        btn_row.addWidget(self._btn_ready)
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_skip)
        btn_row.addWidget(self._btn_cancel)
        guide_layout.addLayout(btn_row)

        layout.addWidget(guide_group)

        # --- Measurement List ---
        list_group = QGroupBox("Durchgefuehrte Messungen")
        list_layout = QVBoxLayout(list_group)

        self._measurement_list = QListWidget()
        self._measurement_list.setMinimumHeight(160)
        list_layout.addWidget(self._measurement_list)

        self._btn_refresh_list = QPushButton("Liste aktualisieren")
        self._btn_refresh_list.clicked.connect(self._refresh_measurement_list)
        list_layout.addWidget(self._btn_refresh_list)

        layout.addWidget(list_group)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # --- Routing Mode ---

    def _on_routing_changed(self, btn_id: int, checked: bool):
        if not checked:
            return
        self._routing_mode = MODE_SINGLE_OUTPUT if btn_id == 1 else MODE_MULTI_OUTPUT
        self._current_zone_idx = 0
        self._current_position = 1
        self._update_guide()

    def _is_single_output(self) -> bool:
        return self._routing_mode == MODE_SINGLE_OUTPUT

    # --- Lifecycle ---

    def on_activated(self):
        self._resume_from_existing()
        self._update_guide()
        self._refresh_measurement_list()

    def _resume_from_existing(self):
        """Setzt den Zaehler auf die erste Zone/Position die noch nicht gemessen wurde."""
        for i, zone in enumerate(self.config.zones):
            measured = len(zone.measurement_ids)
            if measured < zone.positions:
                self._current_zone_idx = i
                self._current_position = measured + 1
                return
        # Alle Zonen fertig
        self._current_zone_idx = len(self.config.zones)
        self._current_position = 1

    def _get_sweep_config(self) -> SweepConfig:
        return SweepConfig(
            start_freq=self._start_freq.value(),
            end_freq=self._end_freq.value(),
            level=self._level.value(),
            repetitions=self._repetitions.value(),
        )

    def _current_zone(self) -> Optional[Zone]:
        if self._current_zone_idx < len(self.config.zones):
            return self.config.zones[self._current_zone_idx]
        return None

    # --- Guide Updates ---

    def _get_step_number(self) -> tuple[int, int]:
        """Liefert (aktuelle Messung, Gesamt)."""
        total = sum(z.positions for z in self.config.zones)
        done = sum(
            self.config.zones[i].positions
            for i in range(self._current_zone_idx)
        ) + self._current_position - 1
        return done + 1, total

    def _build_mute_list(self, active_zone: Zone) -> str:
        """Erstellt eine Mute/Unmute-Anleitung fuer alle Zonen."""
        lines = []
        for zone in self.config.zones:
            if zone.name == active_zone.name:
                lines.append(f"  CH {zone.output_channel}: {zone.name}  --  UNMUTE / SOLO")
            else:
                lines.append(f"  CH {zone.output_channel}: {zone.name}  --  MUTE")
        return "\n".join(lines)

    def _update_guide(self):
        zone = self._current_zone()

        if not zone:
            self._step_header.setText("Fertig!")
            self._guide_label.setText(
                "Alle Zonen gemessen! Gehe weiter zu 'Analyse & EQ'."
            )
            self._btn_start.setEnabled(False)
            self._btn_ready.setVisible(False)
            self._mute_info.setVisible(False)
            self._progress.setValue(100)
            return

        current_step, total = self._get_step_number()
        pos_desc = zone.get_position_name(self._current_position)
        self._progress.setMaximum(total)
        self._progress.setValue(current_step - 1)
        self._step_header.setText(
            f"Messung {current_step} von {total}  -  "
            f"Zone: {zone.name} (Kanal {zone.output_channel}), "
            f"Position {self._current_position}/{zone.positions}"
        )

        if self._is_single_output():
            self._update_guide_single_output(zone)
        elif self.config.is_pro_license:
            self._update_guide_auto(zone)
        else:
            self._update_guide_manual(zone)

    def _update_guide_single_output(self, zone: Zone):
        """Guide fuer Single-Output + DSP-Muting Modus."""
        self._btn_ready.setVisible(True)
        self._btn_start.setVisible(False)
        self._mute_info.setVisible(True)

        mute_list = self._build_mute_list(zone)
        self._mute_info.setText(
            f"DSP-Controller Muting:\n\n{mute_list}"
        )

        pos_desc = zone.get_position_name(self._current_position)
        self._guide_label.setText(
            f"1. Stelle am DSP-Controller folgende Mutes ein (siehe unten)\n"
            f"2. Nur '{zone.name}' (CH {zone.output_channel}) soll aktiv sein\n"
            f"3. Mikrofon-Position: {pos_desc}\n"
            f"4. Druecke 'Bereit - weiter' wenn alles stimmt"
        )

    def _on_ready_confirmed(self):
        """User hat Muting bestaetigt - jetzt Messung starten lassen."""
        self._btn_ready.setVisible(False)
        self._btn_start.setVisible(True)
        self._mute_info.setVisible(False)

        zone = self._current_zone()
        if not zone:
            return

        pos_desc = zone.get_position_name(self._current_position)
        if self.config.is_pro_license:
            self._guide_label.setText(
                f"Muting OK - '{zone.name}' ist aktiv.\n"
                f"Mikrofon: {pos_desc}\n\n"
                f"Druecke jetzt 'Messung starten' - der Sweep wird automatisch ausgefuehrt."
            )
        else:
            self._guide_label.setText(
                f"Muting OK - '{zone.name}' ist aktiv.\n"
                f"Mikrofon: {pos_desc}\n\n"
                f"1. Starte die Messung manuell in REW\n"
                f"2. Druecke dann 'Messung starten' damit ich die Messung erkennen kann"
            )

    def _update_guide_auto(self, zone: Zone):
        """Guide fuer Multi-Output + Pro-Lizenz."""
        self._btn_ready.setVisible(False)
        self._btn_start.setVisible(True)
        self._mute_info.setVisible(False)

        pos_desc = zone.get_position_name(self._current_position)
        self._guide_label.setText(
            f"Mikrofon-Position: {pos_desc}\n\n"
            f"Druecke 'Messung starten' - REW schaltet automatisch auf "
            f"Kanal {zone.output_channel} und fuehrt den Sweep aus."
        )

    def _update_guide_manual(self, zone: Zone):
        """Guide fuer Multi-Output + Standard-Lizenz."""
        self._btn_ready.setVisible(False)
        self._btn_start.setVisible(True)
        self._mute_info.setVisible(False)

        pos_desc = zone.get_position_name(self._current_position)
        self._guide_label.setText(
            f"Mikrofon-Position: {pos_desc}\n\n"
            f"1. Stelle in REW den Ausgangskanal auf {zone.output_channel}\n"
            f"2. Starte die Messung manuell in REW\n"
            f"3. Druecke dann 'Messung starten' damit ich die Messung erkennen kann"
        )

    # --- Measurement Execution ---

    def _start_measurement(self):
        zone = self._current_zone()
        if not zone:
            return

        if self.config.is_pro_license:
            self._start_auto_sweep(zone)
        else:
            self._start_guided_mode(zone)

    def _start_auto_sweep(self, zone: Zone):
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)

        self._worker = SweepWorker(
            self.client, zone, self._current_position, self._get_sweep_config()
        )
        self._worker.progress.connect(self._on_sweep_progress)
        self._worker.measurement_done.connect(self._on_measurement_done)
        self._worker.error.connect(self._on_sweep_error)
        self._worker.finished_all.connect(self._on_sweep_finished)
        self._worker.start()

    def _start_guided_mode(self, zone: Zone):
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)

        try:
            self._last_measurement_count = len(self.client.get_measurements())
        except REWClientError:
            self._last_measurement_count = 0

        self._guide_label.setText(
            f"Warte auf Messung in REW...\n"
            f"Zone: {zone.name}, Position {self._current_position}\n\n"
            f"Fuehre jetzt die Messung in REW durch."
        )
        self._poll_timer.start(1000)

    def _poll_new_measurements(self):
        try:
            measurements = self.client.get_measurements()
            if len(measurements) > self._last_measurement_count:
                self._poll_timer.stop()
                new_index = len(measurements) - 1
                zone = self._current_zone()
                if zone:
                    name = f"{zone.name} - Pos {self._current_position}"
                    try:
                        self.client.set_measurement_name(new_index, name)
                    except REWClientError:
                        pass
                    self._on_measurement_done(zone.name, new_index)
                self._on_sweep_finished()
        except REWClientError:
            pass

    def _on_sweep_progress(self, msg: str):
        zone = self._current_zone()
        zone_info = f"Zone: {zone.name}" if zone else ""
        self._guide_label.setText(f"{zone_info}\n{msg}")

    def _on_measurement_done(self, zone_name: str, index: int):
        for zone in self.config.zones:
            if zone.name == zone_name:
                zone.measurement_ids.append(index)
                break

        self._measurement_list.addItem(f"[{index}] {zone_name} - Pos {self._current_position}")

    def _on_sweep_error(self, msg: str):
        self._guide_label.setText(f"Fehler: {msg}")

    def _on_sweep_finished(self):
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._advance_position()
        self._update_guide()

    def _advance_position(self):
        zone = self._current_zone()
        if not zone:
            return
        if self._current_position < zone.positions:
            self._current_position += 1
        else:
            self._current_zone_idx += 1
            self._current_position = 1

    def _skip_position(self):
        self._advance_position()
        self._update_guide()

    def _cancel_measurement(self):
        if self._worker:
            self._worker.cancel()
        self._poll_timer.stop()
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._update_guide()

    def _refresh_measurement_list(self):
        self._measurement_list.clear()
        try:
            measurements = self.client.get_measurements()
            for m in measurements:
                self._measurement_list.addItem(f"[{m.index}] {m.name}")
        except REWClientError:
            self._measurement_list.addItem("Keine Verbindung zu REW")
