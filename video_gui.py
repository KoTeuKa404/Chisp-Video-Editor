from __future__ import annotations

"""Launcher for the current video editor UI.

This keeps the existing large UI implementation from the previous blob, but patches
PyQt compatibility issues and small UI behavior fixes before executing it.
"""

import subprocess
from pathlib import Path

ORIGINAL_VIDEO_GUI_BLOB = "283835ae4bfd8557296e2362499d94ab0d457bb2"
MISSING_IMPORT = "from PyQt6.QtCore import QObject, QRect, QRectF, QThread, Qt, QUrl, pyqtSignal"
FIXED_IMPORT = "from PyQt6.QtCore import QObject, QPointF, QRect, QRectF, QThread, Qt, QUrl, pyqtSignal"

VOLUME_BUTTON_CODE = r'''
class VolumePopup(QWidget):
    def __init__(self, audio_output: QAudioOutput, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.audio_output = audio_output
        self.setObjectName("volumePopup")
        self.setFixedSize(54, 178)
        self.setStyleSheet("""
        QWidget#volumePopup { background:#2b2b2b; border:1px solid #ffd400; border-radius:4px; }
        QLabel#volumeText { color:#ffd400; font-weight:800; }
        QSlider::groove:vertical { width:5px; background:#777777; border-radius:2px; }
        QSlider::sub-page:vertical { background:#777777; border-radius:2px; }
        QSlider::add-page:vertical { background:#ffd400; border-radius:2px; }
        QSlider::handle:vertical { width:18px; height:18px; margin:0 -7px; border-radius:9px; background:#ffd400; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(7)
        self.value_label = QLabel("85%")
        self.value_label.setObjectName("volumeText")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setInvertedAppearance(False)
        self.slider.setInvertedControls(False)
        self.slider.setValue(int(round(self.audio_output.volume() * 100)))
        self.slider.valueChanged.connect(self.set_volume)
        layout.addWidget(self.value_label)
        layout.addWidget(self.slider, stretch=1)
        self.set_volume(self.slider.value())

    def set_volume(self, value: int) -> None:
        value = max(0, min(100, value))
        self.audio_output.setVolume(value / 100)
        self.value_label.setText(f"{value}%")


class VolumeButton(IconButton):
    def __init__(self, audio_output: QAudioOutput, parent: QWidget | None = None) -> None:
        super().__init__("volume", size=34, parent=parent)
        self.audio_output = audio_output
        self.popup = VolumePopup(audio_output, self)
        self.clicked.connect(self.toggle_popup)

    def toggle_popup(self) -> None:
        if self.popup.isVisible():
            self.popup.hide()
            return
        self.popup.slider.setValue(int(round(self.audio_output.volume() * 100)))
        point = self.mapToGlobal(self.rect().topLeft())
        x = point.x() + self.width() // 2 - self.popup.width() // 2
        y = point.y() - self.popup.height() - 8
        if y < 0:
            y = point.y() + self.height() + 8
        self.popup.move(x, y)
        self.popup.show()
        self.popup.raise_()
        self.popup.slider.setFocus()
'''

