from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from video_core import (
    PRESETS,
    VIDEO_CODECS,
    VideoError,
    VideoJob,
    VideoRunner,
    probe_duration,
    render_preview_frame,
)

VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}

OPERATION_LABELS = {
    "compress": "Compress",
    "trim": "Trim",
    "resize": "Resize",
    "crop": "Crop",
    "convert": "Convert",
    "extract_audio": "Extract audio",
    "mute": "Mute",
    "thumbnail": "Thumbnail",
}

APP_QSS = """
QMainWindow { background: #1e1e1e; }
QWidget { color: #eeeeee; font-family: Segoe UI; font-size: 13px; }
QFrame#topBar { background: #2b2b2b; border-bottom: 1px solid #454545; }
QFrame#toolBar { background: #303030; border-bottom: 1px solid #4b4b4b; }
QFrame#leftPanel { background: #3f3f3f; border-right: 1px solid #505050; }
QFrame#previewPanel { background: #5a5a5a; border-left: 1px solid #444444; }
QFrame#timelinePanel { background: #202020; border-top: 1px solid #4a4a4a; }
QFrame#timelineTools { background: #333333; border-top: 1px solid #505050; border-bottom: 1px solid #1a1a1a; }
QFrame#timelineRuler { background: #242424; border-bottom: 2px solid #777777; }
QFrame#monitor { background: #000000; border: 1px solid #111111; }
QFrame#mediaCard { background: #2b2b2b; border: 2px solid #555555; }
QFrame#mediaCard:hover { border: 2px solid #ffd400; }
QFrame#mediaCard[selected="true"] { border: 3px solid #ffd400; background: #252525; }
QFrame#mediaThumb { background: #111111; border: 1px solid #222222; }
QFrame#settingsPanel { background: #252525; border: 1px solid #555555; }
QFrame#timelineCanvas { background: #1f1f1f; border: 0px; }
QFrame#timelineClipItem { background: #000000; border: 4px solid #ffd400; }
QFrame#timelineClipItem[selected="true"] { border: 5px solid #ffd400; background: #050505; }
QFrame#clipThumb { background: #020202; border: 0px; }
QFrame#audioClip { background: #5d43c9; border: 2px solid #ffd400; }
QLabel#title { font-size: 14px; font-weight: 700; color: #ffffff; }
QLabel#mediaTitle { color: #ffffff; font-size: 12px; font-weight: 800; }
QLabel#mediaDuration { background: #000000; color: #ffffff; padding: 2px 5px; border-radius: 3px; }
QLabel#muted { color: #bbbbbb; }
QLabel#bigTitle { font-size: 27px; color: #ffffff; }
QLabel#timelineTime { color: #ffffff; font-weight: 700; }
QLabel#trackName { color: #ffffff; font-weight: 800; }
QLineEdit, QSpinBox { background: #191919; color: #ffffff; border: 1px solid #555555; border-radius: 2px; padding: 5px 7px; min-height: 22px; }
QLineEdit:focus, QSpinBox:focus { border: 1px solid #ffd400; }
QLineEdit:disabled, QSpinBox:disabled { background: #242424; color: #808080; border: 1px solid #3b3b3b; }
QComboBox { background: #191919; color: #ffffff; border: 1px solid #555555; border-radius: 2px; padding: 5px 28px 5px 7px; min-height: 22px; }
QComboBox:hover { border: 1px solid #777777; }
QComboBox:focus { border: 1px solid #ffd400; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border-left: 1px solid #444444; background: #151515; }
QComboBox::down-arrow { image: none; width: 0px; height: 0px; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #ffffff; margin-right: 7px; }
QComboBox QAbstractItemView { background: #191919; color: #ffffff; border: 1px solid #555555; selection-background-color: #ffd400; selection-color: #111111; outline: 0px; padding: 2px; }
QComboBox QAbstractItemView::item { background: #191919; color: #ffffff; min-height: 26px; padding: 5px 8px; }
QComboBox QAbstractItemView::item:hover { background: #333333; color: #ffffff; }
QComboBox QAbstractItemView::item:selected { background: #ffd400; color: #111111; }
QPushButton { background: #3a3a3a; color: #ffffff; border: 1px solid #555555; padding: 7px 11px; font-weight: 700; }
QPushButton:hover { background: #494949; border: 1px solid #777777; }
QPushButton:pressed { background: #242424; }
QPushButton:disabled { background: #2a2a2a; color: #777777; border: 1px solid #3a3a3a; }
QPushButton#yellowButton { background: #ffd400; color: #111111; border: 1px solid #ffd400; font-weight: 900; }
QPushButton#yellowButton:hover { background: #ffe45c; }
QPushButton#dangerButton { background: #3a2222; color: #ffd0d0; border: 1px solid #7a3a3a; }
QPushButton#toolButton { background: transparent; border: none; padding: 7px 10px; color: #eeeeee; }
QPushButton#toolButton:hover { background: #444444; }
QPushButton#activeToolButton { background: transparent; border: none; border-bottom: 3px solid #ffd400; padding: 7px 10px; color: #ffd400; }
QPushButton#playButton { background: transparent; border: none; font-size: 25px; color: #ffffff; }
QPushButton#playButton:hover { color: #ffd400; }
QPushButton#clipCloseButton { background: transparent; border: none; color: #ffffff; font-size: 26px; font-weight: 400; padding: 0px; }
QPushButton#clipCloseButton:hover { color: #ffd400; }
QCheckBox { spacing: 8px; color: #eeeeee; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #777777; background: #111111; }
QCheckBox::indicator:checked { background: #ffd400; border: 1px solid #ffd400; }
QProgressBar { background: #111111; border: 1px solid #555555; height: 12px; text-align: center; color: transparent; }
QProgressBar::chunk { background: #ffd400; }
QSlider::groove:horizontal { height: 4px; background: #c8c8c8; }
QSlider::handle:horizontal { width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; background: #ffffff; }
QScrollArea { background: transparent; border: none; }
QScrollArea QWidget { background: transparent; }
QScrollBar:vertical { background: #333333; width: 10px; }
QScrollBar::handle:vertical { background: #777777; min-height: 30px; }
QScrollBar:horizontal { background: #333333; height: 10px; }
QScrollBar::handle:horizontal { background: #777777; min-width: 30px; }
"""


