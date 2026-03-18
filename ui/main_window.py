from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

SCREEN_DASHBOARD = 0
SCREEN_GALLERY = 1
SCREEN_PREFLIGHT = 2
SCREEN_CALIBRATION = 3
SCREEN_TRACKING = 4
SCREEN_RESULTS = 5


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eye Tracker — Advanced Gaze Analysis")
        self.resize(1100, 800)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Session state shared between screens
        self.session_state = {
            'group': '',
            'session_name': '',
            'show_pointer': False,
            'calibration_points': [],
            'screen_points': [],
            'gaze_model': None,
            'result_filename': None,
        }

        # Import and Start Unified Engine Thread
        from ui.threads.engine_thread import EngineThread
        self.engine = EngineThread()
        self.engine.start()

        # Import screens here to avoid circular imports
        from ui.screens.dashboard import DashboardScreen
        from ui.screens.gallery import GalleryScreen
        from ui.screens.preflight import PreflightScreen
        from ui.screens.calibration import CalibrationScreen
        from ui.screens.tracking import TrackingScreen
        from ui.screens.results import ResultsScreen

        # Instantiate all screens
        self.dashboard = DashboardScreen(self)
        self.gallery = GalleryScreen(self)
        self.preflight = PreflightScreen(self)
        self.calibration = CalibrationScreen(self)
        self.tracking = TrackingScreen(self)
        self.results = ResultsScreen(self)

        for screen in [self.dashboard, self.gallery, self.preflight,
                        self.calibration, self.tracking, self.results]:
            self.stack.addWidget(screen)

        self._apply_drop_shadows()
        self.show_screen(SCREEN_DASHBOARD)

    def _apply_drop_shadows(self):
        from PySide6.QtWidgets import QFrame
        for frame in self.findChildren(QFrame):
            if frame.objectName() == "card":
                self.apply_shadow(frame)
                
    def apply_shadow(self, widget):
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(30)
        effect.setColor(QColor(0, 0, 0, 180))
        effect.setOffset(0, 12)
        widget.setGraphicsEffect(effect)

    def show_screen(self, index: int):
        """Navigate to a screen by index. Handles fullscreen toggling."""
        # Notify outgoing screen
        current = self.stack.currentWidget()
        if current and hasattr(current, 'on_exit'):
            current.on_exit()

        self.stack.setCurrentIndex(index)
        screen = self.stack.currentWidget()
        if hasattr(screen, 'on_enter'):
            screen.on_enter()

        # Fullscreen for calibration and tracking, normal for others
        if index in (SCREEN_CALIBRATION, SCREEN_TRACKING):
            self.showFullScreen()
        else:
            if self.isFullScreen():
                self.showNormal()
                self.resize(1100, 800)

    def closeEvent(self, event):
        """Ensure all background threads stop safely when closing the app."""
        current = self.stack.currentWidget()
        if current and hasattr(current, 'on_exit'):
            current.on_exit()
        
        if hasattr(self, 'engine') and self.engine and self.engine.isRunning():
            self.engine.stop()
            
        super().closeEvent(event)
