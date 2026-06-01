# Microscope Capture

Lightweight image and video acquisition application for scientific microscopy using a Sony a6700 (or similar camera) connected through an HDMI UVC capture device on Windows 11.

## Features

- Live preview from a selectable capture device
- Selectable capture resolution (default 1920x1080; also 1280x720 / 640x480 / Auto)
- Digital zoom with drag-to-pan; capture the visible region
- Still image capture to PNG
- Basic uncompressed AVI video recording
- User-editable filenames with optional Auto-fill template
- Metadata JSON sidecar files for each capture
- Desktop shortcut launcher (no command line needed)

## Requirements

- Python 3.10 or newer (3.13 recommended)
- Windows 11 for production use with HDMI capture hardware
- OpenCV-compatible UVC/HDMI capture device

## Installation

### Windows (recommended)

**Install the app in a short local path** such as `C:\MicroscopeCapture`.
Do not install the virtual environment inside a deep Dropbox path. PySide6 creates very long file paths and Windows may fail with `OSError: [Errno 2] No such file or directory` during `pip install`.

Recommended layout:

```text
C:\MicroscopeCapture\          <- app + .venv (local, short path)
C:\Users\...\Dropbox\...\      <- saved Images/Videos/Metadata only (optional)
```

Double-click **`setup.bat`**, or run in **Command Prompt**:

```bat
cd /d C:\MicroscopeCapture
setup.bat
```

Then launch the app with **`run.bat`** or:

```bat
.venv\Scripts\python.exe app.py
```

**Important:** Do not run `activate` with `python.exe`. The activate script is a shell command, not a Python file.

If `python` is not on PATH (common on lab PCs), use your full Python path once for setup:

```bat
cd /d C:\MicroscopeCapture
C:\ProgramData\miniforge3\python.exe -m venv .venv
setup.bat
run.bat
```

Optional manual activation in Command Prompt (not PowerShell):

```bat
.venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py
```

### Desktop shortcut (no command line)

After `setup.bat` succeeds, double-click **`create_shortcut.bat`** once.
It creates a **Microscope Capture** shortcut on your Desktop that launches the app via `run.bat`. From then on, just double-click the Desktop icon.

### macOS (development smoke tests only)

```bash
cd MicroscopeCapture
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Version Control (Git)

The project is managed with Git. Use GitHub (or another host) as the single source of truth for code updates.

### Recommended layout

```text
Mac (development)     -->  git push  -->  GitHub
Windows (microscope)  <--  git pull  <--  GitHub

