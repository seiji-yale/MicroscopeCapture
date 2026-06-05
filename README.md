# Microscope Capture

Lightweight image and video acquisition application for scientific microscopy using a Sony a6700 (or similar camera) connected through an HDMI UVC capture device on Windows 11.

## Features

- Live preview from a selectable capture device
- Selectable capture resolution (up to 3840x2160 for 4K capture cards; default 1920x1080)
- Selectable frame rate (60 / 30 / 24 / 15 FPS or device default)
- Digital zoom with drag-to-pan; capture the visible region
- Still image capture to PNG
- Basic uncompressed AVI video recording
- User-editable filenames with optional Auto-fill template
- Optional warning before overwriting an existing filename (images and videos)
- Brief on-preview animation when a capture or recording is saved (no success popup)
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

Run the app **on the Mac whose screen you are using**, in a **local Terminal** window (Terminal.app or iTerm). Do **not** start it over `ssh` from another computer; macOS will not show the Qt window on the remote machine's display.

After `git pull` on branch `feature/ui-preview`, the window title should include **`(0.2-preview)`** and the settings panel should show **Frame rate** and **3840 x 2160 (4K)**. If not, run `git log -1 --oneline` and confirm you are not on `main` only.

```bash
cd MicroscopeCapture
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

If you see `OpenCV: not authorized to capture video`, open **System Settings → Privacy & Security → Camera** and enable access for **Terminal** (or iTerm). The main window should still appear even before camera access is granted; preview works after you allow the camera.

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
git pull origin main
```

If you see *no tracking information for the current branch*, run once:

```bat
git branch --set-upstream-to=origin/main main
git pull
```

### Windows troubleshooting

**`python` was not found** during `setup.bat`:

1. Install [Python 3.12+](https://www.python.org/downloads/windows/) or Miniforge.
2. Check **Add python.exe to PATH** during setup.
3. Disable the Microsoft Store alias: **Settings → Apps → Advanced app settings → App execution aliases** → turn off **python.exe** and **python3.exe**.
4. Open a **new** Command Prompt and run `python --version`, then `setup.bat` again.

**`git` is not recognized**: install [Git for Windows](https://git-scm.com/download/win), then open a new Command Prompt.

**`git pull` fails with no upstream**: use `git pull origin main` or the commands above.

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
4. Choose **Resolution** and **Frame rate** (for example **1920 x 1080** at **60 FPS**, or **3840 x 2160** at **30 FPS** with Cam Link 4K).
5. Enter metadata fields: Sample, ID, Condition, Magnification, Notes.
6. Enter any filename you want, or click **Auto-fill** for:
   `YYYYMMDD_HHMMSS_SAMPLE_ID_CONDITION_MAGNIFICATION`
7. Choose a save directory (default: `~/MicroscopeData`).
8. Click **Capture Image** for a PNG still, or **Start Recording** / **Stop Recording** for AVI.

### Resolution

- The **Resolution** dropdown requests a capture size from the device. It defaults to `1920 x 1080` for a responsive live preview.
- **`3840 x 2160 (4K)`** targets capture hardware such as the [Elgato Cam Link 4K](https://www.elgato.com/us/en/p/cam-link-4k) (HDMI up to 2160p; [supported modes](https://help.elgato.com/hc/en-us/articles/360028240951-Cam-Link-4K-Supported-Video-Sources) include 4K30 and 1080p60 depending on camera output and hardware revision).
- Set the **Sony a6700 HDMI output** to match (for example 4K30 or 1080p60). If the camera and dongle disagree, the device may fall back to another mode; the status line shows the actual `width x height @ FPS` after opening the camera.
- `Auto (camera default)` keeps whatever the device reports.
- The app requests the **MJPG** stream format so HDMI/UVC dongles can deliver high resolution within USB bandwidth (see Troubleshooting).
- **Frame rate:** Choose **60 FPS** for smooth 1080p live view (when the camera HDMI output and capture card support it). Use **30 FPS** for 4K. **Auto** leaves the rate to the device. The status line shows the actual FPS after the camera opens; some combinations fall back if HDMI or USB bandwidth does not allow the requested rate.
- **4K note:** Live preview at 4K is heavier than 1080p. Use 1080p while aligning the sample, then switch to 4K before capturing stills if the preview becomes choppy.

### Zoom, Pan, and Crop (live)

- Use the **Zoom** slider (or the mouse wheel over the image) to zoom from 1.0x to 8.0x.
- When zoomed in, **drag the image** to pan around; the visible region fills the panel.
- **Reset View** returns to the full frame (1.0x).
- **Save visible region only** (on by default): captured PNGs contain exactly what is shown. Turn it off to always save the full frame regardless of zoom.

### Save feedback and duplicate filenames

- After a still image or finished video is saved, the live preview shows a short green flash and a fading **Saved** label with the filename. Errors still use a dialog.
- **Warn when saving over an existing filename** (off by default): when enabled, saving an image or starting a recording with a name that already exists in `Images/` or `Videos/` opens a dialog with **Overwrite**, **Save with new name** (`_001`, …), or **Cancel**. When disabled, new files are renamed automatically as before.
- The duplicate-warning preference is remembered between sessions (Qt settings).

## Troubleshooting

### Preview stutters at Full HD or 4K

If the live preview is choppy even though the status shows 30 FPS:

- The app already requests the **MJPG** format, which is required for most USB HDMI capture dongles (including Cam Link 4K) to reach 1080p/4K within USB bandwidth. The raw (YUYV) default often exceeds bandwidth, so the device silently drops to a few FPS.
- **Cam Link 4K:** Use a **USB 3.x** port directly on the PC (not a hub). For 4K, set the camera HDMI output to **3840x2160** (typically 30 FPS unless your unit supports 4K60 with MJPEG).
- If 4K is choppy but 1080p is smooth, use **1920 x 1080** for live work and switch to **3840 x 2160** only when capturing stills.
- Try **1280 x 720** to verify smoothness; if 720p is smooth but 1080p is not, the bottleneck is bandwidth or the USB path, not the app.

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
