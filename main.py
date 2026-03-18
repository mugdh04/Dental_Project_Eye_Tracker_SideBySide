import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from core.paths import ensure_data_dirs, resource_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("EyeTracker")
    app.setOrganizationName("EyeTracker")

    # Load stylesheet
    qss_path = resource_path("ui/style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, 'r') as f:
            app.setStyleSheet(f.read())

    # Ensure writable directories exist
    ensure_data_dirs()

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()