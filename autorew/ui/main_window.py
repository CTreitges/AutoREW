"""AutoREW Hauptfenster mit Wizard-Navigation."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from autorew.demo_client import DemoClient
from autorew.models import ProjectConfig, WorkflowStep, Zone, ZoneType
from autorew.rew_client import REWClient
from autorew.ui.styles import COLORS as C, global_stylesheet, btn_primary, btn_ghost
from autorew.ui.widgets.connection import ConnectionWidget
from autorew.ui.widgets.zone_setup import ZoneSetupWidget
from autorew.ui.widgets.measurement import MeasurementWidget
from autorew.ui.widgets.analysis import AnalysisWidget
from autorew.ui.widgets.export import ExportWidget


STEPS = [
    (WorkflowStep.CONNECTION, "Verbindung & Setup", "Verbinde REW und konfiguriere Audio"),
    (WorkflowStep.ZONE_SETUP, "Zonen", "Definiere PA-Zonen und Kanaele"),
    (WorkflowStep.MEASUREMENT, "Messungen", "Fuehre Sweep-Messungen durch"),
    (WorkflowStep.ANALYSIS, "Analyse & EQ", "Alignment, EQ und Visualisierung"),
    (WorkflowStep.EXPORT, "Export", "PEQ, FIR, Delay und PDF-Report"),
]


class StepButton(QWidget):
    """Einzelner Schritt in der Sidebar mit Kreis-Indikator."""

    clicked = pyqtSignal()

    def __init__(self, index: int, label: str, subtitle: str, parent=None):
        super().__init__(parent)
        self._index = index
        self._label = label
        self._subtitle = subtitle
        self._active = False
        self._completed = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, val: bool):
        self._active = val
        self.update()

    @property
    def completed(self) -> bool:
        return self._completed

    @completed.setter
    def completed(self, val: bool):
        self._completed = val
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        circle_x = 20
        circle_y = h // 2
        circle_r = 14

        # Hover-Hintergrund
        if self.underMouse() or self._active:
            bg_color = QColor(C["bg_hover"]) if not self._active else QColor(C["accent_dark"])
            bg_color.setAlpha(60 if not self._active else 40)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(bg_color))
            p.drawRoundedRect(4, 2, w - 8, h - 4, 8, 8)

        # Verbindungslinie nach unten (falls nicht letzter Step)
        if self._index < len(STEPS) - 1:
            p.setPen(QPen(QColor(C["border"]), 2))
            p.drawLine(circle_x, circle_y + circle_r + 2, circle_x, h)

        # Verbindungslinie nach oben (falls nicht erster Step)
        if self._index > 0:
            p.setPen(QPen(QColor(C["border"]), 2))
            p.drawLine(circle_x, 0, circle_x, circle_y - circle_r - 2)

        # Kreis
        if self._active:
            p.setPen(QPen(QColor(C["accent"]), 2))
            p.setBrush(QBrush(QColor(C["accent_dark"])))
        elif self._completed:
            p.setPen(QPen(QColor(C["success"]), 2))
            p.setBrush(QBrush(QColor(C["success"])))
        else:
            p.setPen(QPen(QColor(C["border_light"]), 2))
            p.setBrush(QBrush(QColor(C["bg_dark"])))

        p.drawEllipse(circle_x - circle_r, circle_y - circle_r, circle_r * 2, circle_r * 2)

        # Nummer oder Haken im Kreis
        if self._completed and not self._active:
            p.setPen(QPen(QColor("white"), 2))
            p.drawLine(circle_x - 5, circle_y, circle_x - 1, circle_y + 4)
            p.drawLine(circle_x - 1, circle_y + 4, circle_x + 6, circle_y - 4)
        else:
            num_color = QColor("white") if self._active else QColor(C["text_secondary"])
            p.setPen(num_color)
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.drawText(circle_x - circle_r, circle_y - circle_r,
                       circle_r * 2, circle_r * 2,
                       Qt.AlignmentFlag.AlignCenter, str(self._index + 1))

        # Label
        text_x = circle_x + circle_r + 14
        label_color = QColor(C["text_primary"]) if self._active else QColor(C["text_secondary"])
        p.setPen(label_color)
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold if self._active else QFont.Weight.Normal))
        p.drawText(text_x, circle_y - 8, w - text_x - 8, 20,
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        # Subtitle
        if self._active:
            p.setPen(QColor(C["text_muted"]))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(text_x, circle_y + 8, w - text_x - 8, 16,
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._subtitle)

        p.end()


class StepIndicator(QWidget):
    """Sidebar mit Schritt-Anzeige."""

    step_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self._buttons: list[StepButton] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / Titel
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(20, 20, 16, 24)
        title_layout.setSpacing(4)

        title = QLabel("AutoREW")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C['accent']};")
        title_layout.addWidget(title)

        subtitle = QLabel("PA Einmessung")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet(f"color: {C['text_muted']};")
        title_layout.addWidget(subtitle)

        layout.addWidget(title_widget)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {C['border']}; max-height: 1px;")
        layout.addWidget(line)

        layout.addSpacing(12)

        for i, (step, label, desc) in enumerate(STEPS):
            btn = StepButton(i, label, desc)
            btn.clicked.connect(lambda idx=i: self.step_clicked.emit(idx))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Version + Demo-Label
        self._demo_label = QLabel("")
        self._demo_label.setStyleSheet(f"""
            color: {C['warning']};
            background: transparent;
            padding: 4px 20px 0px 20px;
            font-size: 11px;
            font-weight: bold;
        """)
        self._demo_label.setVisible(False)
        layout.addWidget(self._demo_label)

        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet(f"color: {C['text_muted']}; padding: 4px 20px 12px 20px; font-size: 11px;")
        layout.addWidget(version_label)

    def set_current(self, index: int):
        self._current = index
        for i, btn in enumerate(self._buttons):
            btn.active = i == index
            btn.completed = i < index


class MainWindow(QMainWindow):
    """Hauptfenster der Anwendung."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoREW - PA Einmessung")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 820)

        self.config = ProjectConfig()
        self.client = REWClient()
        self._demo_mode = False

        self._init_ui()
        self._goto_step(0)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_dark']};
                border-right: 1px solid {C['border']};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self._step_indicator = StepIndicator()
        self._step_indicator.step_clicked.connect(self._goto_step)
        sidebar_layout.addWidget(self._step_indicator)

        main_layout.addWidget(sidebar)

        # Content area
        content = QFrame()
        content.setStyleSheet(f"QFrame {{ background: {C['bg_surface']}; }}")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Stacked widget fuer Steps
        self._stack = QStackedWidget()
        self._pages: list[QWidget] = []

        self._connection_widget = ConnectionWidget(self.client, self.config)
        self._zone_widget = ZoneSetupWidget(self.client, self.config)
        self._measurement_widget = MeasurementWidget(self.client, self.config)
        self._analysis_widget = AnalysisWidget(self.client, self.config)
        self._export_widget = ExportWidget(self.client, self.config)

        for widget in [
            self._connection_widget,
            self._zone_widget,
            self._measurement_widget,
            self._analysis_widget,
            self._export_widget,
        ]:
            self._stack.addWidget(widget)
            self._pages.append(widget)

        content_layout.addWidget(self._stack, 1)

        # Navigation bar
        nav_bar = QFrame()
        nav_bar.setFixedHeight(64)
        nav_bar.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_dark']};
                border-top: 1px solid {C['border']};
            }}
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(24, 0, 24, 0)

        self._btn_back = QPushButton("Zurueck")
        self._btn_back.setFixedSize(120, 36)
        self._btn_back.setStyleSheet(btn_ghost())
        self._btn_back.clicked.connect(self._go_back)

        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_label.setStyleSheet(f"color: {C['text_muted']}; font-size: 12px;")

        self._btn_next = QPushButton("Weiter")
        self._btn_next.setFixedSize(120, 36)
        self._btn_next.setStyleSheet(btn_primary())
        self._btn_next.clicked.connect(self._go_next)

        nav_layout.addWidget(self._btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self._step_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self._btn_next)

        content_layout.addWidget(nav_bar)
        main_layout.addWidget(content, 1)

        # Global stylesheet
        self.setStyleSheet(global_stylesheet())

    def _goto_step(self, index: int):
        if 0 <= index < len(self._pages):
            self._stack.setCurrentIndex(index)
            self._step_indicator.set_current(index)
            step, label, _ = STEPS[index]
            self.config.current_step = step
            self._step_label.setText(f"Schritt {index + 1} von {len(STEPS)}")
            self._btn_back.setEnabled(index > 0)
            self._btn_next.setText("Fertig" if index == len(STEPS) - 1 else "Weiter")

            page = self._pages[index]
            if hasattr(page, "on_activated"):
                page.on_activated()

    def _go_back(self):
        current = self._stack.currentIndex()
        if current > 0:
            self._goto_step(current - 1)

    def _go_next(self):
        current = self._stack.currentIndex()
        if current < len(self._pages) - 1:
            self._goto_step(current + 1)

    def activate_demo_mode(self):
        """Wechselt in den Demo-Modus mit simulierten Daten."""
        if self._demo_mode:
            return
        self._demo_mode = True
        self.client.close()
        self.client = DemoClient()

        # Demo-Zonen vorbelegen (positions muss zu measurement_ids passen)
        self.config.zones = [
            Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1,
                 positions=2, measurement_ids=[0, 1]),
            Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2,
                 positions=2, measurement_ids=[2, 3]),
            Zone(name="Sub", zone_type=ZoneType.SUB, output_channel=3, is_sub=True,
                 crossover_freq=120.0, positions=1, measurement_ids=[4]),
        ]
        self.config.is_pro_license = True

        # Client in allen Widgets aktualisieren
        for page in self._pages:
            page.client = self.client

        # Demo-Label in Sidebar anzeigen
        self._step_indicator._demo_label.setText("DEMO MODUS")
        self._step_indicator._demo_label.setVisible(True)

        self.setWindowTitle("AutoREW - PA Einmessung [DEMO]")

    def deactivate_demo_mode(self):
        """Wechselt zurueck in den Live-Modus."""
        if not self._demo_mode:
            return
        self._demo_mode = False
        self.client = REWClient()

        for page in self._pages:
            page.client = self.client

        self._step_indicator._demo_label.setVisible(False)
        self.setWindowTitle("AutoREW - PA Einmessung")

    def closeEvent(self, event):
        self.client.close()
        super().closeEvent(event)
