"""
TokGrabber - Advanced TikTok Downloader GUI with Custom Title Bar, QDarkStyleSheet Theme, and Download History Tab

Features:
1. Advanced error handling & retry logic.
2. Pause/Resume downloads in single mode.
3. Concurrency for batch downloads with a global progress bar and detailed logging.
4. Download history logging to a CSV file and display in a dedicated tab.
5. Thumbnail preview.
6. User settings panel.
7. Custom title bar with a menu for Settings, Export Logs, and About.
8. File existence check (prompts in single mode; skips in batch mode).
9. Batch download global progress bar and enhanced error handling.
10. Right-click on a history row to "Show in Folder".

Usage:
    python TokGrabber.py

Dependencies:
    - PyQt5
    - requests
    - tqdm
    - qdarkstyle

Make sure to place your "tiktok_logo.png" in the same directory as this script.
Note: This script uses an unofficial API endpoint which may change or be discontinued.
"""

import os
import re
import sys
import csv
import time
import requests
from datetime import datetime
from functools import partial
from tqdm import tqdm

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QPoint, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog, QProgressBar,
    QTextEdit, QTabWidget, QFormLayout, QMessageBox, QDialog, QCheckBox,
    QToolButton, QMenu, QTableWidget, QTableWidgetItem
)

try:
    import qdarkstyle
except ImportError:
    qdarkstyle = None


# -------------------------
# Helper Functions
# -------------------------
def is_valid_tiktok_link(url: str) -> bool:
    pattern = r'(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/'
    return re.match(pattern, url) is not None

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()

def format_duration(duration) -> str:
    try:
        d = int(duration)
    except (ValueError, TypeError):
        return str(duration)
    if d < 60:
        return f"{d} seconds"
    else:
        return f"{d//60} minutes {d % 60} seconds"

