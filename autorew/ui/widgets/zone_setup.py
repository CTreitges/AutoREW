"""Zone Setup Widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autorew.models import ProjectConfig, Zone, ZoneType, ZONE_PRESETS
from autorew.rew_client import REWClient
from autorew.ui.styles import COLORS as C, btn_primary, btn_danger


class ZoneSetupWidget(QWidget):
    """Step 2: Zonen-Konfiguration mit Presets."""

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

        header = QLabel("Zonen-Konfiguration")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(header)

        desc = QLabel("Definiere die Zonen deiner PA-Anlage. Jede Zone bekommt einen eigenen Ausgangskanal und wird separat gemessen.")
        desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Presets ---
        preset_group = QGroupBox("Schnellauswahl (Presets)")
        preset_layout = QHBoxLayout(preset_group)
        preset_layout.setSpacing(10)
        for name in ZONE_PRESETS:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, n=name: self._load_preset(n))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['bg_dark']};
                    border: 1px solid {C['border']};
                    padding: 10px 18px;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background: {C['accent_dark']};
                    border-color: {C['accent']};
                    color: white;
                }}
            """)
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        layout.addWidget(preset_group)

        # --- Zone Table ---
        table_group = QGroupBox("Zonen")
        table_layout = QVBoxLayout(table_group)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "Name", "Typ", "Ausgangskanal", "Crossover (Hz)", "Positionen"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(1, 130)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(2, 120)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(3, 130)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().resizeSection(4, 100)
        self._table.setMinimumHeight(260)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {C['bg_card']};
            }}
        """)
        table_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._btn_add = QPushButton("+ Zone hinzufuegen")
        self._btn_add.setStyleSheet(btn_primary())
        self._btn_add.clicked.connect(self._add_zone_row)
        self._btn_remove = QPushButton("Ausgewaehlte entfernen")
        self._btn_remove.setStyleSheet(btn_danger())
        self._btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        table_layout.addLayout(btn_row)

        layout.addWidget(table_group)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def on_activated(self):
        if not self.config.zones and self._table.rowCount() == 0:
            self._load_preset("Stereo + Sub")

    def _load_preset(self, preset_name: str):
        zones = ZONE_PRESETS.get(preset_name, [])
        self.config.zones = [z.model_copy() for z in zones]
        self._refresh_table()

    def _refresh_table(self):
        self._table.setRowCount(0)
        for zone in self.config.zones:
            self._add_zone_to_table(zone)

    def _add_zone_to_table(self, zone: Zone):
        row = self._table.rowCount()
        self._table.insertRow(row)

        name_item = QTableWidgetItem(zone.name)
        self._table.setItem(row, 0, name_item)

        type_combo = QComboBox()
        type_combo.addItems([t.value for t in ZoneType])
        idx = type_combo.findText(zone.zone_type.value)
        if idx >= 0:
            type_combo.setCurrentIndex(idx)
        self._table.setCellWidget(row, 1, type_combo)

        ch_spin = QSpinBox()
        ch_spin.setRange(1, 64)
        ch_spin.setValue(zone.output_channel)
        self._table.setCellWidget(row, 2, ch_spin)

        xo_spin = QDoubleSpinBox()
        xo_spin.setRange(0, 20000)
        xo_spin.setDecimals(0)
        xo_spin.setSuffix(" Hz")
        xo_spin.setSpecialValueText("---")
        xo_spin.setValue(zone.crossover_freq or 0)
        self._table.setCellWidget(row, 3, xo_spin)

        pos_spin = QSpinBox()
        pos_spin.setRange(1, 9)
        pos_spin.setValue(zone.positions)
        self._table.setCellWidget(row, 4, pos_spin)

    def _add_zone_row(self):
        new_zone = Zone(
            name=f"Zone {len(self.config.zones) + 1}",
            output_channel=len(self.config.zones) + 1,
        )
        self.config.zones.append(new_zone)
        self._add_zone_to_table(new_zone)

    def _remove_selected(self):
        rows = sorted(set(idx.row() for idx in self._table.selectedIndexes()), reverse=True)
        for row in rows:
            if row < len(self.config.zones):
                self.config.zones.pop(row)
            self._table.removeRow(row)

    def save_to_config(self):
        self.config.zones.clear()
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            name = name_item.text() if name_item else f"Zone {row + 1}"

            type_combo = self._table.cellWidget(row, 1)
            zone_type = ZoneType(type_combo.currentText()) if type_combo else ZoneType.CUSTOM

            ch_spin = self._table.cellWidget(row, 2)
            channel = ch_spin.value() if ch_spin else row + 1

            xo_spin = self._table.cellWidget(row, 3)
            xo = xo_spin.value() if xo_spin else 0

            pos_spin = self._table.cellWidget(row, 4)
            positions = pos_spin.value() if pos_spin else 1

            self.config.zones.append(Zone(
                name=name,
                zone_type=zone_type,
                output_channel=channel,
                crossover_freq=xo if xo > 0 else None,
                is_sub=zone_type == ZoneType.SUB,
                positions=positions,
            ))
