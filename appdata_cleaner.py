# AppData Cleaner GUI
# Requires: PySide6 (or install PyQt5 and adjust imports accordingly)

import os
import sys
import shutil
import ctypes
from pathlib import Path
from threading import Event
from humanize import naturalsize  # pip install humanize

from PySide6.QtCore import Qt, QThread, Signal, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QTableView,
    QVBoxLayout,
    QWidget,
)

# --- Settings -------------------------------------------------------------
KEYWORDS = {"cache", "temp", "crash", "report", "dump", "crashes", "pending"}

# -------------------------------------------------------------------------
class ScanWorker(QThread):
    progress = Signal(int)
    current_path = Signal(str)
    folder_found = Signal(str, str, str)  # path, size_human, size_bytes_str
    finished = Signal(int)  # total count

    def __init__(self, base_paths, max_depth):
        super().__init__()
        self.base_paths = base_paths
        self.max_depth = max_depth
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        self.results_count = 0
        for base in self.base_paths:
            if self._stop_event.is_set():
                break
            self._scan_path(Path(base), 0)
        self.finished.emit(self.results_count)

    def _scan_path(self, path: Path, depth: int):
        if (self.max_depth > 0 and depth > self.max_depth) or self._stop_event.is_set():
            return
        try:
            self.current_path.emit(str(path))
            for entry in path.iterdir():
                if not entry.is_dir():
                    continue
                name = entry.name.lower()
                if any(kw in name for kw in KEYWORDS):
                    size = self._dir_size(entry)
                    # Skip folders with zero size
                    if size == 0:
                        continue
                    self.results_count += 1
                    size_human = naturalsize(size, binary=True)
                    self.folder_found.emit(str(entry), size_human, str(size))
                    self.progress.emit(self.results_count)
                    # Do not descend further inside this folder
                    continue
                # Recurse deeper
                self._scan_path(entry, depth + 1)
        except PermissionError:
            pass

    def _dir_size(self, directory: Path) -> int:
        total = 0
        try:
            for root, _, files in os.walk(directory, topdown=True):
                for f in files:
                    try:
                        fp = Path(root) / f
                        total += fp.stat().st_size
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        return total


class SortFilterProxyModel(QSortFilterProxyModel):
    def lessThan(self, left, right):
        # Special handling for the Size column (column 2)
        if left.column() == 2:
            left_data = self.sourceModel().data(left, Qt.UserRole)
            right_data = self.sourceModel().data(right, Qt.UserRole)
            if left_data is not None and right_data is not None:
                return left_data < right_data
        # Default string comparison for other columns
        return super().lessThan(left, right)


