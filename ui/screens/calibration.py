from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QShortcut, QKeySequence, QGuiApplication
)
import numpy as np


class CalibrationScreen(QWidget):
    """Screen 3 — Fullscreen 12-point calibration using QPainter dots."""

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self.setStyleSheet("background-color: #000000;")
        self.current_dot_pos = None
        self.screen_points = []
        self.calibration_points = []
        self.current_point_idx = 0

        # Emergency exit shortcut
        shortcut = QShortcut(QKeySequence("Q"), self)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(self._emergency_exit)
        
        # Connect to engine
        self.win.engine.calibration_sample.connect(self._on_sample_collected)

    def on_enter(self):
        """Initialize calibration on screen entry."""
        # Get screen dimensions
        screen = QGuiApplication.primaryScreen()
        rect = screen.geometry()
        self.screen_w = rect.width()
        self.screen_h = rect.height()

        # Build 12-point calibration grid (same as original)
        self._build_screen_points()

        # Reset state
        self.calibration_points = []
        self.current_point_idx = 0

        # Start calibration mode on engine
        self.win.engine.start_calibration(self.screen_w, self.screen_h)

        # Show first dot after a brief delay for the thread to open camera
        QTimer.singleShot(500, self._show_next_point)

    def on_exit(self):
        self.current_dot_pos = None

    def _build_screen_points(self):
        """Build the 4x3 calibration grid, matching the original layout."""
        margin_x = 0.04
        margin_top = 0.06
        gap = 0.02
        img_height_ratio = 0.85

        total_img_width = self.screen_w * (1 - 2 * margin_x - gap)
        each_img_width = int(total_img_width / 2)
        img_height = int(self.screen_h * img_height_ratio)

        x_start_left = int(margin_x * self.screen_w)
        y_top = int(margin_top * self.screen_h)

        # Pre region (left)
        pre_x_max = x_start_left + each_img_width

        # Post region (right)
        x_start_right = x_start_left + each_img_width + int(gap * self.screen_w)
        post_x_max = x_start_right + each_img_width

        # Combined display region
        display_x_min = x_start_left
        display_x_max = post_x_max
        display_y_min = y_top
        display_y_max = y_top + img_height

        x_positions = [
            display_x_min,
            pre_x_max,
            x_start_right,
            display_x_max,
        ]
        y_positions = [
            display_y_min,
            (display_y_min + display_y_max) // 2,
            display_y_max,
        ]

        self.screen_points = []
        for y in y_positions:
            for x in x_positions:
                self.screen_points.append((x, y))

    def _show_next_point(self):
        if self.current_point_idx >= len(self.screen_points):
            self._complete_calibration()
            return

        x, y = self.screen_points[self.current_point_idx]
        self.current_dot_pos = (x, y)
        self.update()

        # Start collecting samples after a brief pause for user to look at dot
        QTimer.singleShot(300, self._begin_sample)

    def _begin_sample(self):
        self.win.engine.start_collecting_sample(2.0)

    @Slot(object)
    def _on_sample_collected(self, median_pt):
        if not self.isVisible():
            return
        if median_pt is not None:
            self.calibration_points.append(median_pt)
        self.current_point_idx += 1
        self.current_dot_pos = None
        self.update()
        # Small delay between points
        QTimer.singleShot(200, self._show_next_point)

    def _complete_calibration(self):
        """Calibrate the gaze model and transition to tracking."""
        if len(self.calibration_points) >= 4:
            normalized_screen_points = [
                (x / self.screen_w, y / self.screen_h)
                for x, y in self.screen_points[:len(self.calibration_points)]
            ]
            self.win.engine.set_calibrated_points(self.calibration_points, normalized_screen_points)
            print("Calibration completed!")
        else:
            print(f"Warning: Only {len(self.calibration_points)} calibration points collected")

        self.current_dot_pos = None
        self.win.show_screen(4)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#000000"))

        if self.current_dot_pos is not None:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor("#00C853"))
            p.setPen(Qt.PenStyle.NoPen)
            x, y = self.current_dot_pos
            p.drawEllipse(int(x) - 15, int(y) - 15, 30, 30)

            # Draw smaller inner dot for precision
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)

        p.end()

    def _emergency_exit(self):
        QApplication.quit()
