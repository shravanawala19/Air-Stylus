"""Live camera preview using CustomTkinter + PIL.

Receives numpy frames from the engine callback and renders them into a
CTkLabel. Overlays simple tracking markers (hand landmarks, active region).
"""
from __future__ import annotations

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, width: int = 480, height: int = 360):
        super().__init__(master)
        self.width = width
        self.height = height
        self._photo = None

        self.label = ctk.CTkLabel(self, text="Camera preview will appear here",
                                  width=width, height=height)
        self.label.pack(padx=8, pady=8)

    def show_frame(self, frame: np.ndarray, points=None) -> None:
        img = Image.fromarray(frame)
        img.thumbnail((self.width, self.height), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.label.configure(image=self._photo, text="")

    def clear(self) -> None:
        self.label.configure(image=None, text="Camera preview will appear here")