TRIM_RANGE_BAR_CODE = r'''
class TrimRangeBar(QWidget):
    startChanged = pyqtSignal(int)
    endChanged = pyqtSignal(int)
    seekRequested = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.duration = 0
        self.start_value = 0
        self.end_value = 0
        self.position = 0
        self.drag_target: str | None = None
        self.setMinimumHeight(54)
        self.setMouseTracking(True)

    def set_duration(self, duration: int) -> None:
        self.duration = max(0, duration)
        self.start_value = max(0, min(self.start_value, self.duration))
        self.end_value = self.duration if self.end_value <= 0 else max(self.start_value, min(self.end_value, self.duration))
        self.position = max(self.start_value, min(self.position, self.end_value if self.end_value > self.start_value else self.duration))
        self.update()

    def set_position(self, position: int) -> None:
        self.position = max(0, min(position, self.duration))
        self.update()

    def set_range_values(self, start: int, end: int) -> None:
        start = max(0, min(start, self.duration))
        end = max(start, min(end, self.duration))
        self.start_value = start
        self.end_value = end
        self.position = start
        self.update()

    def bar_rect(self) -> QRect:
        return QRect(12, 24, max(1, self.width() - 24), 16)

    def value_to_x(self, value: int) -> int:
        rect = self.bar_rect()
        if self.duration <= 0:
            return rect.left()
        return rect.left() + int(rect.width() * value / self.duration)

    def x_to_value(self, x: int) -> int:
        rect = self.bar_rect()
        x = max(rect.left(), min(x, rect.right()))
        if rect.width() <= 0 or self.duration <= 0:
            return 0
        return int((x - rect.left()) / rect.width() * self.duration)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.bar_rect()
        y = rect.center().y()
        sx = self.value_to_x(self.start_value)
        ex = self.value_to_x(self.end_value)
        px = self.value_to_x(self.position)

        painter.setPen(QPen(QColor("#bdbdbd"), 3))
        painter.drawLine(rect.left(), y, rect.right(), y)

        painter.setPen(QPen(QColor("#ffd400"), 4))
        painter.drawLine(sx, y, ex, y)

        if abs(px - sx) > 13:
            painter.setPen(QPen(QColor("#ffd400"), 2))
            painter.drawLine(sx, y - 8, sx, y + 8)

        painter.setPen(QPen(QColor("#ffd400"), 3))
        painter.setBrush(QColor("#5a5a5a"))
        painter.drawEllipse(px - 9, y - 9, 18, 18)

        painter.setPen(QPen(QColor("#ffd400"), 3))
        painter.drawLine(ex, y - 16, ex, y + 16)
        painter.drawLine(ex - 3, y - 16, ex + 3, y - 16)
        painter.drawLine(ex - 3, y + 16, ex + 3, y + 16)

        self.draw_tag(painter, px, 0, self.format_msec(self.position))
        self.draw_tag(painter, ex, 0, self.format_msec(self.end_value))

    def draw_tag(self, painter: QPainter, x: int, y: int, text: str) -> None:
        width = 66
        left = max(0, min(x - width // 2, self.width() - width))
        rect = QRect(left, y, width, 22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffd400"))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor("#111111"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.duration <= 0:
            return
        x = int(event.position().x())
        sx = self.value_to_x(self.start_value)
        ex = self.value_to_x(self.end_value)
        px = self.value_to_x(self.position)
        start_hit = abs(x - sx) <= 34 or abs(x - px) <= 24 or (sx <= x <= sx + 54)
        end_hit = abs(x - ex) <= 34
        if start_hit and not end_hit:
            self.drag_target = "start"
            value = min(self.x_to_value(x), self.end_value)
            self.start_value = value
            self.position = value
            self.startChanged.emit(value)
            self.seekRequested.emit(value)
        elif end_hit:
            self.drag_target = "end"
        else:
            self.drag_target = "position"
            value = self.x_to_value(x)
            self.position = value
            self.seekRequested.emit(value)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.drag_target or self.duration <= 0:
            return
        value = self.x_to_value(int(event.position().x()))
        if self.drag_target == "start":
            value = min(value, self.end_value)
            self.start_value = value
            self.position = value
            self.startChanged.emit(value)
            self.seekRequested.emit(value)
        elif self.drag_target == "end":
            value = max(value, self.start_value)
            self.end_value = value
            self.endChanged.emit(value)
        else:
            self.position = value
            self.seekRequested.emit(value)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.drag_target = None

    def format_msec(self, msec: int) -> str:
        total = max(0, msec) / 1000
        minutes = int(total // 60)
        seconds = total % 60
        return f"{minutes:02d}:{seconds:04.1f}"
'''

APPLY_TRIM_METHOD_CODE = r'''
    def apply_trim_and_exit(self) -> None:
        duration = max(0, self.player.duration())
        start = self.safe_seconds_to_msec(self.start_edit.text())
        end = self.safe_seconds_to_msec(self.end_edit.text()) if self.end_edit.text().strip() else duration
        if duration > 0:
            start = max(0, min(start, duration))
            end = max(0, min(end, duration))
        if end <= start:
            QMessageBox.warning(self, "Trim", "End має бути більший за Start.")
            return
        self.set_operation("trim")
        self.start_edit.setText(f"{start / 1000:.3f}")
        self.end_edit.setText(f"{end / 1000:.3f}")
        if hasattr(self, "trim_range_bar"):
            self.trim_range_bar.set_range_values(start, end)
        self.player.pause()
        self.exit_mode()
        self.player.setPosition(start)
        trim_seconds = max(1, int(round((end - start) / 1000)))
        self.time_left_label.setText(self.format_msec(start, with_tenths=True))
        self.time_right_label.setText(self.format_seconds(trim_seconds))
        self.trim_time_right_label.setText(self.format_seconds(trim_seconds))
        self.rebuild_timeline()
        self.update_timeline_selection()
        self.set_status(f"Trim applied: {self.format_seconds(trim_seconds)}")
'''

