

# Redesigned Production Codebase (`Voltix_Advanced.py`)

import os
import sys
import json
import sqlite3
import ctypes
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QSlider, QPushButton, QHBoxLayout,
    QVBoxLayout, QFileDialog, QStackedWidget, QDialog, QListWidget,
    QSplitter, QComboBox, QListWidgetItem, QLineEdit
)
from PyQt6.QtCore import Qt, QUrl, QTime
from PyQt6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

SETTINGS_FILE = "settings.json"
DB_FILE = "voltix_library.db"

DEFAULT_SETTINGS = {
    "volume": 100,
    "keybinds": {
        "open": "O",
        "play_pause": "Space",
        "settings": "S",
        "fullscreen": "F"
    }
}

# Force Windows taskbar to register the custom icon
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "voltix.advanced.app")
except:
    pass


def get_path(file):
    """EXE-safe resource handling system."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, file)


def load_settings():
    if Path(SETTINGS_FILE).exists():
        try:
            return json.loads(Path(SETTINGS_FILE).read_text())
        except:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(data):
    Path(SETTINGS_FILE).write_text(json.dumps(data, indent=4))

# --- Database Setup for Recent Files & Media Library ---


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            file_name TEXT,
            type TEXT
        )
    """)
    conn.commit()
    conn.close()


def db_add_file(file_path, file_type="recent"):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        file_name = os.path.basename(file_path)
        cursor.execute("INSERT OR REPLACE INTO library (file_path, file_name, type) VALUES (?, ?, ?)",
                       (file_path, file_name, file_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")


def db_get_files(file_type="recent"):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_name, file_path FROM library WHERE type = ? ORDER BY id DESC", (file_type,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except:
        return []

# --- Subtitle Parser ---


def parse_srt(srt_path):
    subtitles = []
    if not os.path.exists(srt_path):
        return subtitles
    try:
        content = Path(srt_path).read_text(encoding='utf-8', errors='ignore')
        blocks = content.replace('\r\n', '\n').split('\n\n')
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                times = lines[1].split(' --> ')
                if len(times) == 2:
                    start = parse_srt_time(times[0])
                    end = parse_srt_time(times[1])
                    text = "\n".join(lines[2:])
                    subtitles.append(
                        {"start": start, "end": end, "text": text})
    except Exception as e:
        print(f"Subtitle parsing error: {e}")
    return subtitles


def parse_srt_time(time_str):
    try:
        parts = time_str.replace(',', ':').split(':')
        return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000 + int(parts[3])
    except:
        return 0


# --- Persistent Keybinds Settings Window ---
class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Voltix Advanced Settings")
        self.resize(400, 320)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Keyboard Shortcuts Configuration</b>"))

        self.inputs = {}
        for action, key in self.settings["keybinds"].items():
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"{action.replace('_', ' ').title()}:"))
            line_edit = QLineEdit(key)
            line_edit.setStyleSheet(
                "background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 4px;")
            h_layout.addWidget(line_edit)
            self.inputs[action] = line_edit
            layout.addLayout(h_layout)

        layout.addSpacing(15)
        save_btn = QPushButton("Save & Apply")
        save_btn.setStyleSheet(
            "background-color: #fab387; color: #11111b; padding: 6px; font-weight: bold;")
        save_btn.clicked.connect(self.save_and_close)
        layout.addWidget(save_btn)

    def save_and_close(self):
        for action, line_edit in self.inputs.items():
            self.settings["keybinds"][action] = line_edit.text(
            ).strip().upper()
        self.accept()