class RenderWorker(QObject):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, job: VideoJob) -> None:
        super().__init__()
        self.job = job
        self.runner = VideoRunner()

    def run(self) -> None:
        try:
            self.runner.run(self.job, on_progress=self.progress.emit, on_log=self.log.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        self.runner.cancel()


class PreviewWorker(QObject):
    ready = pyqtSignal(str, str)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, key: str, job: VideoJob, preview_path: Path, preview_time: str | None) -> None:
        super().__init__()
        self.key = key
        self.job = job
        self.preview_path = preview_path
        self.preview_time = preview_time

    def run(self) -> None:
        try:
            render_preview_frame(self.job, self.preview_path, self.preview_time)
            self.ready.emit(self.key, str(self.preview_path))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class TimelineCanvas(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("timelineCanvas")
        self.setMinimumHeight(300)
        self.setMinimumWidth(2400)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#1f1f1f"))

        minor = QPen(QColor("#2b2b2b"))
        major = QPen(QColor("#3a3a3a"))
        for x in range(0, self.width(), 180):
            painter.setPen(major if x % 720 == 0 else minor)
            painter.drawLine(x, 0, x, self.height())

        painter.setPen(QPen(QColor("#777777"), 2))
        painter.drawLine(0, 0, self.width(), 0)

        painter.setPen(QPen(QColor("#777777"), 3))
        painter.drawLine(0, 0, 0, self.height())
        painter.setBrush(QColor("#303030"))
        painter.drawEllipse(-8, -8, 22, 22)


class MediaCard(QFrame):
    clicked = pyqtSignal(Path)

    def __init__(self, path: Path, duration_text: str) -> None:
        super().__init__()
        self.path = path
        self.setObjectName("mediaCard")
        self.setProperty("selected", False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumSize(128, 126)
        self.setMaximumWidth(170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        self.thumb_frame = QFrame()
        self.thumb_frame.setObjectName("mediaThumb")
        self.thumb_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.thumb_frame.setMinimumSize(112, 78)

        thumb_layout = QVBoxLayout(self.thumb_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        self.thumb_label = QLabel("VIDEO")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setObjectName("muted")
        thumb_layout.addWidget(self.thumb_label)

        title = QLabel(self._short_name(path.stem))
        title.setObjectName("mediaTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        duration = QLabel(duration_text)
        duration.setObjectName("mediaDuration")
        duration.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.thumb_frame)
        layout.addWidget(title)
        layout.addWidget(duration, alignment=Qt.AlignmentFlag.AlignRight)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.path)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(self.thumb_frame.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.thumb_label.setPixmap(scaled)
        self.thumb_label.setText("")

    def _short_name(self, value: str, limit: int = 19) -> str:
        return value if len(value) <= limit else value[: limit - 1] + "…"


class TimelineClip(QFrame):
    clicked = pyqtSignal(int)
    remove_clicked = pyqtSignal(int)

    def __init__(self, index: int, path: Path, duration_text: str, pixmap: QPixmap | None = None) -> None:
        super().__init__()
        self.index = index
        self.path = path
        self.setObjectName("timelineClipItem")
        self.setProperty("selected", False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(185, 260)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addStretch()
        close = QPushButton("×")
        close.setObjectName("clipCloseButton")
        close.setFixedSize(30, 30)
        close.clicked.connect(lambda: self.remove_clicked.emit(self.index))
        top.addWidget(close)
        root.addLayout(top)

        self.thumb = QLabel("")
        self.thumb.setObjectName("muted")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setFrameShape(QFrame.Shape.NoFrame)
        self.thumb.setMinimumHeight(125)
        self.thumb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.thumb.setStyleSheet("background:#000000;")
        root.addWidget(self.thumb, stretch=1)

        title = QLabel(path.name)
        title.setObjectName("mediaTitle")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        root.addWidget(title)

        bottom = QHBoxLayout()
        bottom.addStretch()
        duration = QLabel(duration_text)
        duration.setObjectName("mediaDuration")
        bottom.addWidget(duration)
        root.addLayout(bottom)

        if pixmap is not None and not pixmap.isNull():
            self.set_thumbnail(pixmap)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        scaled = pixmap.scaled(165, 125, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.thumb.setPixmap(scaled)
        self.thumb.setText("")


class VideoToolWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.media_paths: list[Path] = []
        self.media_cards: dict[Path, MediaCard] = {}
        self.timeline_paths: list[Path] = []
        self.timeline_widgets: list[TimelineClip] = []
        self.current_input_path: Path | None = None

        self.render_thread: QThread | None = None
        self.render_worker: RenderWorker | None = None
        self.preview_thread: QThread | None = None
        self.preview_worker: PreviewWorker | None = None

        self.temp_dir = tempfile.TemporaryDirectory()
        self.thumb_cache: dict[Path, QPixmap] = {}
        self.slider_is_pressed = False

        self.setWindowTitle("Chisp Video Editor")
        self.resize(1600, 920)
        self.setMinimumSize(1180, 720)
        self.setAcceptDrops(True)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.85)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background:#000000;")
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.add_files_btn = QPushButton("+ Add files")
        self.add_files_btn.setObjectName("yellowButton")
        self.add_color_btn = QPushButton("◉ Add color")
        self.add_color_btn.setObjectName("toolButton")
        self.voiceover_btn = QPushButton("🎙 Voiceover")
        self.voiceover_btn.setObjectName("toolButton")
        self.subtitles_btn = QPushButton("CC Subtitles")
        self.subtitles_btn.setObjectName("toolButton")
        self.export_btn = QPushButton("Export video")
        self.export_btn.setObjectName("yellowButton")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setEnabled(False)
        self.clear_timeline_btn = QPushButton("✕ Clear timeline")
        self.clear_timeline_btn.setObjectName("toolButton")

        self.operation_combo = QComboBox()
        for key, label in OPERATION_LABELS.items():
            self.operation_combo.addItem(label, key)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(VIDEO_CODECS)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS)
        self.preset_combo.setCurrentText("medium")

        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(24)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(0, 16000)
        self.width_spin.setSpecialValueText("Source")
        self.width_spin.setValue(0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(0, 16000)
        self.height_spin.setSpecialValueText("Source")
        self.height_spin.setValue(0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(0, 240)
        self.fps_spin.setSpecialValueText("Source")
        self.fps_spin.setValue(0)
        self.crop_x_spin = QSpinBox()
        self.crop_x_spin.setRange(0, 16000)
        self.crop_y_spin = QSpinBox()
        self.crop_y_spin.setRange(0, 16000)
        self.crop_w_spin = QSpinBox()
        self.crop_w_spin.setRange(0, 16000)
        self.crop_w_spin.setValue(1280)
        self.crop_h_spin = QSpinBox()
        self.crop_h_spin.setRange(0, 16000)
        self.crop_h_spin.setValue(720)

        self.start_edit = QLineEdit("0")
        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("End")
        self.duration_edit = QLineEdit()
        self.duration_edit.setPlaceholderText("Duration")
        self.preview_time_edit = QLineEdit("0")
        self.preview_time_edit.setMaximumWidth(100)
        self.audio_bitrate_edit = QLineEdit("128k")
        self.no_audio_check = QCheckBox("No audio")
        self.copy_mode_check = QCheckBox("Copy mode")
        self.overwrite_check = QCheckBox("Overwrite")
        self.overwrite_check.setChecked(True)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output path")
        self.output_btn = QPushButton("Browse")

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("playButton")
        self.preview_slider = QSlider(Qt.Orientation.Horizontal)
        self.preview_slider.setRange(0, 0)
        self.time_left_label = QLabel("00:00.0")
        self.time_left_label.setObjectName("muted")
        self.time_right_label = QLabel("00:00")
        self.time_right_label.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("muted")
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("muted")
        self.timeline_duration_label = QLabel("")
        self.timeline_duration_label.setObjectName("timelineTime")

        self._build_layout()
        self._connect()
        self._refresh_operation_state()
        self._style_combo_popups()
        self.rebuild_timeline()

    def _build_layout(self) -> None:
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self._build_top_bar())
        main.addWidget(self._build_toolbar())

        center_splitter = QSplitter(Qt.Orientation.Horizontal)
        center_splitter.setChildrenCollapsible(False)
        center_splitter.addWidget(self._build_media_library())
        center_splitter.addWidget(self._build_preview_area())
        center_splitter.setSizes([820, 780])

        main.addWidget(center_splitter, stretch=1)
        main.addWidget(self._build_timeline_tools())
        main.addWidget(self._build_timeline_area())
        self.setCentralWidget(root)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)
        title = QLabel("Chisp Video Editor")
        title.setObjectName("title")
        project = QLabel("- Drag videos here and edit timeline")
        project.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(project)
        layout.addStretch()
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.export_btn)
        return bar

    def _build_toolbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("toolBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        media_title = QLabel("Media Library")
        media_title.setObjectName("bigTitle")
        layout.addWidget(media_title)
        layout.addSpacing(8)
        layout.addWidget(self.add_files_btn)
        layout.addWidget(self.add_color_btn)
        for text in ["✱", "▦", "▥", "♪", "⌕", "▣"]:
            btn = QPushButton(text)
            btn.setObjectName("toolButton")
            layout.addWidget(btn)
        layout.addStretch()
        layout.addWidget(QLabel("Operation:"))
        layout.addWidget(self.operation_combo)
        layout.addWidget(QLabel("Codec:"))
        layout.addWidget(self.codec_combo)
        layout.addWidget(QLabel("CRF:"))
        self.crf_spin.setMaximumWidth(70)
        layout.addWidget(self.crf_spin)
        layout.addWidget(self.voiceover_btn)
        layout.addWidget(self.subtitles_btn)
        aspect = QLabel("16:9 Landscape")
        aspect.setObjectName("muted")
        layout.addWidget(aspect)
        return bar

    def _build_media_library(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setAcceptDrops(True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.media_grid_widget = QWidget()
        self.media_grid = QGridLayout(self.media_grid_widget)
        self.media_grid.setContentsMargins(0, 0, 0, 0)
        self.media_grid.setSpacing(12)
        self.media_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.media_grid_widget)
        layout.addWidget(scroll)
        layout.addWidget(self._build_export_settings_strip())
        return panel

    def _build_export_settings_strip(self) -> QWidget:
        box = QFrame()
        box.setObjectName("settingsPanel")
        layout = QGridLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.addWidget(QLabel("Output:"), 0, 0)
        layout.addWidget(self.output_edit, 0, 1, 1, 5)
        layout.addWidget(self.output_btn, 0, 6)
        layout.addWidget(QLabel("Preset:"), 1, 0)
        layout.addWidget(self.preset_combo, 1, 1)
        layout.addWidget(QLabel("W:"), 1, 2)
        layout.addWidget(self.width_spin, 1, 3)
        layout.addWidget(QLabel("H:"), 1, 4)
        layout.addWidget(self.height_spin, 1, 5)
        layout.addWidget(QLabel("FPS:"), 1, 6)
        layout.addWidget(self.fps_spin, 1, 7)
        layout.addWidget(QLabel("Start:"), 2, 0)
        layout.addWidget(self.start_edit, 2, 1)
        layout.addWidget(QLabel("End:"), 2, 2)
        layout.addWidget(self.end_edit, 2, 3)
        layout.addWidget(QLabel("Duration:"), 2, 4)
        layout.addWidget(self.duration_edit, 2, 5)
        layout.addWidget(QLabel("Crop X:"), 3, 0)
        layout.addWidget(self.crop_x_spin, 3, 1)
        layout.addWidget(QLabel("Crop Y:"), 3, 2)
        layout.addWidget(self.crop_y_spin, 3, 3)
        layout.addWidget(QLabel("Crop W:"), 3, 4)
        layout.addWidget(self.crop_w_spin, 3, 5)
        layout.addWidget(QLabel("Crop H:"), 3, 6)
        layout.addWidget(self.crop_h_spin, 3, 7)
        layout.addWidget(QLabel("Audio:"), 4, 0)
        layout.addWidget(self.audio_bitrate_edit, 4, 1)
        layout.addWidget(self.no_audio_check, 4, 2)
        layout.addWidget(self.copy_mode_check, 4, 3)
        layout.addWidget(self.overwrite_check, 4, 4)
        return box

    def _build_preview_area(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(38, 28, 38, 18)
        layout.setSpacing(12)
        monitor = QFrame()
        monitor.setObjectName("monitor")
        monitor_layout = QVBoxLayout(monitor)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        monitor_layout.addWidget(self.video_widget)
        layout.addWidget(monitor, stretch=1)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.time_left_label)
        controls.addWidget(self.preview_slider, stretch=1)
        controls.addWidget(self.time_right_label)
        controls.addWidget(QLabel("🔊"))
        controls.addWidget(QLabel("⛶"))
        layout.addLayout(controls)
        preview_row = QHBoxLayout()
        preview_row.addStretch()
        preview_row.addWidget(QLabel("Preview time:"))
        preview_row.addWidget(self.preview_time_edit)
        update_preview_btn = QPushButton("Update thumbnail")
        update_preview_btn.clicked.connect(self.start_preview)
        preview_row.addWidget(update_preview_btn)
        layout.addLayout(preview_row)
        return panel

    def _build_timeline_tools(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("timelineTools")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(10)
        tools = [
            ("⚙ General", "toolButton"),
            ("⚙ Audio", "toolButton"),
            ("✂ Trim", "activeToolButton"),
            ("◧ Crop", "toolButton"),
            ("T Text", "toolButton"),
            ("▤ Filters", "toolButton"),
            ("▣ PiP", "toolButton"),
            ("☻ Stickers", "toolButton"),
            ("↔ Split", "toolButton"),
        ]
        for text, obj in tools:
            button = QPushButton(text)
            button.setObjectName(obj)
            layout.addWidget(button)
        layout.addStretch()
        layout.addWidget(QLabel("↶"))
        layout.addWidget(QLabel("↷"))
        layout.addSpacing(8)
        layout.addWidget(self.clear_timeline_btn)
        layout.addSpacing(12)
        layout.addWidget(self.status_label)
        layout.addSpacing(8)
        layout.addWidget(self.percent_label)
        self.progress.setMaximumWidth(220)
        layout.addWidget(self.progress)
        return bar

    def _build_timeline_area(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("timelinePanel")
        panel.setMinimumHeight(330)
        panel.setAcceptDrops(True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        ruler = QFrame()
        ruler.setObjectName("timelineRuler")
        ruler.setFixedHeight(34)
        ruler_layout = QHBoxLayout(ruler)
        ruler_layout.setContentsMargins(8, 0, 8, 0)
        ruler_layout.addWidget(QLabel("0"))
        ruler_layout.addSpacing(160)
        ruler_layout.addWidget(self.timeline_duration_label)
        ruler_layout.addStretch()
        layout.addWidget(ruler)

        timeline_scroll = QScrollArea()
        timeline_scroll.setWidgetResizable(False)
        timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_canvas = TimelineCanvas()
        self.timeline_layout = QHBoxLayout(self.timeline_canvas)
        self.timeline_layout.setContentsMargins(14, 18, 14, 14)
        self.timeline_layout.setSpacing(12)
        self.timeline_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        timeline_scroll.setWidget(self.timeline_canvas)
        layout.addWidget(timeline_scroll, stretch=1)

        audio_track = QFrame()
        audio_track.setObjectName("audioClip")
        audio_track.setFixedHeight(44)
        audio_layout = QHBoxLayout(audio_track)
        audio_layout.setContentsMargins(10, 4, 10, 4)
        audio_name = QLabel("Audio")
        audio_name.setObjectName("trackName")
        audio_name.setFixedWidth(70)
        self.audio_track_label = QLabel("audio follows video clips")
        self.audio_track_label.setObjectName("muted")
        audio_layout.addWidget(audio_name)
        audio_layout.addWidget(self.audio_track_label)
        layout.addWidget(audio_track)
        return panel

    def _connect(self) -> None:
        self.add_files_btn.clicked.connect(self.add_files)
        self.export_btn.clicked.connect(self.start_render)
        self.cancel_btn.clicked.connect(self.cancel_render)
        self.output_btn.clicked.connect(self.choose_output_file)
        self.play_btn.clicked.connect(self.play_pause)
        self.clear_timeline_btn.clicked.connect(self.clear_timeline)
        self.operation_combo.currentIndexChanged.connect(self._refresh_operation_state)
        self.operation_combo.currentIndexChanged.connect(self.refresh_output_suggestion)
        self.player.positionChanged.connect(self.player_position_changed)
        self.player.durationChanged.connect(self.player_duration_changed)
        self.player.playbackStateChanged.connect(self.player_state_changed)
        self.player.errorOccurred.connect(self.player_error)
        self.preview_slider.sliderPressed.connect(self.slider_pressed)
        self.preview_slider.sliderReleased.connect(self.slider_released)
        self.preview_slider.sliderMoved.connect(self.seek_video)

    def _style_combo_popups(self) -> None:
        popup_qss = """
        QListView { background: #191919; color: #ffffff; border: 1px solid #555555; outline: 0px; selection-background-color: #ffd400; selection-color: #111111; }
        QListView::item { background: #191919; color: #ffffff; min-height: 26px; padding: 5px 8px; }
        QListView::item:hover { background: #333333; color: #ffffff; }
        QListView::item:selected { background: #ffd400; color: #111111; }
        """
        for combo in (self.operation_combo, self.codec_combo, self.preset_combo):
            combo.view().setStyleSheet(popup_qss)

    def dragEnterEvent(self, event) -> None:
        if self.paths_from_drop(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        paths = self.paths_from_drop(event)
        if paths:
            self.add_paths(paths, append_to_timeline=True, select_first=True)
            event.acceptProposedAction()

    def paths_from_drop(self, event) -> list[Path]:
        data = event.mimeData()
        if not data.hasUrls():
            return []
        paths: list[Path] = []
        for url in data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
                paths.append(path)
        return paths

    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add video files",
            "",
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v);;All files (*.*)",
        )
        self.add_paths([Path(raw) for raw in paths], append_to_timeline=True, select_first=True)

    def add_paths(self, paths: list[Path], *, append_to_timeline: bool, select_first: bool) -> None:
        clean_paths = [path.expanduser().resolve() for path in paths if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES]
        if not clean_paths:
            return
        for path in clean_paths:
            if path not in self.media_paths:
                self.media_paths.append(path)
            if append_to_timeline:
                self.timeline_paths.append(path)
        self.rebuild_media_grid()
        self.rebuild_timeline()
        if select_first:
            self.select_media(clean_paths[0])
        elif self.current_input_path is None and self.timeline_paths:
            self.select_media(self.timeline_paths[0])
        if not self.output_edit.text().strip() and self.timeline_paths:
            self.output_edit.setText(str(self.suggest_output_path(self.timeline_paths[0])))

    def rebuild_media_grid(self) -> None:
        while self.media_grid.count():
            item = self.media_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.media_cards.clear()
        columns = 5
        for index, path in enumerate(self.media_paths):
            card = MediaCard(path, self.duration_text(path))
            card.clicked.connect(self.select_media)
            self.media_cards[path] = card
            self.media_grid.addWidget(card, index // columns, index % columns)
            if path in self.thumb_cache:
                card.set_thumbnail(self.thumb_cache[path])
        self.update_selected_cards()

    def rebuild_timeline(self) -> None:
        while self.timeline_layout.count():
            item = self.timeline_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.timeline_widgets.clear()
        if not self.timeline_paths:
            placeholder = QLabel("Drop videos here. Multiple clips will be joined on export.")
            placeholder.setObjectName("muted")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setMinimumSize(500, 220)
            self.timeline_layout.addWidget(placeholder)
            self.timeline_layout.addStretch()
            self.timeline_duration_label.setText("")
            self.audio_track_label.setText("audio follows video clips")
            self.timeline_canvas.update()
            return
        total = 0
        for index, path in enumerate(self.timeline_paths):
            duration_text = self.duration_text(path)
            total += self.duration_seconds(path)
            clip = TimelineClip(index, path, duration_text, self.thumb_cache.get(path))
            clip.clicked.connect(self.select_timeline_clip)
            clip.remove_clicked.connect(self.remove_timeline_clip)
            self.timeline_widgets.append(clip)
            self.timeline_layout.addWidget(clip)
        self.timeline_layout.addStretch()
        self.timeline_duration_label.setText(self.format_seconds(total))
        self.audio_track_label.setText(f"{len(self.timeline_paths)} clip(s) audio")
        self.update_timeline_selection()
        self.timeline_canvas.update()

    def clear_timeline(self) -> None:
        self.timeline_paths.clear()
        self.current_input_path = None
        self.player.stop()
        self.player.setSource(QUrl())
        self.rebuild_timeline()
        self.update_selected_cards()
        self.time_left_label.setText("00:00.0")
        self.time_right_label.setText("00:00")
        self.preview_slider.setRange(0, 0)

    def select_media(self, path: Path) -> None:
        self.current_input_path = path
        self.update_selected_cards()
        self.update_timeline_selection()
        if not self.output_edit.text().strip():
            self.output_edit.setText(str(self.suggest_output_path(path)))
        self.load_player(path)
        self.start_preview()

    def select_timeline_clip(self, index: int) -> None:
        if 0 <= index < len(self.timeline_paths):
            self.select_media(self.timeline_paths[index])

    def remove_timeline_clip(self, index: int) -> None:
        if 0 <= index < len(self.timeline_paths):
            removed = self.timeline_paths.pop(index)
            if self.current_input_path == removed:
                self.current_input_path = self.timeline_paths[0] if self.timeline_paths else None
            self.rebuild_timeline()
            if self.current_input_path:
                self.select_media(self.current_input_path)
            else:
                self.player.stop()
                self.player.setSource(QUrl())
                self.update_selected_cards()

    def update_selected_cards(self) -> None:
        for path, card in self.media_cards.items():
            card.set_selected(path == self.current_input_path)

    def update_timeline_selection(self) -> None:
        for widget in self.timeline_widgets:
            widget.set_selected(widget.path == self.current_input_path)

    def load_player(self, path: Path) -> None:
        self.player.stop()
        self.player.setVideoOutput(self.video_widget)
        self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.time_left_label.setText("00:00.0")
        self.time_right_label.setText(self.duration_text(path))
        self.preview_slider.setValue(0)

    def play_pause(self) -> None:
        if self.current_input_path is None:
            QMessageBox.information(self, "No video", "Drag a video into the editor first.")
            return
        if self.player.source().isEmpty():
            self.load_player(self.current_input_path)
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def player_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.play_btn.setText("⏸" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

    def player_position_changed(self, position: int) -> None:
        if not self.slider_is_pressed:
            self.preview_slider.setValue(position)
        self.time_left_label.setText(self.format_msec(position, with_tenths=True))

    def player_duration_changed(self, duration: int) -> None:
        self.preview_slider.setRange(0, max(0, duration))
        if duration > 0:
            self.time_right_label.setText(self.format_msec(duration))

    def player_error(self, _error, error_string: str) -> None:
        if error_string:
            self.status_label.setText("Playback error")
            QMessageBox.warning(self, "Playback error", error_string)

    def slider_pressed(self) -> None:
        self.slider_is_pressed = True

    def slider_released(self) -> None:
        self.slider_is_pressed = False
        self.player.setPosition(self.preview_slider.value())

    def seek_video(self, value: int) -> None:
        self.time_left_label.setText(self.format_msec(value, with_tenths=True))

    def current_operation(self) -> str:
        return str(self.operation_combo.currentData())

    def _refresh_operation_state(self) -> None:
        operation = self.current_operation()
        is_video_encode = operation in {"compress", "resize", "crop", "convert", "trim"}
        is_resize = operation in {"compress", "resize", "crop"}
        is_trim_like = operation in {"trim", "extract_audio", "thumbnail"}
        is_crop = operation == "crop"
        is_compress = operation == "compress"
        is_copy_supported = operation in {"trim", "convert"}
        self.codec_combo.setEnabled(is_video_encode)
        self.preset_combo.setEnabled(is_video_encode)
        self.crf_spin.setEnabled(is_video_encode)
        self.width_spin.setEnabled(is_resize)
        self.height_spin.setEnabled(is_resize)
        self.fps_spin.setEnabled(operation in {"compress", "resize"})
        self.start_edit.setEnabled(is_trim_like)
        self.end_edit.setEnabled(operation == "trim")
        self.duration_edit.setEnabled(operation in {"trim", "extract_audio"})
        self.crop_x_spin.setEnabled(is_crop)
        self.crop_y_spin.setEnabled(is_crop)
        self.crop_w_spin.setEnabled(is_crop)
        self.crop_h_spin.setEnabled(is_crop)
        self.no_audio_check.setEnabled(is_compress)
        self.copy_mode_check.setEnabled(is_copy_supported)
        if not is_copy_supported:
            self.copy_mode_check.setChecked(False)

    def choose_output_file(self) -> None:
        operation = self.current_operation()
        if len(self.timeline_paths) > 1:
            file_filter = "Video files (*.mp4 *.mkv *.mov *.avi *.webm);;All files (*.*)"
        elif operation == "extract_audio":
            file_filter = "Audio files (*.mp3 *.m4a *.aac *.wav);;All files (*.*)"
        elif operation == "thumbnail":
            file_filter = "Image files (*.jpg *.jpeg *.png *.webp);;All files (*.*)"
        else:
            file_filter = "Video files (*.mp4 *.mkv *.mov *.avi *.webm);;All files (*.*)"
        path, _ = QFileDialog.getSaveFileName(self, "Export video", "", file_filter)
        if path:
            self.output_edit.setText(path)

    def suggest_output_path(self, input_path: Path) -> Path:
        operation = "joined" if len(self.timeline_paths) > 1 else self.current_operation()
        suffix = input_path.suffix or ".mp4"
        if operation == "extract_audio":
            suffix = ".mp3"
        elif operation == "thumbnail":
            suffix = ".jpg"
        elif operation == "joined":
            suffix = ".mp4"
        return input_path.with_name(f"{input_path.stem}_{operation}{suffix}")

    def refresh_output_suggestion(self) -> None:
        source = self.timeline_paths[0] if self.timeline_paths else self.current_input_path
        if source is None:
            return
        output_text = self.output_edit.text().strip()
        if not output_text:
            self.output_edit.setText(str(self.suggest_output_path(source)))
            return
        output_path = Path(output_text)
        tags = set(OPERATION_LABELS) | {"joined"}
        if any(tag in output_path.stem for tag in tags):
            self.output_edit.setText(str(self.suggest_output_path(source)))

    def optional_int(self, spin: QSpinBox) -> int | None:
        value = spin.value()
        return None if value <= 0 else value

    def build_job(self, *, allow_missing_output: bool = False) -> VideoJob:
        if not self.timeline_paths and self.current_input_path is None:
            raise VideoError("Спочатку перетягни відео в редактор")
        input_paths = tuple(self.timeline_paths) if self.timeline_paths else (self.current_input_path,)  # type: ignore[arg-type]
        input_path = input_paths[0]
        operation = "concat" if len(input_paths) > 1 else self.current_operation()
        output_text = self.output_edit.text().strip()
        if not output_text:
            output_text = str(self.suggest_output_path(input_path))
            if not allow_missing_output:
                self.output_edit.setText(output_text)
        return VideoJob(
            operation=operation,
            input_path=input_path,
            output_path=Path(output_text),
            input_paths=input_paths if operation == "concat" else None,
            crf=self.crf_spin.value(),
            preset=self.preset_combo.currentText(),
            codec=self.codec_combo.currentText(),
            width=self.optional_int(self.width_spin),
            height=self.optional_int(self.height_spin),
            fps=self.optional_int(self.fps_spin),
            start=self.start_edit.text().strip() or None,
            end=self.end_edit.text().strip() or None,
            duration=self.duration_edit.text().strip() or None,
            crop_x=self.crop_x_spin.value(),
            crop_y=self.crop_y_spin.value(),
            crop_w=self.optional_int(self.crop_w_spin),
            crop_h=self.optional_int(self.crop_h_spin),
            audio_bitrate=self.audio_bitrate_edit.text().strip() or "128k",
            no_audio=self.no_audio_check.isChecked(),
            copy_mode=self.copy_mode_check.isChecked(),
            overwrite=self.overwrite_check.isChecked(),
        )

    def start_preview(self) -> None:
        if self.preview_thread is not None and self.preview_thread.isRunning():
            return
        if self.current_input_path is None:
            return
        job = VideoJob(
            operation=self.current_operation(),
            input_path=self.current_input_path,
            output_path=Path(self.temp_dir.name) / "dummy.mp4",
            crf=self.crf_spin.value(),
            preset=self.preset_combo.currentText(),
            codec=self.codec_combo.currentText(),
            width=self.optional_int(self.width_spin),
            height=self.optional_int(self.height_spin),
            fps=self.optional_int(self.fps_spin),
            crop_x=self.crop_x_spin.value(),
            crop_y=self.crop_y_spin.value(),
            crop_w=self.optional_int(self.crop_w_spin),
            crop_h=self.optional_int(self.crop_h_spin),
        )
        preview_path = Path(self.temp_dir.name) / f"thumb_{abs(hash(str(self.current_input_path)))}.jpg"
        preview_time = self.preview_time_edit.text().strip() or "0"
        thread = QThread(self)
        worker = PreviewWorker(str(self.current_input_path), job, preview_path, preview_time)
        worker.moveToThread(thread)
        self.preview_thread = thread
        self.preview_worker = worker
        thread.started.connect(worker.run)
        worker.ready.connect(self.thumbnail_ready)
        worker.failed.connect(lambda _message: None)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self.preview_thread_finished)
        thread.start()

    def thumbnail_ready(self, key: str, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        source = Path(key)
        self.thumb_cache[source] = pixmap
        if source in self.media_cards:
            self.media_cards[source].set_thumbnail(pixmap)
        for clip in self.timeline_widgets:
            if clip.path == source:
                clip.set_thumbnail(pixmap)

    def preview_thread_finished(self) -> None:
        self.preview_worker = None
        self.preview_thread = None

    def start_render(self) -> None:
        if self.render_thread is not None and self.render_thread.isRunning():
            return
        try:
            job = self.build_job()
        except VideoError as exc:
            QMessageBox.warning(self, "Export error", str(exc))
            return
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Starting export...")
        thread = QThread(self)
        worker = RenderWorker(job)
        worker.moveToThread(thread)
        self.render_thread = thread
        self.render_worker = worker
        thread.started.connect(worker.run)
        worker.progress.connect(self.on_progress)
        worker.failed.connect(self.render_failed)
        worker.finished.connect(self.render_worker_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self.render_thread_finished)
        self.set_running_state(True)
        thread.start()

    def cancel_render(self) -> None:
        if self.render_worker:
            self.render_worker.cancel()
        self.status_label.setText("Cancelling...")

    def on_progress(self, value: int) -> None:
        self.progress.setValue(value)
        self.percent_label.setText(f"{value}%")
        self.status_label.setText("Export complete" if value >= 100 else "Exporting...")

    def render_failed(self, message: str) -> None:
        self.status_label.setText("Export failed")
        if "скасовано" not in message.lower() and "cancelled" not in message.lower():
            QMessageBox.critical(self, "Export error", message)

    def render_worker_finished(self) -> None:
        self.set_running_state(False)

    def render_thread_finished(self) -> None:
        self.render_worker = None
        self.render_thread = None

    def set_running_state(self, running: bool) -> None:
        self.export_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        self.add_files_btn.setEnabled(not running)
        self.output_btn.setEnabled(not running)
        self.operation_combo.setEnabled(not running)

    def duration_seconds(self, path: Path) -> int:
        try:
            return int(probe_duration(path))
        except Exception:
            return 0

    def duration_text(self, path: Path) -> str:
        return self.format_seconds(self.duration_seconds(path))

    def format_seconds(self, seconds: int) -> str:
        if seconds <= 0:
            return "00:00"
        minutes = seconds // 60
        sec = seconds % 60
        if minutes >= 60:
            hours = minutes // 60
            minutes %= 60
            return f"{hours:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"

    def format_msec(self, msec: int, *, with_tenths: bool = False) -> str:
        total_seconds = max(0, msec) / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        if with_tenths:
            return f"{minutes:02d}:{seconds:04.1f}"
        return f"{minutes:02d}:{int(seconds):02d}"

    def closeEvent(self, event) -> None:
        self.player.stop()
        if self.render_thread and self.render_thread.isRunning():
            reply = QMessageBox.question(self, "Close?", "Export is still running. Cancel and close?")
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            if self.render_worker:
                self.render_worker.cancel()
            self.render_thread.quit()
            self.render_thread.wait(3000)
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.quit()
            self.preview_thread.wait(3000)
        self.temp_dir.cleanup()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = VideoToolWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
