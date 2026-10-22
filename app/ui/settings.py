"""Settings panel widget and plumbing (sliders, toggles).

Exposed as a reusable frame so it can be embedded in the main window.
"""
from __future__ import annotations

import customtkinter as ctk

from app.config import SettingsData


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, settings: SettingsData, on_change=None):
        super().__init__(master)
        self.settings = settings
        self.on_change = on_change

        self.grid_columnconfigure(1, weight=1)

        # Sensitivity.
        ctk.CTkLabel(self, text="Sensitivity").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        self.sens = ctk.CTkSlider(self, from_=0.2, to=2.5,
                                  number_of_steps=46,
                                  command=self._on_sens)
        self.sens.set(settings.sensitivity)
        self.sens.grid(row=0, column=1, sticky="ew", padx=12, pady=(12, 2))

        # Smoothing.
        ctk.CTkLabel(self, text="Smoothing").grid(
            row=1, column=0, sticky="w", padx=12, pady=2)
        self.smooth = ctk.CTkSlider(self, from_=0.0, to=1.0,
                                    number_of_steps=20,
                                    command=self._on_smooth)
        self.smooth.set(settings.smoothing)
        self.smooth.grid(row=1, column=1, sticky="ew", padx=12, pady=2)

        # Pinch threshold.
        ctk.CTkLabel(self, text="Click sensitivity").grid(
            row=2, column=0, sticky="w", padx=12, pady=2)
        self.pinch = ctk.CTkSlider(self, from_=0.02, to=0.12,
                                   number_of_steps=20,
                                   command=self._on_pinch)
        self.pinch.set(settings.pinch_threshold)
        self.pinch.grid(row=2, column=1, sticky="ew", padx=12, pady=2)

        # Scroll sensitivity.
        ctk.CTkLabel(self, text="Scroll speed").grid(
            row=3, column=0, sticky="w", padx=12, pady=2)
        self.scroll = ctk.CTkSlider(self, from_=0.5, to=3.0,
                                    number_of_steps=25,
                                    command=self._on_scroll)
        self.scroll.set(settings.scroll_sensitivity)
        self.scroll.grid(row=3, column=1, sticky="ew", padx=12, pady=2)

        # Edge ease (corner reach).
        ctk.CTkLabel(self, text="Corner reach").grid(
            row=4, column=0, sticky="w", padx=12, pady=2)
        self.edge_ease = ctk.CTkSlider(self, from_=0.0, to=1.0,
                                       number_of_steps=20,
                                       command=self._on_edge_ease)
        self.edge_ease.set(settings.edge_ease)
        self.edge_ease.grid(row=4, column=1, sticky="ew", padx=12, pady=2)

        # Two-hand toggle.
        self.two_hand = ctk.CTkSwitch(
            self, text="Enable two-hand zoom",
            command=self._on_two_hand)
        self.two_hand.grid(row=5, column=0, columnspan=2, sticky="w",
                           padx=12, pady=(10, 12))
        if settings.enable_two_hand:
            self.two_hand.select()
        else:
            self.two_hand.deselect()

    # ------------------------------------------------------------------
    def _on_sens(self, v):
        self.settings.sensitivity = float(v)
        self._emit()

    def _on_smooth(self, v):
        self.settings.smoothing = float(v)
        self._emit()

    def _on_pinch(self, v):
        self.settings.pinch_threshold = float(v)
        self._emit()

    def _on_scroll(self, v):
        self.settings.scroll_sensitivity = float(v)
        self._emit()

    def _on_edge_ease(self, v):
        self.settings.edge_ease = float(v)
        self._emit()

    def _on_two_hand(self):
        self.settings.enable_two_hand = bool(self.two_hand.get())
        self._emit()

    def _emit(self):
        if self.on_change is not None:
            self.on_change()