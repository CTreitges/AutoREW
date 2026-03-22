"""Zentrales Styling fuer AutoREW UI."""

# Farbpalette
COLORS = {
    "bg_dark": "#0d1117",
    "bg_surface": "#161b22",
    "bg_card": "#1c2333",
    "bg_input": "#0d1117",
    "bg_hover": "#1f2937",
    "accent": "#58a6ff",
    "accent_hover": "#79c0ff",
    "accent_dark": "#1f6feb",
    "success": "#3fb950",
    "success_hover": "#2ea043",
    "danger": "#f85149",
    "danger_hover": "#da3633",
    "warning": "#d29922",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#484f58",
    "border": "#30363d",
    "border_light": "#3d444d",
    "border_accent": "#1f6feb",
}

C = COLORS


def global_stylesheet() -> str:
    return f"""
        /* === Base === */
        QMainWindow {{
            background: {C['bg_surface']};
        }}

        QWidget {{
            font-family: 'Segoe UI', sans-serif;
        }}

        QLabel {{
            color: {C['text_primary']};
            background: transparent;
        }}

        /* === Scrollbars === */
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {C['bg_dark']};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {C['border']};
            min-height: 40px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {C['border_light']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            height: 0px;
        }}

        /* === GroupBox === */
        QGroupBox {{
            color: {C['text_primary']};
            background: {C['bg_card']};
            border: 1px solid {C['border']};
            border-radius: 10px;
            margin-top: 20px;
            padding: 20px 16px 16px 16px;
            font-size: 13px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 12px;
            left: 12px;
            color: {C['text_primary']};
        }}

        /* === Inputs === */
        QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
            background: {C['bg_input']};
            color: {C['text_primary']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            padding: 7px 10px;
            min-height: 20px;
            selection-background-color: {C['accent_dark']};
        }}
        QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
            border-color: {C['border_light']};
        }}
        QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
            border-color: {C['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {C['text_secondary']};
            margin-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background: {C['bg_card']};
            color: {C['text_primary']};
            border: 1px solid {C['border']};
            selection-background-color: {C['accent_dark']};
            outline: none;
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background: {C['bg_card']};
            border: none;
            border-left: 1px solid {C['border']};
            width: 20px;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background: {C['bg_hover']};
        }}

        /* === Buttons === */
        QPushButton {{
            background: {C['bg_card']};
            color: {C['text_primary']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            padding: 7px 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background: {C['bg_hover']};
            border-color: {C['border_light']};
        }}
        QPushButton:pressed {{
            background: {C['bg_dark']};
        }}
        QPushButton:disabled {{
            background: {C['bg_dark']};
            color: {C['text_muted']};
            border-color: {C['border']};
        }}

        /* === Tables === */
        QTableWidget {{
            background: {C['bg_dark']};
            color: {C['text_primary']};
            gridline-color: {C['border']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            selection-background-color: {C['accent_dark']};
        }}
        QTableWidget::item {{
            padding: 6px 8px;
            border-bottom: 1px solid {C['border']};
        }}
        QTableWidget::item:selected {{
            background: {C['accent_dark']};
        }}
        QHeaderView::section {{
            background: {C['bg_card']};
            color: {C['text_secondary']};
            border: none;
            border-bottom: 2px solid {C['border']};
            border-right: 1px solid {C['border']};
            padding: 8px 8px;
            font-weight: bold;
            font-size: 12px;
            text-transform: uppercase;
        }}

        /* === Lists === */
        QListWidget {{
            background: {C['bg_dark']};
            color: {C['text_primary']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {C['border']};
        }}
        QListWidget::item:selected {{
            background: {C['accent_dark']};
        }}
        QListWidget::item:hover {{
            background: {C['bg_hover']};
        }}

        /* === TextEdit === */
        QTextEdit {{
            background: {C['bg_dark']};
            color: {C['text_primary']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            padding: 8px;
            font-family: 'Cascadia Code', 'Consolas', monospace;
            font-size: 12px;
            selection-background-color: {C['accent_dark']};
        }}

        /* === ProgressBar === */
        QProgressBar {{
            background: {C['bg_dark']};
            border: none;
            border-radius: 4px;
            text-align: center;
            color: {C['text_secondary']};
            font-size: 11px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C['accent_dark']}, stop:1 {C['accent']});
            border-radius: 4px;
        }}

        /* === CheckBox === */
        QCheckBox {{
            color: {C['text_primary']};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid {C['border']};
            background: {C['bg_input']};
        }}
        QCheckBox::indicator:checked {{
            background: {C['accent_dark']};
            border-color: {C['accent']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {C['border_light']};
        }}

        /* === Splitter === */
        QSplitter::handle {{
            background: {C['border']};
            height: 2px;
        }}
        QSplitter::handle:hover {{
            background: {C['accent']};
        }}

        /* === FormLayout Labels === */
        QFormLayout {{
            spacing: 8px;
        }}

        /* === Tooltip === */
        QToolTip {{
            background: {C['bg_card']};
            color: {C['text_primary']};
            border: 1px solid {C['border']};
            border-radius: 4px;
            padding: 6px 8px;
        }}
    """


def btn_primary() -> str:
    return f"""
        QPushButton {{
            background: {C['accent_dark']};
            color: white;
            border: 1px solid {C['accent']};
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {C['accent']};
            border-color: {C['accent_hover']};
        }}
        QPushButton:pressed {{
            background: {C['accent_dark']};
        }}
        QPushButton:disabled {{
            background: {C['bg_dark']};
            color: {C['text_muted']};
            border-color: {C['border']};
        }}
    """


def btn_success() -> str:
    return f"""
        QPushButton {{
            background: {C['success']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {C['success_hover']};
        }}
        QPushButton:disabled {{
            background: {C['bg_dark']};
            color: {C['text_muted']};
        }}
    """


def btn_danger() -> str:
    return f"""
        QPushButton {{
            background: transparent;
            color: {C['danger']};
            border: 1px solid {C['danger']};
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: {C['danger']};
            color: white;
        }}
        QPushButton:disabled {{
            background: transparent;
            color: {C['text_muted']};
            border-color: {C['border']};
        }}
    """


def btn_ghost() -> str:
    return f"""
        QPushButton {{
            background: transparent;
            color: {C['text_secondary']};
            border: 1px solid {C['border']};
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: {C['bg_hover']};
            color: {C['text_primary']};
            border-color: {C['border_light']};
        }}
        QPushButton:disabled {{
            color: {C['text_muted']};
            border-color: {C['border']};
        }}
    """


def card_info() -> str:
    return f"""
        QLabel {{
            background: {C['bg_card']};
            border: 1px solid {C['border']};
            border-left: 3px solid {C['accent']};
            border-radius: 8px;
            padding: 16px;
            color: {C['text_primary']};
            font-size: 13px;
            line-height: 1.5;
        }}
    """