C:\MicroscopeCapture\     local app + .venv (never commit .venv)
C:\Users\...\MicroscopeData\   captured images/videos (not in git)
```

### First-time publish to GitHub (Mac)

1. Install [GitHub CLI](https://cli.github.com/) if needed.
2. Log in (one-time):

   ```bash
   gh auth login
   ```

3. From the project folder, create a public repo and push:

   ```bash
   cd /path/to/MicroscopeCapture
   gh repo create MicroscopeCapture --public --source=. --remote=origin --push
   ```

   If the name `MicroscopeCapture` is taken, pick another name and use that URL when cloning on Windows.

### Day-to-day workflow (Mac — develop)

```bash
cd /path/to/MicroscopeCapture
git status
git add .
git commit -m "Describe your change"
git push
```

### First-time setup on Windows (microscope PC)

1. Install [Git for Windows](https://git-scm.com/download/win).
2. Clone into a short local path (do **not** clone into Dropbox):

   ```bat
   git clone https://github.com/YOUR_USER/MicroscopeCapture.git C:\MicroscopeCapture
   cd /d C:\MicroscopeCapture
   setup.bat
   create_shortcut.bat
   ```

3. Run the app with `run.bat` or the Desktop shortcut.

### Updating on Windows (after code changes on Mac)

```bat
cd /d C:\MicroscopeCapture
update_from_git.bat
```

Or manually:

```bat
git pull
```

If `requirements.txt` changed, run `setup.bat` again. Your `.venv` and capture data are not overwritten by `git pull`.

### Alternative: Dropbox sync (legacy)

If you still mirror files through Dropbox, use **`update_from_dropbox.bat`** instead of `git pull`. Prefer Git when possible.

Personal paths are **not** stored in the repository. On each PC, configure once:

```bat
copy dropbox_sync.config.bat.example dropbox_sync.config.bat
notepad dropbox_sync.config.bat
```

Edit `SRC` to your Dropbox `MicroscopeCapture` folder, then run `update_from_dropbox.bat`. The file `dropbox_sync.config.bat` is listed in `.gitignore` and is never committed.

## Usage

1. Connect the Sony a6700 (clean HDMI output) to the UVC capture device.
2. Launch the app and click **Refresh** if needed.
3. Select the correct camera from the dropdown.
4. Choose a **Resolution** (Auto uses the camera default; pick 1920 x 1080 for full HD).
5. Enter metadata fields: Sample, ID, Condition, Magnification, Notes.
6. Enter any filename you want, or click **Auto-fill** for:
   `YYYYMMDD_HHMMSS_SAMPLE_ID_CONDITION_MAGNIFICATION`
7. Choose a save directory (default: `~/MicroscopeData`).
8. Click **Capture Image** for a PNG still, or **Start Recording** / **Stop Recording** for AVI.

### Resolution

- The **Resolution** dropdown requests a capture size from the device. It defaults to `1920 x 1080`.
- `Auto (camera default)` keeps whatever the device reports.
- The capture device must support the requested size; if not, the camera falls back to the nearest supported mode, which the status line reports.
- The app requests the **MJPG** stream format so HDMI/UVC dongles can deliver full resolution at 30 FPS (see Troubleshooting).

### Zoom, Pan, and Crop (live)

- Use the **Zoom** slider (or the mouse wheel over the image) to zoom from 1.0x to 8.0x.
- When zoomed in, **drag the image** to pan around; the visible region fills the panel.
- **Reset View** returns to the full frame (1.0x).
- **Save visible region only** (on by default): captured PNGs contain exactly what is shown. Turn it off to always save the full frame regardless of zoom.

## Troubleshooting

### Preview stutters at Full HD

If the live preview is choppy at 1920 x 1080 even though the status shows 30 FPS:

- The app already requests the **MJPG** format, which is required for most USB HDMI capture dongles to run 1080p at 30 FPS. The raw (YUYV) format exceeds USB 2.0 bandwidth at 1080p, so the device silently drops to a few FPS.
- If it is still choppy, the **capture device or its USB connection** is the bottleneck:
  - Plug the dongle directly into a USB 3.0 port (blue), not a hub.
  - Confirm the dongle is rated for 1080p60 / 1080p30 capture.
  - Try 1280 x 720 to verify smoothness; if 720p is smooth but 1080p is not, it is a bandwidth/hardware limit, not the app.

## Output Layout

```text
<SaveDir>/
├── Images/     *.png
├── Videos/     *.avi
└── Metadata/   *.json
```

## Metadata Format

Each image or video gets a JSON file with the same basename:

```json
{
  "timestamp": "2026-05-29T15:42:00",
  "sample": "embryo",
  "id": "01",
  "condition": "WT",
  "magnification": "40x",
  "notes": "test image",
  "media_file": "embryo_01_WT_40x.png",
  "media_type": "image",
  "camera": "1: HDMI Capture"
}
```

## Filename Behavior

- You can type any filename before saving.
- Invalid characters are removed automatically.
- If a file already exists, the app appends `_001`, `_002`, etc. instead of overwriting.

## Video Notes

- Recordings are saved as uncompressed AVI (codec preference: `DIB `, then `IYUV`).
- Uncompressed AVI files are large by design to preserve raw frames.
- Verify playback and file size on your Windows laptop before long recordings.

## Windows Verification Checklist

1. Copy the project to a short local path such as `C:\MicroscopeCapture`.
2. Install Python dependencies in a virtual environment (`setup.bat`).
3. Connect the a6700 + HDMI capture dongle.
4. Confirm the device appears in the camera dropdown.
5. Verify live preview at expected resolution.
6. Capture a PNG and confirm image + metadata JSON.
7. Record a short AVI and confirm playback speed and file size.
8. Point **Save Directory** to Dropbox if you want captured data synced to the cloud.

## Development Notes

- The app uses DirectShow (`CAP_DSHOW`) on Windows and the default backend elsewhere.
- macOS can be used for UI smoke testing with a built-in webcam, but HDMI capture must be validated on Windows.

## License

Internal lab use. Add a license here if you distribute the project.
