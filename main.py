"""AutoREW - PA-Einmessungstool mit REW API."""

import sys

from PyQt6.QtWidgets import QApplication

from autorew.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AutoREW")
    app.setOrganizationName("AutoREW")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
