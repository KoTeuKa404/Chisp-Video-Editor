from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
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
    QTextEdit,
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
QMainWindow {
    background: #1e1e1e;
}

QWidget {
    color: #eeeeee;
    font-family: Segoe UI;
    font-size: 13px;
}

QFrame#topBar {
    background: #2b2b2b;
    border-bottom: 1px solid #454545;
}

QFrame#toolBar {
    background: #303030;
    border-bottom: 1px solid #4b4b4b;
}

QFrame#leftPanel {
    background: #3f3f3f;
    border-right: 1px solid #505050;
}

QFrame#previewPanel {
    background: #5a5a5a;
    border-left: 1px solid #444444;
}

QFrame#timelinePanel {
    background: #202020;
    border-top: 1px solid #4a4a4a;
}

QFrame#timelineTools {
    background: #333333;
    border-top: 1px solid #505050;
    border-bottom: 1px solid #1a1a1a;
}

QFrame#monitor {
    background: #000000;
    border: 1px solid #111111;
}

QFrame#mediaCard {
    background: #2b2b2b;
    border: 2px solid #555555;
}

QFrame#mediaCard:hover {
    border: 2px solid #ffd400;
}

QFrame#mediaCard[selected="true"] {
    border: 3px solid #ffd400;
    background: #252525;
}

QFrame#mediaThumb {
    background: #111111;
    border: 1px solid #222222;
}

QFrame#timelineClip {
    background: #050505;
    border: 1px solid #000000;
}

QFrame#audioClip {
    background: #5d43c9;
    border: 2px solid #ffd400;
}

QFrame#settingsPopup {
    background: #252525;
    border: 1px solid #555555;
}

QLabel#title {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#mediaTitle {
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
}

QLabel#mediaDuration {
    background: #000000;
    color: #ffffff;
    padding: 2px 5px;
    border-radius: 3px;
}

QLabel#muted {
    color: #bbbbbb;
}

QLabel#bigTitle {
    font-size: 27px;
    color: #ffffff;
}

QLabel#timelineTime {
    color: #ffffff;
    font-weight: 700;
}

QLabel#trackName {
    color: #cccccc;
    font-weight: 700;
}

QLineEdit, QComboBox, QSpinBox {
    background: #191919;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 2px;
    padding: 5px 7px;
    min-height: 22px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #ffd400;
}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background: #242424;
    color: #808080;
    border: 1px solid #3b3b3b;
}

QPushButton {
    background: #3a3a3a;
    color: #ffffff;
    border: 1px solid #555555;
    padding: 7px 11px;
    font-weight: 700;
}

QPushButton:hover {
    background: #494949;
    border: 1px solid #777777;
}

QPushButton:pressed {
    background: #242424;
}

QPushButton:disabled {
    background: #2a2a2a;
    color: #777777;
    border: 1px solid #3a3a3a;
}

QPushButton#yellowButton {
    background: #ffd400;
    color: #111111;
    border: 1px solid #ffd400;
    font-weight: 900;
}

QPushButton#yellowButton:hover {
    background: #ffe45c;
}

QPushButton#dangerButton {
    background: #3a2222;
    color: #ffd0d0;
    border: 1px solid #7a3a3a;
}

QPushButton#toolButton {
    background: transparent;
    border: none;
    padding: 7px 10px;
    color: #eeeeee;
}

QPushButton#toolButton:hover {
    background: #444444;
}

QPushButton#activeToolButton {
    background: transparent;
    border: none;
    border-bottom: 3px solid #ffd400;
    padding: 7px 10px;
    color: #ffd400;
}

QPushButton#playButton {
    background: transparent;
    border: none;
    font-size: 25px;
    color: #ffffff;
}

QPushButton#playButton:hover {
    color: #ffd400;
}

QProgressBar {
    background: #111111;
    border: 1px solid #555555;
    height: 12px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: #ffd400;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #c8c8c8;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #ffffff;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #333333;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #777777;
    min-height: 30px;
}

QScrollBar:horizontal {
    background: #333333;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background: #777777;
    min-width: 30px;
}

QTextEdit {
    background: #111111;
    color: #cfcfcf;
    border: 1px solid #444444;
    font-family: Consolas;
    font-size: 12px;
}
QComboBox {
    background: #191919;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 2px;
    padding: 5px 28px 5px 7px;
    min-height: 22px;
}

