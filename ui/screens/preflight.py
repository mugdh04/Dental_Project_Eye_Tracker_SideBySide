from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap, QImage
import os
from core.paths import resource_path, data_path


class PreflightScreen(QWidget):
    """Screen 2 — Pre-flight system checks with live camera preview."""

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self._checks_passed = False
        self._build_ui()
        
        # Connect to unified engine
        self.win.engine.camera_ok.connect(self._on_camera_status)
        self.win.engine.frame_ready.connect(self._update_preview)

    def on_enter(self):
        self._run_checks()
        self.win.engine.start_preview()

    def on_exit(self):
        pass

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(60, 30, 60, 30)
        vbox.setSpacing(20)

        # Top bar
        top_h = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setObjectName("secondaryBtn")
        btn_back.clicked.connect(lambda: self.win.show_screen(0))
        top_h.addWidget(btn_back)
        top_h.addStretch()
        title = QLabel("Pre-Flight Check")
        title.setObjectName("heading")
        top_h.addWidget(title)
        top_h.addStretch()
        vbox.addLayout(top_h)

        # ---- System Checks Card ----
        checks_card = QFrame()
        checks_card.setObjectName("card")
        checks_layout = QVBoxLayout(checks_card)
        checks_title = QLabel("System Checks")
        checks_title.setObjectName("sectionTitle")
        checks_layout.addWidget(checks_title)

        self.camera_status = QLabel("📷 Camera: Checking...")
        self.images_status = QLabel("🖼 Image Sets: Checking...")
        self.model_status = QLabel("🧠 Model: Checking...")
        for lbl in [self.camera_status, self.images_status, self.model_status]:
            checks_layout.addWidget(lbl)
        vbox.addWidget(checks_card)

        # ---- Camera Preview Card ----
        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_title = QLabel("Camera Preview")
        preview_title.setObjectName("sectionTitle")
        preview_layout.addWidget(preview_title)

        self.preview_label = QLabel("Waiting for camera...")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(480, 320)
        self.preview_label.setStyleSheet(
            "background-color: rgba(0,0,0,0.5); border-radius: 8px;"
        )
        preview_layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(preview_card)

        # ---- Options Card ----
        options_card = QFrame()
        options_card.setObjectName("card")
        opts_layout = QVBoxLayout(options_card)
        self.pointer_check = QCheckBox("Show gaze pointer on screen")
        opts_layout.addWidget(self.pointer_check)
        vbox.addWidget(options_card)

        # ---- Instructions Card ----
        instr_card = QFrame()
        instr_card.setObjectName("card")
        instr_layout = QVBoxLayout(instr_card)
        instr_title = QLabel("📋 Important Instructions")
        instr_title.setObjectName("sectionTitle")
        instr_layout.addWidget(instr_title)

        instructions = [
            "1. <b>Calibration is critical.</b> Follow each green dot naturally with your "
            "eyes — move your head and eyes as you normally would. Stay relaxed and "
            "keep a comfortable distance from the screen.",
            "2. <b>During the gazing process,</b> do not look away from the screen. "
            "Looking elsewhere will reduce accuracy and the session may need to "
            "be restarted from the beginning.",
            "3. <b>To stop at any time,</b> press <code style='background:#333;padding:2px 6px;"
            "border-radius:4px;color:#00adb5;'>Q</code> on your keyboard. "
            "Your partial data will be saved automatically.",
        ]
        for text in instructions:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setStyleSheet("padding: 4px 0; font-size: 13px; line-height: 1.5;")
            instr_layout.addWidget(lbl)
        vbox.addWidget(instr_card)

        # ---- Start Button ----
        self.btn_start = QPushButton("Start Calibration & Tracking")
        self.btn_start.setEnabled(False)
        self.btn_start.setMinimumHeight(48)
        self.btn_start.clicked.connect(self._on_start)
        vbox.addWidget(self.btn_start)

        vbox.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    def _run_checks(self):
        checks_ok = True

        # Check images
        pre_dir = data_path("images/pre")
        post_dir = data_path("images/post")
        pre_files = set()
        post_files = set()
        if os.path.exists(pre_dir):
            pre_files = {f.split('.')[0] for f in os.listdir(pre_dir)
                         if f.lower().endswith('.png')}
        if os.path.exists(post_dir):
            post_files = {f.split('.')[0] for f in os.listdir(post_dir)
                          if f.lower().endswith('.png')}
        common = pre_files & post_files
        if common:
            self.images_status.setText(f"🖼 Image Sets: ✅ {len(common)} matched pairs")
        else:
            self.images_status.setText("🖼 Image Sets: ❌ No matching pairs found")
            checks_ok = False

        # Check model
        model_bundled = resource_path("models/face_landmarker.task")
        model_data = data_path("models/face_landmarker.task")
        if os.path.exists(model_bundled) or os.path.exists(model_data):
            self.model_status.setText("🧠 Model: ✅ Found")
        else:
            self.model_status.setText("🧠 Model: ⚠ Will download on first run")
            # Still allow start — model will be downloaded by GazeEstimator

        self._images_ok = len(common) > 0
        self._update_start_button()

    @Slot(bool)
    def _on_camera_status(self, ok: bool):
        if ok:
            self.camera_status.setText("📷 Camera: ✅ Connected")
            self._camera_ok = True
        else:
            self.camera_status.setText("📷 Camera: ❌ Not detected")
            self._camera_ok = False
        self._update_start_button()

    @Slot(QImage)
    def _update_preview(self, img: QImage):
        if not self.isVisible():
            return
        self.preview_label.setPixmap(
            QPixmap.fromImage(img).scaled(
                480, 320,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def _update_start_button(self):
        camera_ok = getattr(self, '_camera_ok', False)
        images_ok = getattr(self, '_images_ok', False)
        self.btn_start.setEnabled(camera_ok and images_ok)

    def _on_start(self):
        self.win.session_state['show_pointer'] = self.pointer_check.isChecked()
        self.win.show_screen(3)

    def hideEvent(self, event):
        super().hideEvent(event)
