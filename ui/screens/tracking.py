import os
import time
import json

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Slot, QTimer, QRect
from PySide6.QtGui import (
    QPainter, QColor, QPen, QPixmap,
    QShortcut, QKeySequence, QGuiApplication
)

from core.paths import resource_path, data_path
from logger import AOILogger


class TrackingScreen(QWidget):
    """Screen 4 — Fullscreen tracking with side-by-side images, gaze pointer, and AOI logging."""

    STATE_SHOWING_IMAGES = 0
    STATE_BLACK_BUFFER = 1
    STATE_DONE = 2

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self.setStyleSheet("background-color: #000000;")

        self.timer = None
        self.logger = None

        # Connect to engine
        self.win.engine.gaze_point.connect(self._on_gaze)

        # Display state
        self.pre_pixmap = None
        self.post_pixmap = None
        self.pre_region = QRect()
        self.post_region = QRect()
        self.display_region = {}

        # Pointer state
        self.pointer_x = None
        self.pointer_y = None
        self.show_pointer = False

        # Image cycling state
        self.state = self.STATE_DONE
        self.image_indices = []
        self.image_index = 0
        self.state_start_time = 0
        self.image_change_interval = 30  # seconds per image set
        self.buffer_interval = 5         # seconds black screen between sets

        # Screen dimensions
        self.screen_w = 1920
        self.screen_h = 1080

        # Session info
        self.group = ""
        self.session_name = ""
        self.scaled_aois = {}

        # Emergency exit
        shortcut = QShortcut(QKeySequence("Q"), self)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut.activated.connect(self._emergency_exit)

    def on_enter(self):
        """Set up and start the tracking session."""
        # Get screen dimensions
        screen = QGuiApplication.primaryScreen()
        rect = screen.geometry()
        self.screen_w = rect.width()
        self.screen_h = rect.height()

        # Read session state
        self.group = self.win.session_state.get('group', 'unknown')
        self.session_name = self.win.session_state.get('session_name', 'session')
        self.show_pointer = self.win.session_state.get('show_pointer', False)
        self.gaze_model = self.win.session_state.get('gaze_model')

        # Compute display regions (same as original)
        self._setup_display_regions()

        # Load AOI config
        self._load_aoi_config()

        # Get image indices
        self.image_indices = self._get_image_indices()
        if not self.image_indices:
            print("No image pairs found!")
            self.win.show_screen(0)
            return

        self.image_index = 0

        # Initialize pointer at center
        self.pointer_x = self.screen_w / 2
        self.pointer_y = self.screen_h / 2

        # Load first images and AOIs
        self._load_current_images()
        self._scale_aois_for_current_image()

        # Create AOI logger
        self.logger = AOILogger(
            self.scaled_aois, group=self.group,
            session_type=self.session_name, regions=["pre", "post"]
        )
        current_id = self.image_indices[self.image_index]
        self.logger.new_session(
            self.scaled_aois,
            session_name=f"{current_id}.png",
            image_id=current_id
        )

        # Start tracking mode on engine
        self.win.engine.start_tracking()

        # Start state timer
        self.state = self.STATE_SHOWING_IMAGES
        self.state_start_time = time.time()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(100)

    def on_exit(self):
        self._cleanup()

    def _cleanup(self):
        if self.timer:
            self.timer.stop()
            self.timer = None
        # Release camera when leaving tracking
        self.win.engine.release_camera()

    def _setup_display_regions(self):
        """Set up side-by-side display regions — identical to original."""
        margin_x = 0.04
        margin_top = 0.06
        gap = 0.02
        img_height_ratio = 0.85

        total_img_width = self.screen_w * (1 - 2 * margin_x - gap)
        each_img_width = int(total_img_width / 2)
        img_height = int(self.screen_h * img_height_ratio)

        x_start_left = int(margin_x * self.screen_w)
        y_top = int(margin_top * self.screen_h)

        self.pre_region = QRect(
            x_start_left, y_top,
            each_img_width, img_height
        )

        x_start_right = x_start_left + each_img_width + int(gap * self.screen_w)
        self.post_region = QRect(
            x_start_right, y_top,
            each_img_width, img_height
        )

        self.display_region = {
            "x_min": self.pre_region.x(),
            "x_max": self.post_region.x() + self.post_region.width(),
            "y_min": y_top,
            "y_max": y_top + img_height,
        }

    def _get_image_indices(self):
        pre_path = data_path("images/pre")
        post_path = data_path("images/post")
        os.makedirs(pre_path, exist_ok=True)
        os.makedirs(post_path, exist_ok=True)

        pre_images = {f.split('.')[0] for f in os.listdir(pre_path)
                      if f.lower().endswith('.png')}
        post_images = {f.split('.')[0] for f in os.listdir(post_path)
                       if f.lower().endswith('.png')}

        common = sorted(pre_images & post_images,
                        key=lambda x: int(x) if x.isdigit() else x)
        print(f"Found {len(common)} image sets")
        return common

    def _load_current_images(self):
        current_id = self.image_indices[self.image_index]
        pre_path = data_path(f"images/pre/{current_id}.png")
        post_path = data_path(f"images/post/{current_id}.png")

        if os.path.exists(pre_path):
            pix = QPixmap(pre_path)
            self.pre_pixmap = pix.scaled(
                self.pre_region.width(), self.pre_region.height(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self.pre_pixmap = None

        if os.path.exists(post_path):
            pix = QPixmap(post_path)
            self.post_pixmap = pix.scaled(
                self.post_region.width(), self.post_region.height(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            self.post_pixmap = None

    def _load_aoi_config(self):
        """Load the per-image AOI configuration."""
        self.all_aois = {}
        aoi_path = resource_path("aoi_config_per_image.json")
        if not os.path.exists(aoi_path):
            aoi_path = data_path("aoi_config_per_image.json")
        if os.path.exists(aoi_path):
            with open(aoi_path, "r") as f:
                self.all_aois = json.load(f)

    def _scale_aois_for_current_image(self):
        """Scale AOIs to screen coordinates — identical to original."""
        current_id = self.image_indices[self.image_index]
        img_aois = self.all_aois.get(str(current_id), {})

        self.scaled_aois = {}

        # Pre AOIs — scaled to left display region
        pre_dict = img_aois.get("pre", {})
        pre_x = self.pre_region.x()
        pre_y = self.pre_region.y()
        pre_w = self.pre_region.width()
        pre_h = self.pre_region.height()
        for name, (pt1, pt2) in pre_dict.items():
            rx1, ry1 = pt1
            rx2, ry2 = pt2
            x1 = int(pre_x + rx1 * pre_w)
            y1 = int(pre_y + ry1 * pre_h)
            x2 = int(pre_x + rx2 * pre_w)
            y2 = int(pre_y + ry2 * pre_h)
            self.scaled_aois[f"pre_{name}"] = ((x1, y1), (x2, y2))

        # Post AOIs — scaled to right display region
        post_dict = img_aois.get("post", {})
        post_x = self.post_region.x()
        post_y = self.post_region.y()
        post_w = self.post_region.width()
        post_h = self.post_region.height()
        for name, (pt1, pt2) in post_dict.items():
            rx1, ry1 = pt1
            rx2, ry2 = pt2
            x1 = int(post_x + rx1 * post_w)
            y1 = int(post_y + ry1 * post_h)
            x2 = int(post_x + rx2 * post_w)
            y2 = int(post_y + ry2 * post_h)
            self.scaled_aois[f"post_{name}"] = ((x1, y1), (x2, y2))

    @Slot(float, float, bool)
    def _on_gaze(self, norm_x: float, norm_y: float, is_blinking: bool):
        if not self.isVisible() or self.state != self.STATE_SHOWING_IMAGES:
            return

        screen_x = norm_x * self.screen_w
        screen_y = norm_y * self.screen_h

        # Smoothing (same as original)
        sf = 0.25
        if self.pointer_x is None:
            self.pointer_x = screen_x
            self.pointer_y = screen_y
        else:
            self.pointer_x = (1 - sf) * self.pointer_x + sf * screen_x
            self.pointer_y = (1 - sf) * self.pointer_y + sf * screen_y

        # Clamp
        self.pointer_x = max(0, min(self.screen_w, self.pointer_x))
        self.pointer_y = max(0, min(self.screen_h, self.pointer_y))

        # Log via AOILogger
        if self.logger:
            self.logger.update((self.pointer_x, self.pointer_y), is_blinking)

        # Repaint
        self.update()

    def _tick(self):
        elapsed = time.time() - self.state_start_time

        if self.state == self.STATE_SHOWING_IMAGES:
            if elapsed >= self.image_change_interval:
                self._end_image_session()

        elif self.state == self.STATE_BLACK_BUFFER:
            if elapsed >= self.buffer_interval:
                self._start_next_image()

    def _end_image_session(self):
        """Export current session and transition to buffer or completion."""
        if self.logger:
            self.logger.export()

        self.image_index += 1

        if self.image_index >= len(self.image_indices):
            self._finish_all()
            return

        # Enter black buffer
        self.state = self.STATE_BLACK_BUFFER
        self.state_start_time = time.time()
        self.pre_pixmap = None
        self.post_pixmap = None
        self.update()

    def _start_next_image(self):
        """Load next image pair and resume tracking."""
        self._load_current_images()
        self._scale_aois_for_current_image()

        current_id = self.image_indices[self.image_index]
        if self.logger:
            self.logger.new_session(
                self.scaled_aois,
                session_name=f"{current_id}.png",
                image_id=current_id
            )

        self.state = self.STATE_SHOWING_IMAGES
        self.state_start_time = time.time()
        self.update()

    def _finish_all(self):
        """Complete the entire tracking session."""
        self.state = self.STATE_DONE

        if self.timer:
            self.timer.stop()

        if self.logger:
            summary_filename = (
                f"{self.group}_{self.session_name}_"
                f"{self.logger.summary_report_time}.csv"
            )
            full_path = data_path(f"logs/{summary_filename}")
            self.logger.export_all_sessions(filename=full_path)
            self.win.session_state['result_filename'] = summary_filename

        # Release camera — tracking is done
        self.win.engine.release_camera()

        self.win.show_screen(5)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#000000"))

        # Draw pre image (left)
        if self.pre_pixmap:
            p.drawPixmap(self.pre_region.x(), self.pre_region.y(), self.pre_pixmap)

        # Draw post image (right)
        if self.post_pixmap:
            p.drawPixmap(self.post_region.x(), self.post_region.y(), self.post_pixmap)

        # Draw gaze pointer if enabled and position known
        if (self.show_pointer and self.pointer_x is not None
                and self.state == self.STATE_SHOWING_IMAGES):
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(180, 180, 180, 150))
            p.setPen(QPen(QColor(120, 120, 120), 2))
            p.drawEllipse(
                int(self.pointer_x) - 10, int(self.pointer_y) - 10,
                20, 20
            )

        p.end()

    def _emergency_exit(self):
        """Ctrl+Q — export partial data and exit."""
        if self.logger:
            try:
                self.logger.export()
                summary_filename = (
                    f"{self.group}_{self.session_name}_"
                    f"{self.logger.summary_report_time}.csv"
                )
                full_path = data_path(f"logs/{summary_filename}")
                self.logger.export_all_sessions(filename=full_path)
                self.win.session_state['result_filename'] = summary_filename
            except Exception as e:
                print(f"Error exporting on emergency exit: {e}")

        self._cleanup()
        self.win.show_screen(5)
