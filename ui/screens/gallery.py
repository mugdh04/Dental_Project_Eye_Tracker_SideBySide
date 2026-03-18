from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import os
from core.paths import data_path


class GalleryScreen(QWidget):
    """Screen 1 — Scrollable pre/post image pair viewer."""

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self._build_ui()

    def on_enter(self):
        self._load_images()

    def on_exit(self):
        pass

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(20, 15, 20, 10)
        btn_back = QPushButton("← Back to Dashboard")
        btn_back.setObjectName("secondaryBtn")
        btn_back.clicked.connect(lambda: self.win.show_screen(0))
        top_bar.addWidget(btn_back)
        top_bar.addStretch()
        title = QLabel("Image Gallery")
        title.setObjectName("heading")
        top_bar.addWidget(title)
        top_bar.addStretch()
        outer.addLayout(top_bar)

        # Scroll area for image pairs
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_inner = QWidget()
        self.images_layout = QVBoxLayout(self.scroll_inner)
        self.images_layout.setContentsMargins(40, 10, 40, 40)
        self.images_layout.setSpacing(20)
        self.scroll.setWidget(self.scroll_inner)
        outer.addWidget(self.scroll)

    def _load_images(self):
        # Clear existing
        while self.images_layout.count():
            child = self.images_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        pre_dir = data_path("images/pre")
        post_dir = data_path("images/post")

        if not os.path.exists(pre_dir) or not os.path.exists(post_dir):
            self.images_layout.addWidget(QLabel("No images found."))
            return

        pre_files = {f.split('.')[0] for f in os.listdir(pre_dir)
                     if f.lower().endswith('.png')}
        post_files = {f.split('.')[0] for f in os.listdir(post_dir)
                      if f.lower().endswith('.png')}
        common = sorted(pre_files & post_files, key=lambda x: int(x) if x.isdigit() else x)

        if not common:
            self.images_layout.addWidget(QLabel("No matching image pairs found."))
            return

        for img_id in common:
            card = QFrame()
            card.setObjectName("card")
            self.win.apply_shadow(card)
            card_layout = QVBoxLayout(card)

            header = QLabel(f"Image Set #{img_id}")
            header.setObjectName("sectionTitle")
            card_layout.addWidget(header)

            pair_layout = QHBoxLayout()

            # Pre image
            pre_col = QVBoxLayout()
            pre_col.addWidget(QLabel("Pre Treatment"))
            pre_lbl = QLabel()
            pre_path = os.path.join(pre_dir, f"{img_id}.png")
            if os.path.exists(pre_path):
                pix = QPixmap(pre_path)
                pre_lbl.setPixmap(pix.scaled(
                    400, 400,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            pre_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pre_col.addWidget(pre_lbl)
            pair_layout.addLayout(pre_col)

            # Post image
            post_col = QVBoxLayout()
            post_col.addWidget(QLabel("Post Treatment"))
            post_lbl = QLabel()
            post_path = os.path.join(post_dir, f"{img_id}.png")
            if os.path.exists(post_path):
                pix = QPixmap(post_path)
                post_lbl.setPixmap(pix.scaled(
                    400, 400,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            post_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            post_col.addWidget(post_lbl)
            pair_layout.addLayout(post_col)

            card_layout.addLayout(pair_layout)
            self.images_layout.addWidget(card)

        self.images_layout.addStretch()
