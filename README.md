# AIRstylus — Air Mouse for Windows

Turn your webcam into an air mouse. Move the Windows cursor with your hand,
pinch to click, and use both hands to zoom — no hardware required.

## Features

- **Air mouse** — open-palm hand tracking moves the real cursor smoothly.
- **Gestures**
  - Move: open palm
  - Left click: pinch thumb + index
  - Right click: pinch thumb + middle
  - Drag: hold a pinch
  - Scroll: two fingers up / down
  - Zoom: both hands apart / together (Ctrl-style wheel zoom)
- **Calibration wizard** — maps your hand's motion range to the screen.
- **Smoothing** — One-Euro filter removes jitter while staying responsive.
- **Production ready** — ships as a single Windows `.exe`.

## Requirements

- Windows 10/11
- A webcam
- Python 3.12 (for development only — the exe is self-contained)

## Quick start (development)

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Build the exe

```powershell
.\build.bat
```

Or manually:

```powershell
python -m PyInstaller --clean --noconfirm build.spec
```

The output is `dist\AIRstylus.exe`.

## Usage

1. Launch the app and click **Start Tracking**.
2. Click **Calibrate** and wave your hand across the full area you want to
   use as a mouse surface (reach all four corners), then **Save and Apply**.
3. Move your hand to control the cursor; pinch to click.

Settings (sensitivity, smoothing, pinch threshold, two-hand) are persisted to
`config.json` next to the app.

## Project layout

```
AIRstylus/
├── main.py                 # entry point
├── build.spec              # PyInstaller config
├── build.bat               # one-click build
├── app/
│   ├── config.py           # load/save config.json
│   ├── core/
│   │   ├── camera.py       # threaded webcam capture
│   │   ├── tracking.py     # MediaPipe Hands landmarks
│   │   ├── gestures.py     # gesture classification
│   │   ├── smoothing.py    # One-Euro / EMA / hysteresis filters
│   │   ├── mapper.py       # hand -> screen coordinate mapping
│   │   ├── mouse.py        # Win32 SendInput (ctypes)
│   │   └── engine.py       # pipeline orchestration
│   └── ui/
│       ├── main_window.py  # control panel + live preview
│       ├── settings.py     # sliders / toggles
│       ├── preview.py      # camera preview widget
│       └── calibration.py  # calibration wizard
```

## How it works

- **MediaPipe Hands** extracts 21 landmarks per hand (up to two).
- **Gesture engine** classifies pinches, drags, scroll, and two-hand zoom,
  using hysteresis to avoid click stutter.
- **One-Euro filter** smooths cursor position adaptively.
- **Mapper** translates the calibrated camera-space region to absolute screen
  coordinates.
- **SendInput** (raw Win32 via ctypes) injects mouse events with minimal
  latency, working across all apps including PowerPoint slideshows.