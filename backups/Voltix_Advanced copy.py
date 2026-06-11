

import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtGui import QPixmap
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "volume": 100,
    "keybinds": {
        "open": "O",
        "play_pause": "Space",
        "settings": "S",
        "fullscreen": "F"
    }
}


def load_settings():
    if Path(SETTINGS_FILE).exists():
        try:
            return json.loads(Path(SETTINGS_FILE).read_text())
        except:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(data):
    Path(SETTINGS_FILE).write_text(json.dumps(data, indent=4))


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Voltix Settings")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Edit keybinds in settings.json for now."))

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)


class Player(QWidget):
    def __init__(self):
        super().__init__()

        self.settings_data = load_settings()

        self.setWindowTitle("Voltix Video Player")
        if Path("logo.png").exists():
            self.setWindowIcon(QIcon("logo.png"))

        self.resize(1200, 700)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(self.settings_data["volume"] / 100)
        self.video = QVideoWidget()

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if Path("logo.png").exists():
            pixmap = QPixmap("logo.png")
            self.logo_label.setPixmap(
                pixmap.scaled(
                    300,
                    300,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        self.media_stack = QStackedWidget()

        self.media_stack.addWidget(self.logo_label)
        self.media_stack.addWidget(self.video)

        self.player.setVideoOutput(self.video)

        self.title = QLabel("Voltix Video Player")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slider = QSlider(Qt.Orientation.Horizontal)

        self.open_btn = QPushButton("📁 Open")
        self.play_btn = QPushButton("▶/⏸")
        self.settings_btn = QPushButton("⚙")

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(self.settings_data["volume"])

        layout = QVBoxLayout(self)

        layout.addWidget(self.title)
        layout.addWidget(self.media_stack, 10)
        layout.addWidget(self.time_label)
        layout.addWidget(self.slider)

        row = QHBoxLayout()
        row.addWidget(self.open_btn)
        row.addWidget(self.play_btn)
        row.addWidget(self.settings_btn)
        row.addStretch()
        row.addWidget(self.volume)
        layout.addLayout(row)

        self.open_btn.clicked.connect(self.open_file)
        self.play_btn.clicked.connect(self.play_pause)
        self.settings_btn.clicked.connect(self.open_settings)

        self.volume.valueChanged.connect(self.change_volume)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.slider.setMaximum)
        self.slider.sliderMoved.connect(self.player.setPosition)

    def keyPressEvent(self, event):
        key = event.text().upper()

        if key == self.settings_data["keybinds"]["open"]:
            self.open_file()
        elif key == self.settings_data["keybinds"]["settings"]:
            self.open_settings()
        elif event.key() == Qt.Key.Key_Space:
            self.play_pause()
        elif key == self.settings_data["keybinds"]["fullscreen"]:
            self.video.setFullScreen(not self.video.isFullScreen())

    def open_settings(self):
        dlg = SettingsDialog(self.settings_data, self)
        dlg.exec()
        save_settings(self.settings_data)

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media",
            "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.wmv *.webm *.mp3 *.wav *.flac *.ogg *.aac *.m4a);;All Files (*.*)"
        )

        if file_name:
            self.player.setSource(QUrl.fromLocalFile(file_name))

            self.media_stack.setCurrentIndex(1)

            self.player.play()

    def play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def change_volume(self, value):
        self.audio.setVolume(value / 100)
        self.settings_data["volume"] = value
        save_settings(self.settings_data)

    def update_position(self, pos):
        self.slider.setValue(pos)

        s = pos // 1000
        ds = self.player.duration() // 1000

        self.time_label.setText(
            f"{s//60:02}:{s%60:02} / {ds//60:02}:{ds%60:02}"
        )

    def stop_media(self):
        self.player.stop()
        self.media_stack.setCurrentIndex(0)
        self.stop_btn = QPushButton("⏹")

        self.stop_btn.clicked.connect(self.stop_media)
        self.media_stack.setCurrentIndex(0)


app = QApplication(sys.argv)
w = Player()
w.show()
sys.exit(app.exec())
