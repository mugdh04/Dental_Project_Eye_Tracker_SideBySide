from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt
import os
from core.paths import data_path


class DashboardScreen(QWidget):
    """Screen 0 — Main dashboard with session config and previous results."""

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self._build_ui()

    def on_enter(self):
        self._refresh_status()
        self._refresh_results()

    def on_exit(self):
        pass

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(60, 40, 60, 40)
        vbox.setSpacing(20)

        # ---- Header ----
        title = QLabel("\U0001F441 Eye Tracker")
        title.setObjectName("heading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Advanced Gaze Analysis System")
        sub.setObjectName("subheading")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(title)
        vbox.addWidget(sub)

        # ---- Status Card ----
        self.status_card = QFrame()
        self.status_card.setObjectName("card")
        status_layout = QVBoxLayout(self.status_card)
        status_title = QLabel("Image Status")
        status_title.setObjectName("sectionTitle")
        status_layout.addWidget(status_title)

        status_h = QHBoxLayout()
        self.pre_label = QLabel("Pre Images: —")
        self.post_label = QLabel("Post Images: —")
        self.ready_label = QLabel("Status: —")
        for lbl in [self.pre_label, self.post_label, self.ready_label]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_h.addWidget(lbl)
        status_layout.addLayout(status_h)

        btn_view = QPushButton("View Images")
        btn_view.setObjectName("secondaryBtn")
        btn_view.clicked.connect(lambda: self.win.show_screen(1))
        status_layout.addWidget(btn_view, alignment=Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(self.status_card)

        # ---- Session Config Card ----
        session_card = QFrame()
        session_card.setObjectName("card")
        sess_layout = QVBoxLayout(session_card)
        sess_title = QLabel("Start Eye Tracking")
        sess_title.setObjectName("sectionTitle")
        sess_layout.addWidget(sess_title)

        sess_layout.addWidget(QLabel("Select Group"))
        self.group_combo = QComboBox()
        self.group_combo.addItems(
            ["-- Select Group --", "Orthodontist", "Dentist", "Layperson"]
        )
        self.group_combo.setEditable(True)
        sess_layout.addWidget(self.group_combo)

        sess_layout.addWidget(QLabel("Session Name"))
        self.session_edit = QLineEdit()
        self.session_edit.setPlaceholderText("Enter session name")
        sess_layout.addWidget(self.session_edit)

        self.btn_continue = QPushButton("Continue to Pre-flight Check")
        self.btn_continue.clicked.connect(self._on_continue)
        sess_layout.addWidget(self.btn_continue)
        vbox.addWidget(session_card)

        # ---- Previous Results Card ----
        results_card = QFrame()
        results_card.setObjectName("card")
        res_layout = QVBoxLayout(results_card)
        res_title = QLabel("Previous Results")
        res_title.setObjectName("sectionTitle")
        res_layout.addWidget(res_title)

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(200)
        self.results_list.itemDoubleClicked.connect(self._open_result)
        res_layout.addWidget(self.results_list)
        vbox.addWidget(results_card)

        # ---- Data Folder Info ----
        import platform
        if platform.system() == 'Darwin' and getattr(__import__('sys'), 'frozen', False):
            folder_card = QFrame()
            folder_card.setObjectName("card")
            folder_layout = QVBoxLayout(folder_card)
            folder_layout.addWidget(QLabel(
                f"Data folder: {data_path('')}"
            ))
            btn_open = QPushButton("Open Data Folder")
            btn_open.setObjectName("secondaryBtn")
            btn_open.clicked.connect(self._open_data_folder)
            folder_layout.addWidget(btn_open)
            vbox.addWidget(folder_card)

        vbox.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _refresh_status(self):
        pre_dir = data_path("images/pre")
        post_dir = data_path("images/post")
        pre_count = len([f for f in os.listdir(pre_dir)
                         if f.lower().endswith('.png')]) if os.path.exists(pre_dir) else 0
        post_count = len([f for f in os.listdir(post_dir)
                          if f.lower().endswith('.png')]) if os.path.exists(post_dir) else 0
        self.pre_label.setText(f"Pre Images: {pre_count}")
        self.post_label.setText(f"Post Images: {post_count}")
        ready = pre_count > 0 and pre_count == post_count
        self.ready_label.setText(f"Status: {'✅ Ready' if ready else '⚠ Not ready'}")
        self.btn_continue.setEnabled(ready)

    def _refresh_results(self):
        self.results_list.clear()
        logs_dir = data_path("logs")
        if not os.path.exists(logs_dir):
            return
        files = sorted(
            [f for f in os.listdir(logs_dir) if f.endswith('.csv')],
            key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)),
            reverse=True
        )
        for f in files:
            item = QListWidgetItem(f)
            item.setData(Qt.ItemDataRole.UserRole, f)
            self.results_list.addItem(item)

    def _on_continue(self):
        group = self.group_combo.currentText().strip()
        session = self.session_edit.text().strip()
        if not group or group == "-- Select Group --" or not session:
            return
        self.win.session_state['group'] = group.lower().replace(' ', '_')
        self.win.session_state['session_name'] = session.lower().replace(' ', '_')
        self.win.show_screen(2)

    def _open_result(self, item):
        self.win.session_state['result_filename'] = item.data(Qt.ItemDataRole.UserRole)
        self.win.show_screen(5)

    def _open_data_folder(self):
        import subprocess
        subprocess.Popen(['open', data_path('')])
