"""Setup-Wizard: PA-Konfiguration vor dem Workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QPushButton,
    QVBoxLayout, QWidget,
)

from autorew.models import (
    EQUALIZER_PRESETS, ProjectConfig, SetupConfig, TopConfig,
)
from autorew.ui.styles import COLORS as C, btn_ghost


class _CountSelector(QWidget):
    """Kompakter +/- Zaehler mit Label."""
    value_changed = pyqtSignal(int)

    def __init__(self, label: str, value: int, min_v: int, max_v: int, parent=None):
        super().__init__(parent)
        self._min = min_v
        self._max = max_v
        self._value = value

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setStyleSheet(f"color: {C['text_primary']}; font-size: 13px;")
        layout.addWidget(lbl)

        self._btn_minus = QPushButton("−")
        self._btn_minus.setFixedSize(32, 32)
        self._btn_minus.setStyleSheet(btn_ghost())
        self._btn_minus.clicked.connect(self._decrement)
        layout.addWidget(self._btn_minus)

        self._value_label = QLabel(str(value))
        self._value_label.setFixedWidth(28)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setStyleSheet(
            f"color: {C['accent']}; font-size: 15px; font-weight: bold;"
        )
        layout.addWidget(self._value_label)

        self._btn_plus = QPushButton("+")
        self._btn_plus.setFixedSize(32, 32)
        self._btn_plus.setStyleSheet(btn_ghost())
        self._btn_plus.clicked.connect(self._increment)
        layout.addWidget(self._btn_plus)

        layout.addStretch()
        self._update_buttons()

    def _increment(self):
        if self._value < self._max:
            self._value += 1
            self._value_label.setText(str(self._value))
            self._update_buttons()
            self.value_changed.emit(self._value)

    def _decrement(self):
        if self._value > self._min:
            self._value -= 1
            self._value_label.setText(str(self._value))
            self._update_buttons()
            self.value_changed.emit(self._value)

    def _update_buttons(self):
        self._btn_minus.setEnabled(self._value > self._min)
        self._btn_plus.setEnabled(self._value < self._max)

    @property
    def value(self) -> int:
        return self._value


class SetupWizardWidget(QWidget):
    """Erster Schritt: PA-System konfigurieren."""

    def __init__(self, config: ProjectConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.client = None
        self._target_curve_path: Optional[str] = None
        self._init_ui()
        self._refresh_preview()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(20)

        hdr = QLabel("System-Setup")
        hdr.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C['text_primary']};")
        root.addWidget(hdr)

        sub_hdr = QLabel(
            "Konfiguriere dein PA-System. AutoREW erstellt den "
            "Mess-Workflow automatisch."
        )
        sub_hdr.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px;")
        sub_hdr.setWordWrap(True)
        root.addWidget(sub_hdr)

        cols = QHBoxLayout()
        cols.setSpacing(24)
        root.addLayout(cols, 1)

        # ---- Left: Controls ----
        left = QVBoxLayout()
        left.setSpacing(12)
        cols.addLayout(left, 1)

        grp_tops = QGroupBox("Tops")
        grp_tops.setStyleSheet(self._group_style())
        gl = QVBoxLayout(grp_tops)
        gl.setSpacing(6)
        lbl = QLabel("Konfiguration:")
        lbl.setStyleSheet(f"color: {C['text_secondary']}; font-size: 11px;")
        gl.addWidget(lbl)
        self._top_combo = QComboBox()
        self._top_combo.addItems([t.value for t in TopConfig])
        self._top_combo.setCurrentText(TopConfig.STEREO.value)
        self._top_combo.setStyleSheet(self._combo_style())
        self._top_combo.currentIndexChanged.connect(self._refresh_preview)
        gl.addWidget(self._top_combo)
        left.addWidget(grp_tops)

        grp_subs = QGroupBox("Subwoofer")
        grp_subs.setStyleSheet(self._group_style())
        sl = QVBoxLayout(grp_subs)
        self._subs_sel = _CountSelector("Anzahl Subs:", 1, 0, 4)
        self._subs_sel.value_changed.connect(self._refresh_preview)
        sl.addWidget(self._subs_sel)
        left.addWidget(grp_subs)

        grp_pos = QGroupBox("Messpositionen")
        grp_pos.setStyleSheet(self._group_style())
        pl = QVBoxLayout(grp_pos)
        hint = QLabel("Mikro-Positionen pro Zone")
        hint.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px;")
        pl.addWidget(hint)
        self._pos_sel = _CountSelector("Positionen:", 3, 1, 5)
        self._pos_sel.value_changed.connect(self._refresh_preview)
        pl.addWidget(self._pos_sel)
        left.addWidget(grp_pos)

        grp_dsp = QGroupBox("DSP / EQ Geraet")
        grp_dsp.setStyleSheet(self._group_style())
        dl = QVBoxLayout(grp_dsp)
        dsp_hint = QLabel("Bestimmt Band-Limit, Q-Range und Freq-Raster")
        dsp_hint.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px;")
        dl.addWidget(dsp_hint)
        self._dsp_combo = QComboBox()
        self._dsp_combo.addItems(sorted(EQUALIZER_PRESETS.keys()))
        self._dsp_combo.setStyleSheet(self._combo_style())
        self._dsp_combo.setCurrentText("Generic")
        self._dsp_combo.currentIndexChanged.connect(self._refresh_preview)
        dl.addWidget(self._dsp_combo)
        left.addWidget(grp_dsp)

        grp_curve = QGroupBox("Zielkurve (.targetcurve)")
        grp_curve.setStyleSheet(self._group_style())
        cl = QVBoxLayout(grp_curve)
        c_hint = QLabel("REW .targetcurve oder kompatible Textdatei")
        c_hint.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px;")
        cl.addWidget(c_hint)
        row = QHBoxLayout()
        self._curve_btn = QPushButton("Datei laden …")
        self._curve_btn.setStyleSheet(btn_ghost())
        self._curve_btn.clicked.connect(self._load_target_curve)
        row.addWidget(self._curve_btn)
        self._curve_label = QLabel("Keine Kurve geladen")
        self._curve_label.setStyleSheet(
            f"color: {C['text_muted']}; font-size: 11px;"
        )
        row.addWidget(self._curve_label, 1)
        cl.addLayout(row)
        left.addWidget(grp_curve)

        left.addStretch()

        # ---- Right: Preview ----
        right = QVBoxLayout()
        right.setSpacing(12)
        cols.addLayout(right, 1)

        prev_hdr = QLabel("Mess-Plan Vorschau")
        prev_hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        prev_hdr.setStyleSheet(f"color: {C['text_primary']};")
        right.addWidget(prev_hdr)

        self._preview_list = QListWidget()
        self._preview_list.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_dark']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                color: {C['text_primary']};
                font-size: 12px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                border-radius: 4px;
            }}
        """)
        right.addWidget(self._preview_list, 1)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet(
            f"color: {C['text_muted']}; font-size: 11px;"
        )
        self._summary_label.setWordWrap(True)
        right.addWidget(self._summary_label)

    def _refresh_preview(self):
        setup = self._build_setup()
        zones = setup.generate_zones()

        self._preview_list.clear()
        total_sweeps = 0

        for z in zones:
            header = f"▸  {z.name}  (Kanal {z.output_channel})"
            self._preview_list.addItem(header)
            for p in range(1, z.positions + 1):
                desc = z.get_position_name(p)
                short = desc.split(" - ")[0] if " - " in desc else desc
                self._preview_list.addItem(f"    {p}. {short}")
                total_sweeps += 1
            self._preview_list.addItem("")

        dsp_name = self._dsp_combo.currentText()
        preset = EQUALIZER_PRESETS.get(dsp_name)
        bands = ""
        if preset:
            bands = (
                f"{preset.peq_bands} PEQ-Baender, "
                f"Q {preset.q_min}–{preset.q_max}"
            )

        self._summary_label.setText(
            f"Gesamt: {len(zones)} Zonen · "
            f"{total_sweeps} Sweeps · {bands}"
        )

    def _build_setup(self) -> SetupConfig:
        top_text = self._top_combo.currentText()
        top_cfg = next(
            (t for t in TopConfig if t.value == top_text), TopConfig.STEREO
        )
        return SetupConfig(
            top_config=top_cfg,
            num_subs=self._subs_sel.value,
            num_positions=self._pos_sel.value,
            dsp_preset_name=self._dsp_combo.currentText(),
            target_curve_path=self._target_curve_path or "",
        )

    def _load_target_curve(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Zielkurve laden",
            str(Path.home()),
            "Zielkurven (*.targetcurve *.txt);;Alle Dateien (*)",
        )
        if path:
            self._target_curve_path = path
            self._curve_label.setText(Path(path).name)
            self._curve_label.setStyleSheet(
                f"color: {C['success']}; font-size: 11px;"
            )
            self._refresh_preview()

    def get_setup(self) -> SetupConfig:
        return self._build_setup()

    def on_activated(self):
        self._refresh_preview()

    @staticmethod
    def _group_style() -> str:
        return f"""
            QGroupBox {{
                color: {C['text_secondary']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                margin-top: 8px;
                padding: 8px;
                font-size: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """

    @staticmethod
    def _combo_style() -> str:
        return f"""
            QComboBox {{
                background: {C['bg_surface']};
                color: {C['text_primary']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {C['bg_dark']};
                color: {C['text_primary']};
                selection-background-color: {C['accent_dark']};
            }}
        """