CLIP_DURATION_HELPER_CODE = r'''
    def clip_duration_seconds(self, path: Path) -> int:
        if path == self.current_input_path and self.current_operation() == "trim":
            start = self.safe_seconds_to_msec(self.start_edit.text())
            end = self.safe_seconds_to_msec(self.end_edit.text()) if self.end_edit.text().strip() else self.player.duration()
            if end > start:
                return max(1, int(round((end - start) / 1000)))
        return self.duration_seconds(path)
'''


def replace_between(source: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = source.find(start_marker)
    end = source.find(end_marker, start)
    if start == -1 or end == -1:
        return source
    return source[:start] + replacement + "\n\n" + source[end:]


def load_editor_source() -> str:
    repo_dir = Path(__file__).resolve().parent
    result = subprocess.run(
        ["git", "cat-file", "-p", ORIGINAL_VIDEO_GUI_BLOB],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not load bundled video editor source from git history. "
            f"git stderr: {result.stderr.strip()}"
        )

    source = result.stdout.replace(MISSING_IMPORT, FIXED_IMPORT)

    source = source.replace(
        "r.center() + QPointF(-6, -10),\n"
        "                r.center() + QPointF(-6, 10),\n"
        "                r.center() + QPointF(10, 0),",
        "QPointF(r.center()) + QPointF(-6, -10),\n"
        "                QPointF(r.center()) + QPointF(-6, 10),\n"
        "                QPointF(r.center()) + QPointF(10, 0),",
    )

    source = source.replace(
        "class TimelineCanvas(QFrame):",
        VOLUME_BUTTON_CODE + "\n\nclass TimelineCanvas(QFrame):",
    )
    source = replace_between(source, "class TrimRangeBar(QWidget):", "class MediaCard(QFrame):", TRIM_RANGE_BAR_CODE)
    source = source.replace('self.volume_icon = StaticIcon("volume")', 'self.volume_icon = VolumeButton(self.audio_output)')
    source = source.replace('self.trim_volume_icon = StaticIcon("volume")', 'self.trim_volume_icon = VolumeButton(self.audio_output)')

    source = source.replace(
        "        self.done_trim_btn.clicked.connect(self.exit_mode)",
        "        self.done_trim_btn.clicked.connect(self.apply_trim_and_exit)",
    )
    source = source.replace(
        "    def exit_mode(self) -> None:",
        APPLY_TRIM_METHOD_CODE + "\n    def exit_mode(self) -> None:",
    )
    source = source.replace(
        "            total += self.duration_seconds(path)\n"
        "            clip = TimelineClip(index, path, self.duration_text(path), self.thumb_cache.get(path))",
        "            clip_seconds = self.clip_duration_seconds(path)\n"
        "            total += clip_seconds\n"
        "            clip = TimelineClip(index, path, self.format_seconds(clip_seconds), self.thumb_cache.get(path))",
    )
    source = source.replace(
        "    def duration_seconds(self, path: Path) -> int:",
        CLIP_DURATION_HELPER_CODE + "\n    def duration_seconds(self, path: Path) -> int:",
    )
    source = source.replace(
        '        if self.current_mode == "trim":\n'
        '            start = self.trim_range_bar.start_value\n'
        '            end = self.trim_range_bar.end_value\n'
        '            pos = self.player.position()\n'
        '            if end > start and (pos < start or pos >= end):\n'
        '                self.player.setPosition(start)',
        '        if self.current_operation() == "trim":\n'
        '            start = self.safe_seconds_to_msec(self.start_edit.text())\n'
        '            end = self.safe_seconds_to_msec(self.end_edit.text()) if self.end_edit.text().strip() else self.player.duration()\n'
        '            if self.current_mode == "trim":\n'
        '                start = self.trim_range_bar.start_value\n'
        '                end = self.trim_range_bar.end_value\n'
        '            pos = self.player.position()\n'
        '            if end > start and (pos < start or pos >= end):\n'
        '                self.player.setPosition(start)',
    )
    source = source.replace(
        '        if self.current_mode == "trim" and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:\n'
        '            end = self.trim_range_bar.end_value\n'
        '            start = self.trim_range_bar.start_value\n'
        '            if end > start and position >= end:',
        '        if self.current_operation() == "trim" and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:\n'
        '            start = self.safe_seconds_to_msec(self.start_edit.text())\n'
        '            end = self.safe_seconds_to_msec(self.end_edit.text()) if self.end_edit.text().strip() else self.player.duration()\n'
        '            if self.current_mode == "trim":\n'
        '                start = self.trim_range_bar.start_value\n'
        '                end = self.trim_range_bar.end_value\n'
        '            if end > start and position >= end:',
    )
    return source


if __name__ == "__main__":
    namespace = {
        "__name__": "__main__",
        "__file__": __file__,
        "__package__": None,
    }
    exec(compile(load_editor_source(), __file__, "exec"), namespace)