class DeleteWorker(QThread):
    progress = Signal(int)
    finished = Signal()

    def __init__(self, paths):
        super().__init__()
        self.paths = paths

    def run(self):
        for idx, p in enumerate(self.paths, 1):
            try:
                shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass
            self.progress.emit(idx)
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AppData Cleaner")
        self.resize(900, 600)

        # UI Elements
        self.scan_btn = QPushButton("Scan")
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Deselect All")
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setStyleSheet("QPushButton { background:red; color:white; }")
        self.delete_btn.setEnabled(False)

        # Depth slider
        self.depth_label = QLabel("Depth: 3")
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.setMinimum(0)
        self.depth_slider.setMaximum(10)
        self.depth_slider.setValue(3)
        self.depth_slider.setFixedWidth(100)
        self.depth_slider.valueChanged.connect(self.update_depth_label)

        # Size info label
        self.size_info_label = QLabel("")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.table = QTableView()
        self.source_model = QStandardItemModel(0, 3)
        self.source_model.setHorizontalHeaderLabels(["✔", "Path", "Size"])
        
        # Setup proxy model for sorting
        self.proxy_model = SortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 100)  # Size column
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Path column
        self.table.setSelectionBehavior(QTableView.SelectRows)
        
        # Sort by size (column 2) in descending order by default
        self.table.sortByColumn(2, Qt.DescendingOrder)

        self.status_label = QLabel("Ready")

        # Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.scan_btn)
        top_layout.addWidget(self.select_all_btn)
        top_layout.addWidget(self.deselect_all_btn)
        top_layout.addWidget(self.depth_label)
        top_layout.addWidget(self.depth_slider)
        top_layout.addStretch()
        top_layout.addWidget(self.progress_bar)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.size_info_label)
        bottom_layout.addWidget(self.delete_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table)
        main_layout.addLayout(bottom_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connections
        self.scan_btn.clicked.connect(self.start_scan)
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.delete_btn.clicked.connect(self.start_delete)
        self.source_model.itemChanged.connect(self.update_totals)

        self.scan_worker = None
        self.delete_worker = None

        # No initial scan - user will click button when ready

    def update_depth_label(self, value):
        if value == 0:
            self.depth_label.setText("Depth: ∞")
        else:
            self.depth_label.setText(f"Depth: {value}")

    # ---------- Scanning --------------------------------------------------
    def start_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            return
        self.source_model.removeRows(0, self.source_model.rowCount())
        self.progress_bar.setVisible(False)  # Hide progress bar
        self.status_label.setText("Scanning…")
        self.size_info_label.setText("")  # Clear size info
        self.delete_btn.setEnabled(False)  # Disable during scan
        self.scan_btn.setEnabled(False)  # Disable scan button during scan
        self.select_all_btn.setEnabled(False)  # Disable selection buttons during scan
        self.deselect_all_btn.setEnabled(False)

        bases = [
            os.environ.get("APPDATA"),
            os.environ.get("LOCALAPPDATA"),
            os.environ.get("LOCALAPPDATA").replace("Local", "LocalLow") if os.environ.get("LOCALAPPDATA") else None,
        ]
        bases = [b for b in bases if b and os.path.exists(b)]
        max_depth = self.depth_slider.value()
        self.scan_worker = ScanWorker(bases, max_depth)
        self.scan_worker.progress.connect(lambda n: self.status_label.setText(f"Found {n} folders"))
        self.scan_worker.current_path.connect(lambda path: self.status_label.setText(f"Scanning: {path}"))
        self.scan_worker.folder_found.connect(self.add_folder_to_table)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.start()

    def add_folder_to_table(self, path, size_human, size_bytes_str):
        checkbox_item = QStandardItem()
        checkbox_item.setCheckable(True)
        checkbox_item.setEditable(False)
        path_item = QStandardItem(path)
        size_item = QStandardItem(size_human)
        # Store the raw size in bytes as user data for calculations
        size_item.setData(int(size_bytes_str), Qt.UserRole)
        self.source_model.appendRow([checkbox_item, path_item, size_item])
        self.update_totals()

    def scan_finished(self, total_count):
        self.status_label.setText(f"Scan completed. Found {total_count} folders")
        self.scan_btn.setEnabled(True)  # Re-enable scan button
        self.select_all_btn.setEnabled(True)  # Re-enable selection buttons
        self.deselect_all_btn.setEnabled(True)
        # Sort by size in descending order after scan completion
        self.table.sortByColumn(2, Qt.DescendingOrder)
        self.update_totals()  # Final update to enable delete button if something selected

    # ---------- Selection -------------------------------------------------
    def select_all(self):
        for row in range(self.source_model.rowCount()):
            self.source_model.item(row, 0).setCheckState(Qt.Checked)

    def deselect_all(self):
        for row in range(self.source_model.rowCount()):
            self.source_model.item(row, 0).setCheckState(Qt.Unchecked)

    def update_totals(self, *_):
        total_found = 0
        total_selected = 0
        selected_count = 0
        
        for row in range(self.source_model.rowCount()):
            size_item = self.source_model.item(row, 2)
            # Get the raw size in bytes from UserRole data
            size_bytes = size_item.data(Qt.UserRole)
            if size_bytes is None:
                # Fallback to parsing the displayed text if no UserRole data
                size_bytes = self._parse_size(size_item.text())
            
            total_found += size_bytes
            if self.source_model.item(row, 0).checkState() == Qt.Checked:
                total_selected += size_bytes
                selected_count += 1
        
        found_h = naturalsize(total_found, binary=True)
        selected_h = naturalsize(total_selected, binary=True)
        
        # Update status
        row_count = self.source_model.rowCount()
        if row_count > 0:
            self.status_label.setText(f"Found {row_count} folders")
            self.size_info_label.setText(f"[{selected_h} / {found_h}]")
        else:
            self.status_label.setText("Ready")
            self.size_info_label.setText("")
        
        # Enable delete button if something is selected
        self.delete_btn.setEnabled(total_selected > 0 and selected_count > 0)

    def _parse_size(self, human):
        try:
            multipliers = {
                "B": 1, 
                "Bytes": 1,
                "KiB": 1024, 
                "MiB": 1024**2, 
                "GiB": 1024**3, 
                "TiB": 1024**4,
                "kB": 1000,
                "MB": 1000**2,
                "GB": 1000**3,
                "TB": 1000**4
            }
            parts = human.split()
            if len(parts) != 2:
                return 0
            number, unit = parts
            return int(float(number) * multipliers.get(unit, 1))
        except (ValueError, KeyError, IndexError):
            return 0

    # ---------- Deleting --------------------------------------------------
    def start_delete(self):
        paths_to_delete = []
        for row in range(self.source_model.rowCount()):
            if self.source_model.item(row, 0).checkState() == Qt.Checked:
                paths_to_delete.append(self.source_model.item(row, 1).text())

        if not paths_to_delete:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"This will permanently delete {len(paths_to_delete)} folders. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.delete_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(paths_to_delete))
        self.status_label.setText("Deleting…")

        self.delete_worker = DeleteWorker(paths_to_delete)
        self.delete_worker.progress.connect(self.progress_bar.setValue)
        self.delete_worker.finished.connect(self.deletion_finished)
        self.delete_worker.start()

    def deletion_finished(self):
        QMessageBox.information(self, "Done", "Selected folders have been deleted.")
        # Auto re-scan
        self.start_scan()


# ----------------- Admin rights on Windows ------------------------------

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def show_admin_error():
    """Show admin error with fallback methods"""
    # Try to create QApplication first if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create message box
    msg = QMessageBox()
    msg.setWindowTitle("Administrator Required")
    msg.setIcon(QMessageBox.Critical)
    msg.setText("This application requires Administrator privileges to clean AppData folders.")
    msg.setInformativeText("Please run as Administrator and try again.")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()

if __name__ == "__main__":
    # Debug info for admin check
    admin_status = is_admin()
    
    # Debug mode - show admin status (remove this after testing)
    debug_mode = "--debug" in sys.argv
    if debug_mode:
        app = QApplication(sys.argv)
        QMessageBox.information(None, "Debug Info", 
                               f"Platform: {sys.platform}\n"
                               f"Admin Status: {admin_status}\n"
                               f"Will show admin error: {sys.platform.startswith('win') and not admin_status}")
    
    if sys.platform.startswith("win") and not admin_status:
        show_admin_error()
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
