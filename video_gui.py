from __future__ import annotations

"""Launcher for the current video editor UI.

This keeps the existing large UI implementation from the previous blob, but patches
one missed PyQt import before executing it. The previous implementation used
QPointF in custom vector icons without importing it, which caused a NameError in
IconButton.paintEvent.
"""

import subprocess
from pathlib import Path

ORIGINAL_VIDEO_GUI_BLOB = "283835ae4bfd8557296e2362499d94ab0d457bb2"
MISSING_IMPORT = "from PyQt6.QtCore import QObject, QRect, QRectF, QThread, Qt, QUrl, pyqtSignal"
FIXED_IMPORT = "from PyQt6.QtCore import QObject, QPointF, QRect, QRectF, QThread, Qt, QUrl, pyqtSignal"


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
    return result.stdout.replace(MISSING_IMPORT, FIXED_IMPORT)


if __name__ == "__main__":
    namespace = {
        "__name__": "__main__",
        "__file__": __file__,
        "__package__": None,
    }
    exec(compile(load_editor_source(), __file__, "exec"), namespace)