def fetch_video_info(video_url: str) -> dict:
    api_endpoint = "https://tikwm.com/api"
    params = {"url": video_url, "hd": "1"}
    for attempt in range(3):
        try:
            response = requests.get(api_endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise e

def download_image_as_pixmap(url: str) -> QPixmap:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        pixmap = QPixmap()
        pixmap.loadFromData(r.content)
        return pixmap
    except Exception:
        return QPixmap()

def append_download_history(title: str, url: str, filepath: str, filesize: int):
    history_file = "download_history.csv"
    with open(history_file, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([datetime.now().isoformat(), title, url, filepath, filesize])


# -------------------------
# Worker Threads
# -------------------------
class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, int)  # filepath, filesize
    error = pyqtSignal(str)
    
    def __init__(self, download_url: str, output_filename: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.output_filename = output_filename
        self._paused = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        try:
            headers = {}
            mode = "wb"
            existing_size = 0
            if os.path.exists(self.output_filename):
                existing_size = os.path.getsize(self.output_filename)
                headers["Range"] = f"bytes={existing_size}-"
                mode = "ab"
            response = requests.get(self.download_url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()
            total_size = response.headers.get("content-length")
            if total_size is None:
                total_size = 0
            else:
                total_size = int(total_size)
                if "Content-Range" in response.headers:
                    total_size = int(response.headers.get("Content-Range").split("/")[-1])
            total = total_size
            downloaded = existing_size
            with open(self.output_filename, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    while self._paused:
                        time.sleep(0.2)
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            percent = int((downloaded / total) * 100)
                            self.progress.emit(percent)
            self.finished.emit(self.output_filename, downloaded)
        except Exception as e:
            self.error.emit(str(e))

class FetchInfoWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, video_url: str, parent=None):
        super().__init__(parent)
        self.video_url = video_url
        
    def run(self):
        try:
            info = fetch_video_info(self.video_url)
            self.finished.emit(info)
        except Exception as e:
            self.error.emit(str(e))


# -------------------------
# Custom Title Bar
# -------------------------
class CustomTitleBar(QWidget):
    """
    A custom title bar that includes:
      - TikTok logo
      - Title label (TokGrabber)
      - A menu button for Settings, Export Logs, and About
      - Minimize, Maximize/Restore, and Close buttons
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(50)
        self._startPos = QPoint(0, 0)
        self._clickPos = None

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)

        # TikTok Logo
        self.logo_label = QLabel()
        pixmap = QPixmap("tiktok_logo.png")
        self.logo_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.logo_label)

        # Title Label (TokGrabber)
        self.title_label = QLabel("TokGrabber")
        self.title_label.setStyleSheet("color: #F0F0F0; font: bold 16px;")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Menu Button for Settings, Export Logs & About
        self.menu_button = QToolButton()
        self.menu_button.setText("≡")
        self.menu_button.setStyleSheet("QToolButton { color: #F0F0F0; background: transparent; }")
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.menu = QMenu()
        self.settings_action = self.menu.addAction("Settings")
        self.settings_action.triggered.connect(self.parent.open_settings)
        self.export_logs_action = self.menu.addAction("Export Logs")
        self.export_logs_action.triggered.connect(self.parent.export_logs)
        self.about_action = self.menu.addAction("About")
        self.about_action.triggered.connect(self.parent.show_about)
        self.menu_button.setMenu(self.menu)
        layout.addWidget(self.menu_button)

        # Minimize Button
        self.min_button = QPushButton("-")
        self.min_button.setFixedSize(30, 30)
        self.min_button.setStyleSheet("background-color: transparent; color: #F0F0F0;")
        self.min_button.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.min_button)

        # Maximize/Restore Button
        self.max_button = QPushButton("☐")
        self.max_button.setFixedSize(30, 30)
        self.max_button.setStyleSheet("background-color: transparent; color: #F0F0F0;")
        self.max_button.clicked.connect(self.toggle_max_restore)
        layout.addWidget(self.max_button)

        # Close Button
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("background-color: transparent; color: #F0F0F0;")
        self.close_button.clicked.connect(self.parent.close)
        layout.addWidget(self.close_button)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #19232d;")

    def toggle_max_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._clickPos = event.globalPos()
            self._startPos = self.parent.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._clickPos is not None:
            delta = event.globalPos() - self._clickPos
            self.parent.move(self._startPos + delta)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._clickPos = None
        event.accept()


# -------------------------
# Settings Dialog
# -------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 200)

        self.settings = QSettings("MyCompany", "TokGrabber")

        layout = QFormLayout()
        self.output_dir_edit = QLineEdit(self.settings.value("output_dir", os.getcwd()))
        self.timeout_edit = QLineEdit(self.settings.value("timeout", "10"))
        self.verbose_checkbox = QCheckBox("Verbose Logging")
        self.verbose_checkbox.setChecked(self.settings.value("verbose", "false") == "true")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])

        layout.addRow("Default Output Directory:", self.output_dir_edit)
        layout.addRow("Network Timeout (sec):", self.timeout_edit)
        layout.addRow("", self.verbose_checkbox)
        layout.addRow("Theme:", self.theme_combo)

        btn_box = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.save_btn)
        btn_box.addWidget(self.cancel_btn)
        layout.addRow("", btn_box)
        self.setLayout(layout)

    def accept(self):
        self.settings.setValue("output_dir", self.output_dir_edit.text())
        self.settings.setValue("timeout", self.timeout_edit.text())
        self.settings.setValue("verbose", "true" if self.verbose_checkbox.isChecked() else "false")
        self.settings.setValue("theme", self.theme_combo.currentText())
        super().accept()


# -------------------------
# Main GUI Window
# -------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Remove native title bar for custom one
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(800, 600)
        self.setWindowTitle("TokGrabber")
        self.setWindowIcon(QIcon("tiktok_logo.png"))

        self.settings = QSettings("MyCompany", "TokGrabber")

        self.statusBar().showMessage("Ready")

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Tab Widget for downloader functionality
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.single_tab = QWidget()
        self.batch_tab = QWidget()
        self.history_tab = QWidget()
        self.tabs.addTab(self.single_tab, "Single Download")
        self.tabs.addTab(self.batch_tab, "Batch Download")
        self.tabs.addTab(self.history_tab, "Download History")

        self.setup_single_tab()
        self.setup_batch_tab()
        self.setup_history_tab()

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Refresh history when switching to history tab
        self.tabs.currentChanged.connect(self.on_tab_changed)

    # -------------------------
    # Single Download Tab (using QGridLayout)
    # -------------------------
    def setup_single_tab(self):
        main_layout = QVBoxLayout()
        grid = QGridLayout()

        grid.addWidget(QLabel("TikTok URL:"), 0, 0)
        self.url_input = QLineEdit()
        grid.addWidget(self.url_input, 0, 1)
        self.fetch_button = QPushButton("Fetch Info")
        self.fetch_button.clicked.connect(self.fetch_info)
        grid.addWidget(self.fetch_button, 0, 2)

        self.title_label = QLabel("Title: ")
        grid.addWidget(self.title_label, 1, 0, 1, 3)

        self.region_label = QLabel("Region: ")
        grid.addWidget(self.region_label, 2, 0, 1, 3)

        self.duration_label = QLabel("Duration: ")
        grid.addWidget(self.duration_label, 3, 0, 1, 3)

        grid.addWidget(QLabel("Thumbnail:"), 4, 0)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(200, 200)
        self.preview_button = QPushButton("Preview Thumbnail")
        self.preview_button.clicked.connect(self.preview_thumbnail)
        thumb_layout = QHBoxLayout()
        thumb_layout.addWidget(self.thumbnail_label)
        thumb_layout.addWidget(self.preview_button)
        thumb_container = QWidget()
        thumb_container.setLayout(thumb_layout)
        grid.addWidget(thumb_container, 4, 1, 1, 2)

        grid.addWidget(QLabel("Download Type:"), 5, 0)
        self.download_type = QComboBox()
        self.download_type.addItems(["Standard Video", "HD Video", "Cover Image", "Music"])
        grid.addWidget(self.download_type, 5, 1, 1, 2)

        grid.addWidget(QLabel("Output Directory:"), 6, 0)
        self.output_dir_input = QLineEdit(self.settings.value("output_dir", os.getcwd()))
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_output_dir)
        out_layout = QHBoxLayout()
        out_layout.addWidget(self.output_dir_input)
        out_layout.addWidget(self.browse_button)
        out_container = QWidget()
        out_container.setLayout(out_layout)
        grid.addWidget(out_container, 6, 1, 1, 2)

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_media)
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        download_layout = QHBoxLayout()
        download_layout.addWidget(self.download_button)
        download_layout.addWidget(self.pause_button)
        download_container = QWidget()
        download_container.setLayout(download_layout)
        grid.addWidget(download_container, 7, 0, 1, 3)

        main_layout.addLayout(grid)
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)
        self.single_tab.setLayout(main_layout)

    # -------------------------
    # Batch Download Tab
    # -------------------------
    def setup_batch_tab(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.batch_file_input = QLineEdit()
        self.batch_browse_button = QPushButton("Browse")
        self.batch_browse_button.clicked.connect(self.browse_batch_file)
        batch_file_layout = QHBoxLayout()
        batch_file_layout.addWidget(self.batch_file_input)
        batch_file_layout.addWidget(self.batch_browse_button)
        form_layout.addRow("URLs File:", batch_file_layout)

        self.batch_download_type = QComboBox()
        self.batch_download_type.addItems(["Standard Video", "HD Video", "Cover Image", "Music"])
        form_layout.addRow("Download Type:", self.batch_download_type)

        self.batch_output_dir_input = QLineEdit(self.settings.value("output_dir", os.getcwd()))
        self.batch_browse_button_dir = QPushButton("Browse")
        self.batch_browse_button_dir.clicked.connect(self.browse_batch_output_dir)
        batch_out_layout = QHBoxLayout()
        batch_out_layout.addWidget(self.batch_output_dir_input)
        batch_out_layout.addWidget(self.batch_browse_button_dir)
        form_layout.addRow("Output Directory:", batch_out_layout)

        self.batch_download_button = QPushButton("Start Batch Download")
        self.batch_download_button.clicked.connect(self.start_batch_download)
        form_layout.addRow("", self.batch_download_button)

        layout.addLayout(form_layout)
        self.batch_progress_bar = QProgressBar()
        layout.addWidget(self.batch_progress_bar)
        self.batch_log_area = QTextEdit()
        self.batch_log_area.setReadOnly(True)
        layout.addWidget(self.batch_log_area)
        self.batch_tab.setLayout(layout)
        self.batch_workers = []

    # -------------------------
    # Download History Tab
    # -------------------------
    def setup_history_tab(self):
        layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Date", "Title", "URL", "File Path", "File Size"])
        # Enable right-click context menu for "Show in Folder"
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_history_context_menu)
        layout.addWidget(self.history_table)
        self.history_refresh_button = QPushButton("Refresh History")
        self.history_refresh_button.clicked.connect(self.load_history)
        layout.addWidget(self.history_refresh_button)
        self.history_tab.setLayout(layout)
        self.load_history()

    def load_history(self):
        self.history_table.setRowCount(0)
        history_file = "download_history.csv"
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    row_position = self.history_table.rowCount()
                    self.history_table.insertRow(row_position)
                    for col, item in enumerate(row):
                        self.history_table.setItem(row_position, col, QTableWidgetItem(item))
        else:
            self.history_table.setRowCount(0)
            self.history_table.insertRow(0)
            self.history_table.setItem(0, 0, QTableWidgetItem("No history available."))

    def show_history_context_menu(self, pos):
        index = self.history_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        file_item = self.history_table.item(row, 3)  # File Path column
        if file_item:
            file_path = file_item.text()
            menu = QMenu(self.history_table)
            action_show = menu.addAction("Show in Folder")
            action = menu.exec_(self.history_table.viewport().mapToGlobal(pos))
            if action == action_show:
                folder = os.path.dirname(file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def on_tab_changed(self, index):
        if self.tabs.tabText(index) == "Download History":
            self.load_history()

    # -------------------------
    # Utility Methods
    # -------------------------
    def log(self, message: str):
        self.log_area.append(f'<span style="color: #00BFFF;">{message}</span>')
        self.statusBar().showMessage(message, 5000)

    def batch_log(self, message: str):
        self.batch_log_area.append(f'<span style="color: #00BFFF;">{message}</span>')
        self.statusBar().showMessage(message, 5000)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if directory:
            self.output_dir_input.setText(directory)

    def browse_batch_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select URLs File", os.getcwd(), "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.batch_file_input.setText(file_name)

    def browse_batch_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.getcwd())
        if directory:
            self.batch_output_dir_input.setText(directory)

    def export_logs(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Export Logs", "logs.txt", "Text Files (*.txt);;All Files (*)")
        if fname:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(self.log_area.toPlainText())
            QMessageBox.information(self, "Export Logs", "Logs exported successfully.")

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_():
            self.output_dir_input.setText(self.settings.value("output_dir", os.getcwd()))
            self.batch_output_dir_input.setText(self.settings.value("output_dir", os.getcwd()))
            self.log("Settings saved.")

    def show_about(self):
        QMessageBox.about(
            self,
            "About TokGrabber",
            "<h3>TokGrabber</h3>"
            "<p>Created by Ibrahim Hammad (HaMMaDy)</p>"
            '<p>GitHub: <a href="https://github.com/xHaMMaDy" style="color:#00BFFF;">https://github.com/xHaMMaDy</a></p>'
        )

    # -------------------------
    # Single Download Actions
    # -------------------------
    def fetch_info(self):
        url = self.url_input.text().strip()
        if not is_valid_tiktok_link(url):
            QMessageBox.warning(self, "Invalid URL", "This does not appear to be a valid TikTok URL.")
            return
        self.log("Fetching video info...")
        self.fetch_worker = FetchInfoWorker(url)
        self.fetch_worker.finished.connect(self.on_info_fetched)
        self.fetch_worker.error.connect(lambda err: self.log("Error: " + err))
        self.fetch_worker.start()

    def on_info_fetched(self, info: dict):
        if not isinstance(info, dict) or info.get("code") != 0 or "data" not in info:
            self.log("Invalid API response.")
            return
        data = info["data"]
        title = data.get("title", "untitled")
        region = data.get("region", "unknown")
        duration = data.get("duration", "unknown")
        self.title_label.setText("Title: " + title)
        self.region_label.setText("Region: " + region)
        self.duration_label.setText("Duration: " + format_duration(duration))
        cover_url = data.get("cover")
        if cover_url:
            pixmap = download_image_as_pixmap(cover_url)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.thumbnail_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_label.setPixmap(scaled)
        self.log("Video info fetched successfully.")

    def preview_thumbnail(self):
        if self.thumbnail_label.pixmap():
            dlg = QDialog(self)
            dlg.setWindowTitle("Thumbnail Preview")
            vbox = QVBoxLayout(dlg)
            lbl = QLabel()
            lbl.setPixmap(self.thumbnail_label.pixmap().scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            vbox.addWidget(lbl)
            dlg.exec_()
        else:
            QMessageBox.information(self, "Preview", "No thumbnail available.")

    def download_media(self):
        url = self.url_input.text().strip()
        if not is_valid_tiktok_link(url):
            QMessageBox.warning(self, "Invalid URL", "This does not appear to be a valid TikTok URL.")
            return
        try:
            info = fetch_video_info(url)
        except Exception as e:
            QMessageBox.critical(self, "Error", "Error fetching info: " + str(e))
            return
        if not isinstance(info, dict) or info.get("code") != 0 or "data" not in info:
            self.log("Invalid API response.")
            return
        data = info["data"]
        title = data.get("title", "untitled")
        sanitized_title = sanitize_filename(title)
        download_type = self.download_type.currentText()
        file_ext = ".mp4"
        if download_type == "Standard Video":
            download_url = data.get("play")
        elif download_type == "HD Video":
            download_url = data.get("hdplay")
        elif download_type == "Cover Image":
            download_url = data.get("cover")
            file_ext = ".jpg"
        elif download_type == "Music":
            download_url = data.get("music")
            file_ext = ".mp3"
        else:
            self.log("Invalid download type selected.")
            return
        if not download_url:
            self.log("Selected media is not available.")
            return
        output_dir = self.output_dir_input.text().strip()
        output_filename = os.path.join(output_dir, sanitized_title + file_ext)
        if os.path.exists(output_filename):
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"The file {output_filename} already exists.\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                self.log("Download cancelled: file already exists.")
                return
        self.log("Starting download...")
        self.download_worker = DownloadWorker(download_url, output_filename)
        self.download_worker.progress.connect(lambda p: self.progress_bar.setValue(p))
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(lambda err: self.log("Download error: " + err))
        self.pause_button.setEnabled(True)
        self.download_worker.start()

    def on_download_finished(self, filepath: str, filesize: int):
        self.log("Download complete: " + filepath)
        append_download_history(self.title_label.text().replace("Title: ", ""),
                                self.url_input.text().strip(), filepath, filesize)

    def toggle_pause(self):
        if hasattr(self, "download_worker"):
            if self.pause_button.text() == "Pause":
                self.download_worker.pause()
                self.pause_button.setText("Resume")
                self.log("Download paused.")
            else:
                self.download_worker.resume()
                self.pause_button.setText("Pause")
                self.log("Download resumed.")

    # -------------------------
    # Batch Download Actions
    # -------------------------
    def start_batch_download(self):
        batch_file = self.batch_file_input.text().strip()
        if not batch_file or not os.path.exists(batch_file):
            self.batch_log("Please select a valid URLs file.")
            return
        output_dir = self.batch_output_dir_input.text().strip()
        download_type = self.batch_download_type.currentText()
        options = {
            "Standard Video": ("play", ".mp4"),
            "HD Video": ("hdplay", ".mp4"),
            "Cover Image": ("cover", ".jpg"),
            "Music": ("music", ".mp3")
        }
        if download_type not in options:
            self.batch_log("Invalid download type selected.")
            return
        key, file_ext = options[download_type]
        with open(batch_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
        valid_urls = [url for url in urls if is_valid_tiktok_link(url)]
        if not valid_urls:
            self.batch_log("No valid TikTok URLs found in the file.")
            return
        self.batch_total = len(valid_urls)
        self.batch_completed = 0
        self.batch_progress_bar.setValue(0)
        self.batch_workers = []
        for idx, video_url in enumerate(valid_urls, start=1):
            self.batch_log(f"Processing video {idx} of {self.batch_total}")
            try:
                info = fetch_video_info(video_url)
            except Exception as e:
                self.batch_log(f"Error fetching info for URL {video_url}: {e}")
                self.increment_batch_progress()
                continue
            if not isinstance(info, dict) or info.get("code") != 0 or "data" not in info:
                self.batch_log(f"Invalid API response for URL {video_url}")
                self.increment_batch_progress()
                continue
            data = info["data"]
            title = data.get("title", f"untitled_{idx}")
            sanitized_title = sanitize_filename(title)
            download_url = data.get(key)
            if not download_url:
                self.batch_log(f"Media for {download_type} not available for URL {video_url}")
                self.increment_batch_progress()
                continue
            output_filename = os.path.join(output_dir, sanitized_title + file_ext)
            if os.path.exists(output_filename):
                self.batch_log(f"File {output_filename} already exists. Skipping download.")
                self.increment_batch_progress()
                continue
            self.batch_log(f"Downloading: {output_filename}")
            worker = DownloadWorker(download_url, output_filename)
            worker.progress.connect(lambda p, url=video_url: self.batch_log(f"Progress for {url}: {p}%"))
            worker.finished.connect(lambda f, url=video_url: self.on_batch_item_complete(url, f))
            worker.error.connect(lambda err, url=video_url: self.on_batch_item_error(url, err))
            worker.start()
            self.batch_workers.append(worker)

    def on_batch_item_complete(self, url, filename):
        self.batch_log(f"Download complete for {url}: {filename}")
        self.increment_batch_progress()

    def on_batch_item_error(self, url, err):
        self.batch_log(f"Download error for {url}: {err}")
        self.increment_batch_progress()

    def increment_batch_progress(self):
        self.batch_completed += 1
        percent = int((self.batch_completed / self.batch_total) * 100)
        self.batch_progress_bar.setValue(percent)

    def batch_log(self, message: str):
        self.batch_log_area.append(f'<span style="color: #00BFFF;">{message}</span>')
        self.statusBar().showMessage(message, 5000)

# -------------------------
# Main Execution
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    if qdarkstyle is not None:
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    else:
        fallback_theme = "QMainWindow { background-color: #2E2E2E; }"
        app.setStyleSheet(fallback_theme)

    window = MainWindow()
    window.tabs.currentChanged.connect(window.on_tab_changed)
    window.show()
    sys.exit(app.exec_())