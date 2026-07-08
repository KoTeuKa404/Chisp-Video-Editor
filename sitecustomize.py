"""Runtime Qt compatibility helpers for the editor.

Python automatically imports this module on startup when it is present
in the project directory. It keeps video_gui.py compatible even if a Qt
symbol was missed in the local imports.
"""

from __future__ import annotations

import builtins

from PyQt6.QtCore import QPointF

builtins.QPointF = QPointF
