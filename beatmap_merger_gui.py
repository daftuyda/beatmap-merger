import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QDoubleSpinBox,
    QLineEdit, QFileDialog, QGroupBox, QGridLayout, QHeaderView,
    QMessageBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from beatmap_merger import parse_osu, merge_beatmaps


def extract_map_info(osu_path):
    """Extract display name and audio path from an .osu file."""
    sections = parse_osu(osu_path)
    osu_dir = os.path.dirname(osu_path)

    # Extract audio filename from General section
    audio_filename = None
    for line in sections.get('General', []):
        if line.startswith('AudioFilename:'):
            audio_filename = line.split(':', 1)[1].strip()
            break

    audio_path = None
    if audio_filename:
        candidate = os.path.join(osu_dir, audio_filename)
        if os.path.isfile(candidate):
            audio_path = candidate

    # Extract artist and title from Metadata section
    artist = ''
    title = ''
    for line in sections.get('Metadata', []):
        if line.startswith('Artist:'):
            artist = line.split(':', 1)[1].strip()
        elif line.startswith('Title:'):
            title = line.split(':', 1)[1].strip()

    display_name = f'{artist} - {title}' if artist or title else os.path.basename(osu_path)

    return {
        'osu_path': osu_path,
        'audio_path': audio_path,
        'audio_filename': audio_filename or '(not found)',
        'display_name': display_name,
    }


class MergeWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, osu_paths, audio_paths, output_osu, output_audio, hp, od, cs, ar, version):
        super().__init__()
        self.osu_paths = osu_paths
        self.audio_paths = audio_paths
        self.output_osu = output_osu
        self.output_audio = output_audio
        self.hp = hp
        self.od = od
        self.cs = cs
        self.ar = ar
        self.version = version

    def run(self):
        try:
            merge_beatmaps(
                self.osu_paths, self.audio_paths,
                self.output_osu, self.output_audio,
                self.hp, self.od, self.cs, self.ar,
                version=self.version or None,
            )
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class MergerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('osu! Beatmap Merger')
        self.setMinimumSize(700, 520)
        self.entries = []  # list of extract_map_info dicts
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Beatmap list ---
        list_group = QGroupBox('Beatmaps')
        list_layout = QVBoxLayout(list_group)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['#', 'Map Name', 'Audio File'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        list_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton('Add .osu Files')
        self.btn_remove = QPushButton('Remove')
        self.btn_up = QPushButton('Move Up')
        self.btn_down = QPushButton('Move Down')
        for btn in (self.btn_add, self.btn_remove, self.btn_up, self.btn_down):
            btn_row.addWidget(btn)
        list_layout.addLayout(btn_row)
        layout.addWidget(list_group)

        self.btn_add.clicked.connect(self.add_files)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)

        # --- Difficulty settings ---
        diff_group = QGroupBox('Difficulty Settings')
        diff_layout = QGridLayout(diff_group)
        self.spin_hp = self._make_spin(5.0)
        self.spin_cs = self._make_spin(4.0)
        self.spin_od = self._make_spin(8.0)
        self.spin_ar = self._make_spin(9.0)
        diff_layout.addWidget(QLabel('HP'), 0, 0)
        diff_layout.addWidget(self.spin_hp, 0, 1)
        diff_layout.addWidget(QLabel('CS'), 0, 2)
        diff_layout.addWidget(self.spin_cs, 0, 3)
        diff_layout.addWidget(QLabel('OD'), 1, 0)
        diff_layout.addWidget(self.spin_od, 1, 1)
        diff_layout.addWidget(QLabel('AR'), 1, 2)
        diff_layout.addWidget(self.spin_ar, 1, 3)
        diff_layout.addWidget(QLabel('Version'), 2, 0)
        self.edit_version = QLineEdit()
        self.edit_version.setPlaceholderText('e.g. Compilation, Marathon, Insane')
        diff_layout.addWidget(self.edit_version, 2, 1, 1, 3)
        layout.addWidget(diff_group)

        # --- Output paths ---
        out_group = QGroupBox('Output')
        out_layout = QGridLayout(out_group)

        out_layout.addWidget(QLabel('.osu file:'), 0, 0)
        self.edit_osu_out = QLineEdit('merged.osu')
        out_layout.addWidget(self.edit_osu_out, 0, 1)
        self.btn_browse_osu = QPushButton('Browse')
        out_layout.addWidget(self.btn_browse_osu, 0, 2)

        out_layout.addWidget(QLabel('Audio:'), 1, 0)
        self.edit_audio_out = QLineEdit('merged_audio.mp3')
        out_layout.addWidget(self.edit_audio_out, 1, 1)
        self.btn_browse_audio = QPushButton('Browse')
        out_layout.addWidget(self.btn_browse_audio, 1, 2)

        layout.addWidget(out_group)

        self.btn_browse_osu.clicked.connect(self.browse_osu_out)
        self.btn_browse_audio.clicked.connect(self.browse_audio_out)

        # --- Merge button + status ---
        bottom_row = QHBoxLayout()
        self.btn_merge = QPushButton('Merge!')
        self.btn_merge.setMinimumHeight(36)
        self.status_label = QLabel('')
        bottom_row.addWidget(self.btn_merge)
        bottom_row.addWidget(self.status_label, 1)
        layout.addLayout(bottom_row)

        self.btn_merge.clicked.connect(self.start_merge)

    def _make_spin(self, default):
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 10.0)
        spin.setSingleStep(0.1)
        spin.setDecimals(1)
        spin.setValue(default)
        return spin

    # --- Beatmap list actions ---

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select .osu files', '', 'osu! Beatmaps (*.osu)')
        if not paths:
            return
        for p in paths:
            info = extract_map_info(p)
            self.entries.append(info)
        self._refresh_table()

    def remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.entries.pop(row)
        self._refresh_table()

    def move_up(self):
        row = self.table.currentRow()
        if row <= 0:
            return
        self.entries[row - 1], self.entries[row] = self.entries[row], self.entries[row - 1]
        self._refresh_table()
        self.table.selectRow(row - 1)

    def move_down(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.entries) - 1:
            return
        self.entries[row], self.entries[row + 1] = self.entries[row + 1], self.entries[row]
        self._refresh_table()
        self.table.selectRow(row + 1)

    def _refresh_table(self):
        self.table.setRowCount(len(self.entries))
        for i, entry in enumerate(self.entries):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(entry['display_name']))
            audio_text = entry['audio_filename']
            if entry['audio_path'] is None:
                audio_text += '  [MISSING]'
            self.table.setItem(i, 2, QTableWidgetItem(audio_text))

    # --- Output browse ---

    def browse_osu_out(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save merged .osu', self.edit_osu_out.text(), 'osu! Beatmap (*.osu)')
        if path:
            self.edit_osu_out.setText(path)

    def browse_audio_out(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save merged audio', self.edit_audio_out.text(),
            'Audio Files (*.mp3 *.wav *.ogg)')
        if path:
            self.edit_audio_out.setText(path)

    # --- Merge ---

    def start_merge(self):
        if not self.entries:
            QMessageBox.warning(self, 'No beatmaps', 'Add at least one .osu file first.')
            return

        missing = [e['display_name'] for e in self.entries if e['audio_path'] is None]
        if missing:
            QMessageBox.critical(
                self, 'Missing audio files',
                'Could not find audio files for:\n' + '\n'.join(missing))
            return

        osu_paths = [e['osu_path'] for e in self.entries]
        audio_paths = [e['audio_path'] for e in self.entries]

        self.btn_merge.setEnabled(False)
        self.status_label.setText('Merging...')

        self.worker = MergeWorker(
            osu_paths, audio_paths,
            self.edit_osu_out.text(), self.edit_audio_out.text(),
            self.spin_hp.value(), self.spin_od.value(),
            self.spin_cs.value(), self.spin_ar.value(),
            self.edit_version.text().strip(),
        )
        self.worker.finished.connect(self.on_merge_done)
        self.worker.error.connect(self.on_merge_error)
        self.worker.start()

    def on_merge_done(self):
        self.btn_merge.setEnabled(True)
        self.status_label.setText('Done!')
        QMessageBox.information(self, 'Success', 'Beatmaps merged successfully!')

    def on_merge_error(self, msg):
        self.btn_merge.setEnabled(True)
        self.status_label.setText('Error')
        QMessageBox.critical(self, 'Merge failed', msg)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MergerWindow()
    window.show()
    sys.exit(app.exec())