# --- Modern UI Application Main Framework ---
class Player(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_data = load_settings()
        init_db()

        self.subtitles = []

        self.setWindowTitle("Voltix Video Player")
        icon_path = get_path("logo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1300, 750)
        self.setAcceptDrops(True)

        # Fluid Dark Palette Stylesheet
        self.setStyleSheet("""
            QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
            QPushButton { background-color: #313244; border: none; padding: 8px 12px; border-radius: 5px; }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
            QSlider::groove:horizontal { height: 6px; background: #313244; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #fab387; border-radius: 3px; }
            QSlider::handle:horizontal { background: #cdd6f4; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
            QListWidget { background-color: #11111b; border: 1px solid #313244; border-radius: 6px; padding: 5px; }
            QComboBox { background-color: #313244; border: none; padding: 4px; border-radius: 4px; color: #cdd6f4; }
        """)

        # Core Media Infrastructure
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(self.settings_data["volume"] / 100)

        # Display Window stack setup
        self.video = QVideoWidget()
        self.video.setStyleSheet("background-color: #000000;")

        # Stacked Container for Canvas Layout
        self.media_container = QWidget()
        self.container_layout = QStackedWidget(self.media_container)
        # Fallback placeholder geometry
        self.container_layout.setGeometry(0, 0, 1000, 500)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(icon_path):
            self.logo_label.setPixmap(QPixmap(icon_path).scaled(
                280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        self.container_layout.addWidget(self.logo_label)
        self.container_layout.addWidget(self.video)

        # Connect player visual pipeline output directly inside our stacked framework
        self.player.setVideoOutput(self.video)

        # Embedded Overlays
        self.center_play_btn = QPushButton("▶", self.media_container)
        self.center_play_btn.setStyleSheet(
            "font-size: 38px; background-color: rgba(17, 17, 27, 200); color: #fab387; border-radius: 35px; min-width: 70px; max-width: 70px; min-height: 70px; max-height: 70px;")
        self.center_play_btn.clicked.connect(self.play_pause)

        self.subtitle_label = QLabel("", self.media_container)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet(
            "color: #f9e2af; background-color: rgba(0, 0, 0, 160); font-size: 19px; font-weight: bold; padding: 6px; border-radius: 4px;")
        self.subtitle_label.setVisible(False)

        # Structure Application UI Window Splitters
        outer_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel layout structure logic
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel("Voltix Advanced Media Engine")
        self.title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #fab387; padding: 4px;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slider = QSlider(Qt.Orientation.Horizontal)

        # Toolbar layout implementation
        row = QHBoxLayout()
        self.open_btn = QPushButton("📁 Open")
        self.sub_btn = QPushButton("💬 Sub")
        self.play_btn = QPushButton("▶ / ⏸")
        self.stop_btn = QPushButton("⏹")
        self.settings_btn = QPushButton("⚙")

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(self.settings_data["volume"])
        self.volume.setFixedWidth(110)

        row.addWidget(self.open_btn)
        row.addWidget(self.sub_btn)
        row.addWidget(self.play_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.settings_btn)
        row.addSpacing(10)
        row.addWidget(QLabel("Speed:"))
        row.addWidget(self.speed_combo)
        row.addStretch()
        row.addWidget(QLabel("🔊"))
        row.addWidget(self.volume)

        left_layout.addWidget(self.title)
        # Fixed allocation layout assignment
        left_layout.addWidget(self.media_container, 10)
        left_layout.addWidget(self.time_label)
        left_layout.addWidget(self.slider)
        left_layout.addLayout(row)

        # Right Side Library Panel layout setup
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("<b>Media Library Panel</b>"))
        self.playlist_widget = QListWidget()
        right_layout.addWidget(self.playlist_widget)

        playlist_controls = QHBoxLayout()
        self.add_playlist_btn = QPushButton("+ Add to Playlist")
        self.clear_lib_btn = QPushButton("Clear History")
        playlist_controls.addWidget(self.add_playlist_btn)
        playlist_controls.addWidget(self.clear_lib_btn)
        right_layout.addLayout(playlist_controls)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([950, 350])
        outer_layout.addWidget(splitter)

        # Control Wiring Triggers
        self.open_btn.clicked.connect(self.open_file)
        self.sub_btn.clicked.connect(self.load_subtitles_dialog)
        self.play_btn.clicked.connect(self.play_pause)
        self.stop_btn.clicked.connect(self.stop_media)
        self.settings_btn.clicked.connect(self.open_settings)
        self.add_playlist_btn.clicked.connect(self.add_to_playlist_action)
        self.clear_lib_btn.clicked.connect(self.clear_library)
        self.playlist_widget.itemDoubleClicked.connect(
            self.playlist_item_selected)

        self.speed_combo.currentTextChanged.connect(self.change_speed)
        self.volume.valueChanged.connect(self.change_volume)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.slider.setMaximum)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.player.playbackStateChanged.connect(self.handle_state_change)

        self.refresh_library_panel()

        # Support running via open-with or arguments directly
        if len(sys.argv) > 1:
            if os.path.exists(sys.argv[1]):
                self.load_media_from_path(sys.argv[1])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Force the stacked layout engine to dynamically match container adjustments
        self.container_layout.setGeometry(
            0, 0, self.media_container.width(), self.media_container.height())
        self.reposition_overlays()

    def reposition_overlays(self):
        cw, ch = self.media_container.width(), self.media_container.height()
        self.center_play_btn.move(int((cw - 70) / 2), int((ch - 70) / 2))
        self.subtitle_label.setGeometry(15, ch - 75, cw - 30, 45)

    def load_media_from_path(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.title.setText(os.path.basename(path))
        self.container_layout.setCurrentIndex(1)
        db_add_file(path, "recent")
        self.refresh_library_panel()
        self.player.play()

        # Sibling subtitle lookups
        srt_guess = os.path.splitext(path)[0] + ".srt"
        if os.path.exists(srt_guess):
            self.subtitles = parse_srt(srt_guess)
        else:
            self.subtitles = []

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Media", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.mp3 *.wav *.flac *.ogg *.aac *.m4a);;All Files (*.*)"
        )
        if file_name:
            self.load_media_from_path(file_name)

    def load_subtitles_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Subtitle File", "", "Subtitles (*.srt)")
        if file_name:
            self.subtitles = parse_srt(file_name)

    # --- Drag & Drop ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                self.load_media_from_path(file_path)
                break

    def play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop_media(self):
        self.player.stop()
        self.container_layout.setCurrentIndex(0)
        self.subtitle_label.setVisible(False)
        self.title.setText("Voltix Advanced Media Engine")

    def change_volume(self, value):
        self.audio.setVolume(value / 100)
        self.settings_data["volume"] = value
        save_settings(self.settings_data)

    def change_speed(self, speed_str):
        factor = float(speed_str.replace("x", ""))
        self.player.setPlaybackRate(factor)

    def handle_state_change(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.center_play_btn.hide()
        else:
            self.center_play_btn.setText("▶")
            self.center_play_btn.show()

    def update_position(self, pos):
        self.slider.setValue(pos)
        dur = self.player.duration()

        pos_sec = pos // 1000
        dur_sec = dur // 1000

        self.time_label.setText(
            f"{pos_sec//3600:02}:{(pos_sec % 3600)//60:02}:{pos_sec % 60:02} / "
            f"{dur_sec//3600:02}:{(dur_sec % 3600)//60:02}:{dur_sec % 60:02}"
        )

        # Subtitle logic tracking synced frame indexes
        current_sub = ""
        for sub in self.subtitles:
            if sub["start"] <= pos <= sub["end"]:
                current_sub = sub["text"]
                break

        if current_sub:
            self.subtitle_label.setText(current_sub)
            self.subtitle_label.setVisible(True)
        else:
            self.subtitle_label.setVisible(False)

    def keyPressEvent(self, event):
        key = event.text().upper()
        binds = self.settings_data["keybinds"]

        if key == binds.get("open"):
            self.open_file()
        elif key == binds.get("settings"):
            self.open_settings()
        elif key == binds.get("fullscreen") or event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            self.play_pause()
        else:
            super().keyPressEvent(event)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.title.show()
        else:
            self.showFullScreen()
            self.title.hide()

    def open_settings(self):
        dlg = SettingsDialog(self.settings_data, self)
        if dlg.exec():
            save_settings(self.settings_data)

    # --- Media Library Mechanics ---
    def add_to_playlist_action(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Add Playlist Track", "", "All Media (*.*)")
        if file_name:
            db_add_file(file_name, "playlist")
            self.refresh_library_panel()

    def clear_library(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM library")
        conn.commit()
        conn.close()
        self.refresh_library_panel()

    def refresh_library_panel(self):
        self.playlist_widget.clear()

        playlist_items = db_get_files("playlist")
        if playlist_items:
            header = QListWidgetItem("📂 SAVED PLAYLIST")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.playlist_widget.addItem(header)
            for name, path in playlist_items:
                item = QListWidgetItem(f"  🎵 {name}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.playlist_widget.addItem(item)

        recents = db_get_files("recent")
        if recents:
            header = QListWidgetItem("🕒 RECENT FILES")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.playlist_widget.addItem(header)
            for name, path in recents:
                item = QListWidgetItem(f"  📄 {name}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.playlist_widget.addItem(item)

    def playlist_item_selected(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            self.load_media_from_path(path)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Configure global application icon natively
    icon_p = get_path("logo.ico")
    if os.path.exists(icon_p):
        app.setWindowIcon(QIcon(icon_p))

    player_app = Player()
    player_app.show()
    sys.exit(app.exec())
