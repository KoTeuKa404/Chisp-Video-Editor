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
        QSlider::sub-page:vertical { background:#ffd400; border-radius:2px; }
        QSlider::add-page:vertical { background:#777777; border-radius:2px; }
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
    source = source.replace(
        'self.volume_icon = StaticIcon("volume")',
        'self.volume_icon = VolumeButton(self.audio_output)',
    )
    source = source.replace(
        'self.trim_volume_icon = StaticIcon("volume")',
        'self.trim_volume_icon = VolumeButton(self.audio_output)',
    )

    source = source.replace(
        '        painter.setPen(QPen(QColor("#ffd400"), 2))\n'
        '        painter.drawLine(px, y - 15, px, y + 15)',
        '        if self.drag_target not in {"start", "end"} and abs(px - sx) > 14 and abs(px - ex) > 14:\n'
        '            painter.setPen(QPen(QColor("#ffd400"), 2))\n'
        '            painter.drawLine(px, y - 15, px, y + 15)',
    )

    source = source.replace(
        '        if abs(x - sx) <= 18:\n'
        '            self.drag_target = "start"\n'
        '            self.position = self.start_value\n'
        '            self.seekRequested.emit(self.position)\n'
        '        elif abs(x - ex) <= 18:',
        '        start_hit = abs(x - sx) <= 34 or (sx <= x <= sx + 54) or (x < sx and sx - x <= 34)\n'
        '        end_hit = abs(x - ex) <= 34\n'
        '        if start_hit:\n'
        '            self.drag_target = "start"\n'
        '            self.position = self.start_value\n'
        '            self.seekRequested.emit(self.position)\n'
        '        elif end_hit:',
    )

    return source


if __name__ == "__main__":
    namespace = {
        "__name__": "__main__",
        "__file__": __file__,
        "__package__": None,
    }
    exec(compile(load_editor_source(), __file__, "exec"), namespace)
