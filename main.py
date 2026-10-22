"""AIRstylus — Air Mouse application entry point.

Turns your webcam into an air mouse. Control the cursor with your hands,
pinch to click, and use two hands to zoom.
"""
from __future__ import annotations

import sys

import customtkinter as ctk

from app.config import load_config
from app.ui.main_window import MainWindow


def main() -> int:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    config = load_config()
    app = MainWindow(config)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())