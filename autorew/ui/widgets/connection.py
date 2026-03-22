"""Connection & Audio Setup Widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
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
    QVBoxLayout,
    QWidget,
)

from autorew.models import (
    AudioConfig, DevicePreset, DriverType, ProjectConfig,
    DEVICE_PRESETS, MANUAL_DEVICE_NAME,
)
from autorew.rew_client import REWClient, REWClientError
from autorew.ui.styles import COLORS as C, btn_primary, btn_success, card_info


class ConnectionWidget(QWidget):
    """Step 1: REW-Verbindung, Audio-Setup, Mic-Kalibrierung."""

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

        # Header
        header = QLabel("Verbindung & Setup")
        header.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(header)

        desc = QLabel("Stelle sicher, dass REW laeuft und die API aktiviert ist (REW > Preferences > API > Enable API Server).")
        desc.setStyleSheet(f"color: {C['text_secondary']}; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Connection ---
        conn_group = QGroupBox("REW Verbindung")
        conn_layout = QFormLayout(conn_group)
        conn_layout.setSpacing(12)

        host_row = QHBoxLayout()
        self._host_input = QLineEdit("localhost")
        self._host_input.setFixedWidth(200)
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(4735)
        self._port_input.setFixedWidth(100)
        colon = QLabel(":")
        colon.setFixedWidth(10)
        host_row.addWidget(self._host_input)
        host_row.addWidget(colon)
        host_row.addWidget(self._port_input)
        host_row.addStretch()
        conn_layout.addRow("Host / Port:", host_row)

        status_row = QHBoxLayout()
        self._status_indicator = QLabel()
        self._status_indicator.setFixedSize(10, 10)
        self._status_indicator.setStyleSheet(f"""
            background: {C['danger']};
            border-radius: 5px;
        """)
        self._status_label = QLabel("Nicht verbunden")
        self._status_label.setStyleSheet(f"color: {C['text_secondary']};")
        self._btn_connect = QPushButton("Verbinden")
        self._btn_connect.setFixedWidth(130)
        self._btn_connect.setStyleSheet(btn_primary())
        self._btn_connect.clicked.connect(self._connect)
        status_row.addWidget(self._status_indicator)
        status_row.addWidget(self._status_label)
        status_row.addSpacing(12)
        status_row.addWidget(self._btn_connect)
        status_row.addStretch()
        conn_layout.addRow("Status:", status_row)

        self._license_label = QLabel("")
        self._license_label.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px;")
        conn_layout.addRow("Lizenz:", self._license_label)

        # Demo-Modus Button
        demo_row = QHBoxLayout()
        self._btn_demo = QPushButton("Demo-Modus starten")
        self._btn_demo.setToolTip("UI mit simulierten Daten testen - ohne REW-Verbindung")
        self._btn_demo.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['warning']};
                border: 1px solid {C['warning']};
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {C['warning']};
                color: {C['bg_dark']};
            }}
        """)
        self._btn_demo.clicked.connect(self._toggle_demo)
        demo_row.addWidget(self._btn_demo)
        demo_row.addStretch()
        conn_layout.addRow("", demo_row)

        layout.addWidget(conn_group)

        # --- Device Preset ---
        device_group = QGroupBox("Audio-Geraet")
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(12)

        device_form = QFormLayout()
        device_form.setSpacing(12)
        self._device_combo = QComboBox()
        self._device_combo.addItem(MANUAL_DEVICE_NAME)
        for name in DEVICE_PRESETS:
            self._device_combo.addItem(name)
        self._device_combo.currentTextChanged.connect(self._on_device_changed)
        device_form.addRow("Geraet:", self._device_combo)
        device_layout.addLayout(device_form)

        self._device_notes = QLabel("")
        self._device_notes.setWordWrap(True)
        self._device_notes.setStyleSheet(card_info())
        self._device_notes.setVisible(False)
        device_layout.addWidget(self._device_notes)

        layout.addWidget(device_group)

        # --- Audio Driver ---
        self._audio_group = QGroupBox("Audio-Interface")
        audio_layout = QFormLayout(self._audio_group)
        audio_layout.setSpacing(12)

        self._driver_combo = QComboBox()
        self._driver_combo.addItems(["Java", "ASIO"])
        self._driver_combo.currentTextChanged.connect(self._on_driver_changed)
        audio_layout.addRow("Treiber:", self._driver_combo)

        self._input_combo = QComboBox()
        self._input_combo.setMinimumWidth(300)
        self._btn_refresh_audio = QPushButton("Aktualisieren")
        self._btn_refresh_audio.setFixedWidth(130)
        self._btn_refresh_audio.clicked.connect(self._refresh_devices)
        input_row = QHBoxLayout()
        input_row.addWidget(self._input_combo, 1)
        input_row.addWidget(self._btn_refresh_audio)
        audio_layout.addRow("Eingang:", input_row)

        self._output_combo = QComboBox()
        self._output_combo.setMinimumWidth(300)
        audio_layout.addRow("Ausgang:", self._output_combo)

        self._input_ch_spin = QSpinBox()
        self._input_ch_spin.setRange(1, 64)
        self._input_ch_spin.setFixedWidth(80)
        audio_layout.addRow("Eingangskanal:", self._input_ch_spin)

        self._samplerate_combo = QComboBox()
        self._samplerate_combo.setFixedWidth(140)
        audio_layout.addRow("Samplerate:", self._samplerate_combo)

        layout.addWidget(self._audio_group)

        # --- Mic Calibration ---
        cal_group = QGroupBox("Mikrofon-Kalibrierung")
        cal_layout = QFormLayout(cal_group)
        cal_layout.setSpacing(12)

        cal_row = QHBoxLayout()
        self._cal_path = QLineEdit()
        self._cal_path.setPlaceholderText("Pfad zur .cal / .txt Datei")
        self._cal_path.setReadOnly(True)
        self._btn_browse_cal = QPushButton("Durchsuchen...")
        self._btn_browse_cal.setFixedWidth(130)
        self._btn_browse_cal.clicked.connect(self._browse_cal)
        self._btn_load_cal = QPushButton("Laden")
        self._btn_load_cal.setFixedWidth(80)
        self._btn_load_cal.clicked.connect(self._load_cal)
        cal_row.addWidget(self._cal_path, 1)
        cal_row.addWidget(self._btn_browse_cal)
        cal_row.addWidget(self._btn_load_cal)
        cal_layout.addRow("Cal-Datei:", cal_row)

        layout.addWidget(cal_group)

        # --- Apply Button ---
        self._btn_apply = QPushButton("Audio-Einstellungen anwenden")
        self._btn_apply.setFixedHeight(42)
        self._btn_apply.setStyleSheet(btn_success())
        self._btn_apply.clicked.connect(self._apply_audio)
        layout.addWidget(self._btn_apply)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _main_window(self):
        """Zugriff auf das MainWindow."""
        from autorew.ui.main_window import MainWindow
        w = self.window()
        return w if isinstance(w, MainWindow) else None

    def _toggle_demo(self):
        mw = self._main_window()
        if not mw:
            return
        if mw._demo_mode:
            mw.deactivate_demo_mode()
            self._btn_demo.setText("Demo-Modus starten")
            self._set_connected(False, "Nicht verbunden")
            self._license_label.setText("")
        else:
            mw.activate_demo_mode()
            self._btn_demo.setText("Demo-Modus beenden")
            self._set_connected(True, "Demo-Modus aktiv")
            self._license_label.setText("Pro (Demo)")
            self._refresh_devices()

    def on_activated(self):
        mw = self._main_window()
        if mw and mw._demo_mode:
            return
        if not self.client.is_connected():
            self._connect()

    def _set_connected(self, connected: bool, text: str = ""):
        if connected:
            self._status_indicator.setStyleSheet(f"background: {C['success']}; border-radius: 5px;")
            self._status_label.setText(text or "Verbunden")
            self._status_label.setStyleSheet(f"color: {C['success']};")
        else:
            self._status_indicator.setStyleSheet(f"background: {C['danger']}; border-radius: 5px;")
            self._status_label.setText(text or "Nicht verbunden")
            self._status_label.setStyleSheet(f"color: {C['danger']};")

    def _on_device_changed(self, device_name: str):
        preset = DEVICE_PRESETS.get(device_name)
        if preset:
            self._device_notes.setText(preset.notes)
            self._device_notes.setVisible(True)
            self._apply_device_preset(preset)
        else:
            self._device_notes.setVisible(False)

    def _apply_device_preset(self, preset: DevicePreset):
        # Treiber setzen
        idx = self._driver_combo.findText(preset.driver.value)
        if idx >= 0:
            self._driver_combo.setCurrentIndex(idx)

        # Eingangskanal
        self._input_ch_spin.setValue(preset.input_channel)

        # Samplerate
        rate_idx = self._samplerate_combo.findText(str(preset.sample_rate))
        if rate_idx >= 0:
            self._samplerate_combo.setCurrentIndex(rate_idx)

        # Geraet in Dropdowns vorwaehlen (falls verfuegbar)
        if preset.input_hint:
            self._select_by_hint(self._input_combo, preset.input_hint)
        if preset.output_hint:
            self._select_by_hint(self._output_combo, preset.output_hint)

    @staticmethod
    def _select_by_hint(combo: QComboBox, hint: str):
        hint_lower = hint.lower()
        for i in range(combo.count()):
            if hint_lower in combo.itemText(i).lower():
                combo.setCurrentIndex(i)
                return

    def _connect(self):
        self.client.base_url = f"http://{self._host_input.text()}:{self._port_input.value()}"
        try:
            if self.client.is_connected():
                self._set_connected(True)

                is_pro = self.client.is_pro_license()
                self.config.is_pro_license = is_pro
                self._license_label.setText(
                    "Pro (automatische Sweeps moeglich)" if is_pro
                    else "Standard (manuelle Sweeps)"
                )

                self._refresh_devices()
                self._load_current_audio()
            else:
                self._set_connected(False, "Verbindung fehlgeschlagen")
        except REWClientError as e:
            self._set_connected(False, str(e))

    def _on_driver_changed(self, driver: str):
        self._refresh_devices()

    def _refresh_devices(self):
        if not self.client.is_connected():
            return
        try:
            driver = self._driver_combo.currentText()
            self._input_combo.clear()
            self._output_combo.clear()

            if driver == "ASIO":
                devices = self.client.get_asio_devices()
                self._input_combo.addItems(devices)
                self._output_combo.addItems(devices)
            else:
                inputs = self.client.get_java_input_devices()
                outputs = self.client.get_java_output_devices()
                self._input_combo.addItems(inputs)
                self._output_combo.addItems(outputs)

            rates = self.client.get_sample_rates()
            self._samplerate_combo.clear()
            self._samplerate_combo.addItems([str(r) for r in rates])

            current_rate = self.client.get_sample_rate()
            idx = self._samplerate_combo.findText(str(current_rate))
            if idx >= 0:
                self._samplerate_combo.setCurrentIndex(idx)

            # Falls ein Geraete-Preset aktiv ist, nochmal Hints anwenden
            preset = DEVICE_PRESETS.get(self._device_combo.currentText())
            if preset:
                if preset.input_hint:
                    self._select_by_hint(self._input_combo, preset.input_hint)
                if preset.output_hint:
                    self._select_by_hint(self._output_combo, preset.output_hint)

        except REWClientError:
            pass

    def _load_current_audio(self):
        try:
            driver = self.client.get_driver_type()
            idx = self._driver_combo.findText(driver)
            if idx >= 0:
                self._driver_combo.setCurrentIndex(idx)

            cal = self.client.get_mic_cal()
            if cal:
                self._cal_path.setText(cal)
        except REWClientError:
            pass

    def _browse_cal(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Kalibrierungsdatei waehlen", "",
            "Cal Files (*.cal *.txt);;Alle Dateien (*.*)",
        )
        if path:
            self._cal_path.setText(path)

    def _load_cal(self):
        path = self._cal_path.text()
        if path and self.client.is_connected():
            try:
                self.client.load_mic_cal(path)
                self.config.audio.mic_cal_path = path
            except REWClientError as e:
                self._set_connected(False, f"Cal-Fehler: {e}")

    def _apply_audio(self):
        if not self.client.is_connected():
            return
        try:
            driver_text = self._driver_combo.currentText()
            driver = DriverType.ASIO if driver_text == "ASIO" else DriverType.JAVA
            self.client.set_driver_type(driver)

            if driver == DriverType.ASIO:
                if self._input_combo.currentText():
                    self.client.set_asio_device(self._input_combo.currentText())
            else:
                if self._input_combo.currentText():
                    self.client.set_java_input_device(self._input_combo.currentText())
                if self._output_combo.currentText():
                    self.client.set_java_output_device(self._output_combo.currentText())
                self.client.set_java_input_channel(self._input_ch_spin.value())

            rate_text = self._samplerate_combo.currentText()
            if rate_text:
                self.client.set_sample_rate(int(rate_text))

            self.config.audio.driver = driver
            self.config.audio.input_device = self._input_combo.currentText()
            self.config.audio.output_device = self._output_combo.currentText()
            self.config.audio.input_channel = self._input_ch_spin.value()
            self.config.audio.sample_rate = int(rate_text) if rate_text else 48000

            self._set_connected(True, "Verbunden - Audio konfiguriert")

        except REWClientError as e:
            self._set_connected(False, f"Audio-Fehler: {e}")
