import os
import csv
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt
from core.paths import data_path


def parse_results_csv(filepath):
    """
    Parse CSV results from AOILogger.
    Handles both the new side-by-side format and the legacy sequential format.
    Returns (sessions, summary_stats).
    """
    sessions = []
    current_session = None
    summary_stats = {}
    reading_mode = None  # None, 'pre_table', 'post_table', 'side_by_side_table'

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or not row[0]:
                reading_mode = None
                continue

            if row[0].startswith('Session -'):
                if current_session:
                    sessions.append(current_session)
                current_session = {
                    'name': row[0].replace('Session - ', '').replace(':', '').strip(),
                    'pre_aois': [],
                    'post_aois': [],
                    'pre_first_focused': 'None',
                    'pre_most_focused': 'None',
                    'post_first_focused': 'None',
                    'post_most_focused': 'None',
                }
                reading_mode = None
                
            elif row[0] == 'Pre Treatment Image Report:' and len(row) > 5 and row[5] == 'Post Treatment Image Report:':
                reading_mode = 'side_by_side_table'
            elif row[0] == 'Pre Treatment Image Report:':
                reading_mode = 'pre_table'
            elif row[0] == 'Post Treatment Image Report:':
                reading_mode = 'post_table'
                
            elif row[0] == 'AOI' and current_session:
                continue  # Skip header row
                
            elif row[0] == 'First Focused AOI' and current_session:
                reading_mode = None
                current_session['pre_first_focused'] = row[1] if len(row) > 1 else 'None'
                if len(row) > 6 and row[5] == 'First Focused AOI':
                    current_session['post_first_focused'] = row[6] if row[6] else 'None'
                    
            elif row[0] == 'Most Focused AOI' and current_session:
                current_session['pre_most_focused'] = row[1] if len(row) > 1 else 'None'
                if len(row) > 6 and row[5] == 'Most Focused AOI':
                    current_session['post_most_focused'] = row[6] if row[6] else 'None'
                    
            elif row[0] == 'Total Blinks':
                summary_stats['total_blinks'] = row[1] if len(row) > 1 else '0'
            elif row[0] == 'Blink Rate (blinks/min)':
                summary_stats['blink_rate'] = row[1] if len(row) > 1 else '0'
                
            elif reading_mode and current_session and len(row) >= 4:
                try:
                    name = row[0]
                    first = float(row[1])
                    total = float(row[2])
                    blinks = int(row[3])
                    
                    if reading_mode in ('pre_table', 'side_by_side_table') and name:
                        current_session['pre_aois'].append({
                            'name': name, 'first_fixation': first,
                            'total_fixation': total, 'blinks': blinks
                        })
                        
                    if reading_mode == 'side_by_side_table' and len(row) >= 9 and row[5]:
                        current_session['post_aois'].append({
                            'name': row[5], 'first_fixation': float(row[6]),
                            'total_fixation': float(row[7]), 'blinks': int(row[8])
                        })
                        
                    if reading_mode == 'post_table' and name:
                         current_session['post_aois'].append({
                            'name': name, 'first_fixation': first,
                            'total_fixation': total, 'blinks': blinks
                        })
                except Exception:
                    pass

    if current_session:
        sessions.append(current_session)

    return sessions, summary_stats