QComboBox:hover {
    border: 1px solid #777777;
}

QComboBox:focus {
    border: 1px solid #ffd400;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #444444;
    background: #151515;
}

QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #ffffff;
    margin-right: 7px;
}

QComboBox QAbstractItemView {
    background: #191919;
    color: #ffffff;
    border: 1px solid #555555;
    selection-background-color: #ffd400;
    selection-color: #111111;
    outline: 0px;
    padding: 2px;
}

QComboBox QAbstractItemView::item {
    background: #191919;
    color: #ffffff;
    min-height: 26px;
    padding: 5px 8px;
}

QComboBox QAbstractItemView::item:hover {
    background: #333333;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:selected {
    background: #ffd400;
    color: #111111;
}
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
            self.runner.run(
                self.job,
                on_progress=self.progress.emit,
                on_log=self.log.emit,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        self.runner.cancel()


class PreviewWorker(QObject):
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, job: VideoJob, preview_path: Path, preview_time: str | None) -> None:
        super().__init__()
        self.job = job
        self.preview_path = preview_path
        self.preview_time = preview_time

    def run(self) -> None:
        try:
            render_preview_frame(self.job, self.preview_path, self.preview_time)
            self.ready.emit(str(self.preview_path))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class MediaCard(QFrame):
    clicked = pyqtSignal(Path)

    def __init__(self, path: Path, duration_text: str) -> None:
        super().__init__()

        self.path = path
        self.setObjectName("mediaCard")
        self.setProperty("selected", False)
        self.setMinimumSize(120, 120)
        self.setMaximumWidth(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.thumb_frame = QFrame()
        self.thumb_frame.setObjectName("mediaThumb")
        self.thumb_frame.setMinimumSize(110, 76)

        thumb_layout = QVBoxLayout(self.thumb_frame)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        self.thumb_label = QLabel("VIDEO")
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setObjectName("muted")
        thumb_layout.addWidget(self.thumb_label)

        title = QLabel(path.stem[:18])
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

        scaled = pixmap.scaled(
            self.thumb_frame.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.thumb_label.setPixmap(scaled)
        self.thumb_label.setText("")


class VideoToolWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.media_paths: list[Path] = []
        self.media_cards: dict[Path, MediaCard] = {}
        self.current_input_path: Path | None = None

        self.render_thread: QThread | None = None
        self.render_worker: RenderWorker | None = None

        self.preview_thread: QThread | None = None
        self.preview_worker: PreviewWorker | None = None

        self.temp_dir = tempfile.TemporaryDirectory()
        self.preview_pixmap_original: QPixmap | None = None

        self.setWindowTitle("PyQt Video Tool")
        self.resize(1600, 920)
        self.setMinimumSize(1180, 720)

        self.add_files_btn = QPushButton("+ Add files")
        self.add_files_btn.setObjectName("yellowButton")

        self.add_color_btn = QPushButton("◉ Add color")
        self.add_color_btn.setObjectName("toolButton")

        self.audio_btn = QPushButton("Audio")
        self.audio_btn.setObjectName("toolButton")

        self.trim_btn = QPushButton("✂ Trim")
        self.trim_btn.setObjectName("activeToolButton")

        self.offset_btn = QPushButton("Offset")
        self.offset_btn.setObjectName("toolButton")

        self.split_btn = QPushButton("Split")
        self.split_btn.setObjectName("toolButton")

        self.voiceover_btn = QPushButton("🎙 Voiceover")
        self.voiceover_btn.setObjectName("toolButton")

        self.subtitles_btn = QPushButton("CC Subtitles")
        self.subtitles_btn.setObjectName("toolButton")

        self.export_btn = QPushButton("Export video")
        self.export_btn.setObjectName("yellowButton")

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setEnabled(False)

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

        self.start_edit = QLineEdit("0")
        self.end_edit = QLineEdit()
        self.end_edit.setPlaceholderText("End")

        self.duration_edit = QLineEdit()
        self.duration_edit.setPlaceholderText("Duration")

        self.preview_time_edit = QLineEdit("0")
        self.preview_time_edit.setMaximumWidth(100)

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

        self.audio_bitrate_edit = QLineEdit("128k")

        self.no_audio_check = QCheckBox("No audio")
        self.copy_mode_check = QCheckBox("Copy mode")
        self.overwrite_check = QCheckBox("Overwrite")
        self.overwrite_check.setChecked(True)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output path")
        self.output_btn = QPushButton("Browse")

        self.preview_label = QLabel("")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("playButton")

        self.preview_slider = QSlider(Qt.Orientation.Horizontal)
        self.preview_slider.setRange(0, 1000)
        self.preview_slider.setValue(0)

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

        self.timeline_clip_label = QLabel("Drop video here")
        self.timeline_clip_label.setObjectName("muted")
        self.timeline_clip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.timeline_duration_label = QLabel("")
        self.timeline_duration_label.setObjectName("timelineTime")

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(90)
        self.log_edit.setPlaceholderText("FFmpeg log...")

        self._build_layout()
        self._connect()
        self._refresh_operation_state()

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

        title = QLabel("PyQt Video Tool")
        title.setObjectName("title")

        project = QLabel("- My project 1")
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

        settings = self._build_export_settings_strip()
        layout.addWidget(settings)

        return panel

    def _build_export_settings_strip(self) -> QWidget:
        box = QFrame()
        box.setObjectName("settingsPopup")

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

        layout.addWidget(self.no_audio_check, 3, 0, 1, 2)
        layout.addWidget(self.copy_mode_check, 3, 2, 1, 2)
        layout.addWidget(self.overwrite_check, 3, 4, 1, 2)

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
        monitor_layout.addWidget(self.preview_label)

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

        update_preview_btn = QPushButton("Update preview")
        update_preview_btn.clicked.connect(self.start_preview)
        preview_row.addWidget(update_preview_btn)

        layout.addLayout(preview_row)

        return panel

    def _build_timeline_tools(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("timelineTools")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)

        layout.addWidget(self.audio_btn)
        layout.addWidget(self.trim_btn)
        layout.addWidget(self.offset_btn)
        layout.addWidget(self.split_btn)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addSpacing(16)
        layout.addWidget(self.percent_label)

        self.progress.setMaximumWidth(260)
        layout.addWidget(self.progress)

        return bar

    def _build_timeline_area(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("timelinePanel")
        panel.setMinimumHeight(250)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        ruler = QFrame()
        ruler.setFixedHeight(22)
        ruler_layout = QHBoxLayout(ruler)
        ruler_layout.setContentsMargins(0, 0, 0, 0)

        ruler_layout.addWidget(QLabel("0"))
        ruler_layout.addStretch()
        ruler_layout.addWidget(self.timeline_duration_label)

        layout.addWidget(ruler)

        video_track = QFrame()
        video_track.setObjectName("timelineClip")
        video_track.setMinimumHeight(120)

        video_layout = QHBoxLayout(video_track)
        video_layout.setContentsMargins(8, 8, 8, 8)

        track_name = QLabel("Video")
        track_name.setObjectName("trackName")
        track_name.setFixedWidth(70)

        video_layout.addWidget(track_name)
        video_layout.addWidget(self.timeline_clip_label, stretch=1)

        audio_track = QFrame()
        audio_track.setObjectName("audioClip")
        audio_track.setFixedHeight(36)

        audio_layout = QHBoxLayout(audio_track)
        audio_layout.setContentsMargins(8, 4, 8, 4)

        audio_name = QLabel("Audio")
        audio_name.setObjectName("trackName")
        audio_name.setFixedWidth(70)

        audio_label = QLabel("audio track")
        audio_label.setObjectName("muted")

        audio_layout.addWidget(audio_name)
        audio_layout.addWidget(audio_label)

        layout.addWidget(video_track)
        layout.addWidget(audio_track)

        log_row = QHBoxLayout()
        log_row.addWidget(self.log_edit)
        layout.addLayout(log_row)

        return panel

    def _connect(self) -> None:
        self.add_files_btn.clicked.connect(self.add_files)
        self.export_btn.clicked.connect(self.start_render)
        self.cancel_btn.clicked.connect(self.cancel_render)
        self.output_btn.clicked.connect(self.choose_output_file)

        self.operation_combo.currentIndexChanged.connect(self._refresh_operation_state)
        self.operation_combo.currentIndexChanged.connect(self.refresh_output_suggestion)

    def add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add video files",
            "",
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v);;All files (*.*)",
        )

        if not paths:
            return

        for raw in paths:
            path = Path(raw)

            if path not in self.media_paths:
                self.media_paths.append(path)

        self.rebuild_media_grid()

        if self.current_input_path is None and self.media_paths:
            self.select_media(self.media_paths[0])

    def rebuild_media_grid(self) -> None:
        while self.media_grid.count():
            item = self.media_grid.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

        self.media_cards.clear()

        columns = 5

        for index, path in enumerate(self.media_paths):
            duration_text = self.duration_text(path)

            card = MediaCard(path, duration_text)
            card.clicked.connect(self.select_media)

            self.media_cards[path] = card

            row = index // columns
            col = index % columns

            self.media_grid.addWidget(card, row, col)

        self.update_selected_cards()

    def select_media(self, path: Path) -> None:
        self.current_input_path = path
        self.update_selected_cards()

        if not self.output_edit.text().strip():
            self.output_edit.setText(str(self.suggest_output_path(path)))

        self.timeline_clip_label.setText(path.name)
        self.timeline_duration_label.setText(self.duration_text(path))
        self.time_right_label.setText(self.duration_text(path))

        self.start_preview()

    def update_selected_cards(self) -> None:
        for path, card in self.media_cards.items():
            card.set_selected(path == self.current_input_path)

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

        self.no_audio_check.setEnabled(is_compress)
        self.copy_mode_check.setEnabled(is_copy_supported)

        if not is_copy_supported:
            self.copy_mode_check.setChecked(False)

    def choose_output_file(self) -> None:
        operation = self.current_operation()

        if operation == "extract_audio":
            file_filter = "Audio files (*.mp3 *.m4a *.aac *.wav);;All files (*.*)"
        elif operation == "thumbnail":
            file_filter = "Image files (*.jpg *.jpeg *.png *.webp);;All files (*.*)"
        else:
            file_filter = "Video files (*.mp4 *.mkv *.mov *.avi *.webm);;All files (*.*)"

        path, _ = QFileDialog.getSaveFileName(self, "Export video", "", file_filter)

        if path:
            self.output_edit.setText(path)

    def suggest_output_path(self, input_path: Path) -> Path:
        operation = self.current_operation()
        suffix = input_path.suffix or ".mp4"

        if operation == "extract_audio":
            suffix = ".mp3"
        elif operation == "thumbnail":
            suffix = ".jpg"

        return input_path.with_name(f"{input_path.stem}_{operation}{suffix}")

    def refresh_output_suggestion(self) -> None:
        if self.current_input_path is None:
            return

        output_text = self.output_edit.text().strip()

        if not output_text:
            self.output_edit.setText(str(self.suggest_output_path(self.current_input_path)))
            return

        output_path = Path(output_text)

        if any(tag in output_path.stem for tag in OPERATION_LABELS):
            self.output_edit.setText(str(self.suggest_output_path(self.current_input_path)))

    def optional_int(self, spin: QSpinBox) -> int | None:
        value = spin.value()
        return None if value <= 0 else value

    def build_job(self, *, allow_missing_output: bool = False) -> VideoJob:
        if self.current_input_path is None:
            raise VideoError("Спочатку додай і вибери відео в Media Library")

        output_text = self.output_edit.text().strip()

        if not output_text and not allow_missing_output:
            raise VideoError("Вибери шлях експорту")

        if not output_text:
            output_text = str(self.suggest_output_path(self.current_input_path))

        return VideoJob(
            operation=self.current_operation(),
            input_path=self.current_input_path,
            output_path=Path(output_text),
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
        if self.preview_thread is not None:
            return

        try:
            job = self.build_job(allow_missing_output=True)
        except VideoError as exc:
            self.set_preview_text(str(exc))
            return

        preview_path = Path(self.temp_dir.name) / "preview.jpg"
        preview_time = self.preview_time_edit.text().strip() or job.start or "0"

        self.set_preview_text("Rendering preview...")

        self.preview_thread = QThread()
        self.preview_worker = PreviewWorker(job, preview_path, preview_time)
        self.preview_worker.moveToThread(self.preview_thread)

        self.preview_thread.started.connect(self.preview_worker.run)
        self.preview_worker.ready.connect(self.show_preview_image)
        self.preview_worker.failed.connect(self.preview_failed)
        self.preview_worker.finished.connect(self.preview_finished)
        self.preview_worker.finished.connect(self.preview_thread.quit)
        self.preview_worker.finished.connect(self.preview_worker.deleteLater)
        self.preview_thread.finished.connect(self.preview_thread.deleteLater)

        self.preview_thread.start()

    def show_preview_image(self, path: str) -> None:
        pixmap = QPixmap(path)

        if pixmap.isNull():
            self.set_preview_text("Preview failed")
            return

        self.preview_pixmap_original = pixmap
        self.update_preview_pixmap()

        if self.current_input_path and self.current_input_path in self.media_cards:
            self.media_cards[self.current_input_path].set_thumbnail(pixmap)

    def update_preview_pixmap(self) -> None:
        if self.preview_pixmap_original is None or self.preview_pixmap_original.isNull():
            return

        scaled = self.preview_pixmap_original.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.preview_label.setPixmap(scaled)

    def set_preview_text(self, text: str) -> None:
        self.preview_pixmap_original = None
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(text)

    def preview_failed(self, message: str) -> None:
        self.set_preview_text(f"Preview error:\n{message}")

    def preview_finished(self) -> None:
        self.preview_worker = None
        self.preview_thread = None

    def start_render(self) -> None:
        try:
            job = self.build_job()
        except VideoError as exc:
            QMessageBox.warning(self, "Export error", str(exc))
            return

        self.log_edit.clear()
        self.progress.setValue(0)
        self.percent_label.setText("0%")
        self.status_label.setText("Starting export...")

        self.render_thread = QThread()
        self.render_worker = RenderWorker(job)
        self.render_worker.moveToThread(self.render_thread)

        self.render_thread.started.connect(self.render_worker.run)
        self.render_worker.progress.connect(self.on_progress)
        self.render_worker.log.connect(self.append_log)
        self.render_worker.failed.connect(self.render_failed)
        self.render_worker.finished.connect(self.render_finished)
        self.render_worker.finished.connect(self.render_thread.quit)
        self.render_worker.finished.connect(self.render_worker.deleteLater)
        self.render_thread.finished.connect(self.render_thread.deleteLater)

        self.set_running_state(True)
        self.render_thread.start()

    def cancel_render(self) -> None:
        if self.render_worker:
            self.render_worker.cancel()

        self.status_label.setText("Cancelling...")
        self.append_log("Cancelling...")

    def on_progress(self, value: int) -> None:
        self.progress.setValue(value)
        self.percent_label.setText(f"{value}%")

        if value >= 100:
            self.status_label.setText("Export complete")
        else:
            self.status_label.setText("Exporting...")

    def render_failed(self, message: str) -> None:
        self.status_label.setText("Export failed")
        self.append_log("")
        self.append_log(f"ERROR: {message}")

        if "скасовано" not in message.lower() and "cancelled" not in message.lower():
            QMessageBox.critical(self, "Export error", message)

    def render_finished(self) -> None:
        self.set_running_state(False)
        self.render_worker = None
        self.render_thread = None

    def set_running_state(self, running: bool) -> None:
        self.export_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        self.add_files_btn.setEnabled(not running)
        self.output_btn.setEnabled(not running)
        self.operation_combo.setEnabled(not running)

    def append_log(self, text: str) -> None:
        self.log_edit.append(text)

    def duration_text(self, path: Path) -> str:
        try:
            seconds = int(probe_duration(path))
        except Exception:
            return "00:00"

        if seconds <= 0:
            return "00:00"

        minutes = seconds // 60
        sec = seconds % 60

        if minutes >= 60:
            hours = minutes // 60
            minutes %= 60
            return f"{hours:02d}:{minutes:02d}:{sec:02d}"

        return f"{minutes:02d}:{sec:02d}"

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_preview_pixmap()

    def closeEvent(self, event) -> None:
        if self.render_worker:
            reply = QMessageBox.question(
                self,
                "Close?",
                "Export is still running. Cancel and close?",
            )

            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            self.render_worker.cancel()

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