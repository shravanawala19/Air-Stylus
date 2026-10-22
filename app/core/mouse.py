"""Low-level Windows mouse control via raw Win32 SendInput (ctypes).

Zero external dependencies. SendInput is the fastest and most reliable way to
inject mouse events on Windows, working across all apps including PowerPoint
slideshows and elevated windows.
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

# Constants.
INPUT_MOUSE = 0

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

WHEEL_DELTA = 120

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT(ctypes.Structure):
    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUTUNION),
    ]


# Make the process DPI-aware so absolute coordinates are consistent on
# high-DPI / multi-monitor setups.
try:
    user32.SetProcessDPIAware()
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def _send_input(flags: int, dx: int = 0, dy: int = 0, mouse_data: int = 0) -> None:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi = MOUSEINPUT(dx, dy, mouse_data, flags, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _normalized_absolute(x: int, y: int) -> tuple[int, int]:
    """Convert screen pixel coords to SendInput absolute (0..65535)."""
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    nx = int((65535 * (x - left)) / max(1, width - 1))
    ny = int((65535 * (y - top)) / max(1, height - 1))
    return nx, ny


def get_screen_size() -> tuple[int, int]:
    return (
        user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
        user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
    )


def get_cursor_pos() -> tuple[int, int]:
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)


def move_absolute(x: int, y: int) -> None:
    nx, ny = _normalized_absolute(x, y)
    _send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, nx, ny)


def move_relative(dx: int, dy: int) -> None:
    _send_input(MOUSEEVENTF_MOVE, int(dx), int(dy))


def button_down(button: str = "left") -> None:
    flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
    _send_input(flag)


def button_up(button: str = "left") -> None:
    flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
    _send_input(flag)


def click(button: str = "left") -> None:
    button_down(button)
    button_up(button)


def scroll(delta: int) -> None:
    """Scroll by wheel notches. Positive delta = scroll up."""
    _send_input(MOUSEEVENTF_WHEEL, 0, 0, int(delta) * WHEEL_DELTA)


def drag(start_x: int, start_y: int, end_x: int, end_y: int,
         steps: int = 12, duration: float = 0.25) -> None:
    """Perform a click-drag from one screen coordinate to another."""
    move_absolute(start_x, start_y)
    time.sleep(0.01)
    button_down("left")
    time.sleep(0.02)

    dx = end_x - start_x
    dy = end_y - start_y
    for i in range(1, steps + 1):
        t = i / steps
        move_absolute(start_x + int(dx * t), start_y + int(dy * t))
        time.sleep(duration / steps)

    time.sleep(0.02)
    button_up("left")