class ResultsScreen(QWidget):
    """Screen 5 — Displays parsed CSV results with tables per session."""

    def __init__(self, main_window):
        super().__init__()
        self.win = main_window
        self._current_filepath = None
        self._build_ui()

    def on_enter(self):
        filename = self.win.session_state.get('result_filename')
        if filename:
            filepath = data_path(f"logs/{filename}")
            if os.path.exists(filepath):
                self._current_filepath = filepath
                self._display_results(filepath)
            else:
                self._show_error(f"File not found: {filename}")
        else:
            self._show_error("No result file specified.")

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
        title = QLabel("Results")
        title.setObjectName("heading")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.btn_download = QPushButton("Download CSV")
        self.btn_download.clicked.connect(self._download_csv)
        top_bar.addWidget(self.btn_download)
        outer.addLayout(top_bar)

        # Scroll area for results
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_inner = QWidget()
        self.results_layout = QVBoxLayout(self.scroll_inner)
        self.results_layout.setContentsMargins(40, 10, 40, 40)
        self.results_layout.setSpacing(20)
        self.scroll.setWidget(self.scroll_inner)
        outer.addWidget(self.scroll)

    def _clear_results(self):
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _show_error(self, message):
        self._clear_results()
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_layout.addWidget(lbl)

    def _display_results(self, filepath):
        self._clear_results()

        sessions, summary = parse_results_csv(filepath)

        if not sessions:
            self._show_error("No session data found in file.")
            return

        # Summary card
        if summary:
            summary_card = QFrame()
            summary_card.setObjectName("card")
            s_layout = QVBoxLayout(summary_card)
            s_title = QLabel("Overall Summary")
            s_title.setObjectName("sectionTitle")
            s_layout.addWidget(s_title)
            blinks = summary.get('total_blinks', '0')
            rate = summary.get('blink_rate', '0')
            s_layout.addWidget(QLabel(f"Total Blinks: {blinks}"))
            s_layout.addWidget(QLabel(f"Blink Rate: {rate} blinks/min"))
            self.results_layout.addWidget(summary_card)

        # Session cards
        for session in sessions:
            card = QFrame()
            card.setObjectName("card")
            self.win.apply_shadow(card)
            card_layout = QVBoxLayout(card)

            header = QLabel(f"Session: {session['name']}")
            header.setObjectName("sectionTitle")
            card_layout.addWidget(header)

            # Side by side: Pre | Post
            pair_h = QHBoxLayout()

            # Pre table
            pre_col = QVBoxLayout()
            pre_col.addWidget(QLabel("Pre Treatment"))
            pre_table = self._build_aoi_table(session['pre_aois'])
            pre_col.addWidget(pre_table)
            pre_col.addWidget(QLabel(
                f"First Focused: {session['pre_first_focused']}  |  "
                f"Most Focused: {session['pre_most_focused']}"
            ))
            pair_h.addLayout(pre_col)

            # Post table
            post_col = QVBoxLayout()
            post_col.addWidget(QLabel("Post Treatment"))
            post_table = self._build_aoi_table(session['post_aois'])
            post_col.addWidget(post_table)
            post_col.addWidget(QLabel(
                f"First Focused: {session['post_first_focused']}  |  "
                f"Most Focused: {session['post_most_focused']}"
            ))
            pair_h.addLayout(post_col)

            card_layout.addLayout(pair_h)
            self.results_layout.addWidget(card)

        self.results_layout.addStretch()

    def _build_aoi_table(self, aois):
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([
            "AOI", "First Fixation (s)", "Total Fixation (s)", "Blinks"
        ])
        table.setRowCount(len(aois))
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        # Compute proper height: header + rows + margin
        header_h = table.horizontalHeader().defaultSectionSize()
        row_h = 30
        needed = header_h + row_h * max(len(aois), 1) + 4
        table.setMinimumHeight(needed)
        table.setFixedHeight(needed)

        for row, aoi in enumerate(aois):
            table.setItem(row, 0, QTableWidgetItem(aoi['name']))
            table.setItem(row, 1, QTableWidgetItem(f"{aoi['first_fixation']:.2f}"))
            table.setItem(row, 2, QTableWidgetItem(f"{aoi['total_fixation']:.2f}"))
            table.setItem(row, 3, QTableWidgetItem(str(aoi['blinks'])))

        return table

    def _download_csv(self):
        if not self._current_filepath or not os.path.exists(self._current_filepath):
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", os.path.basename(self._current_filepath),
            "CSV Files (*.csv)"
        )
        if dest:
            shutil.copy2(self._current_filepath, dest)
