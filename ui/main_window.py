"""Main application window for microscope capture."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from capture.devices import CaptureDevice, list_capture_devices
from capture.naming import (
    build_auto_filename,
    build_metadata,
    ensure_output_dirs,
    resolve_unique_path,
    sanitize_filename,
    validate_save_directory,
    write_metadata,
)
from capture.worker import CaptureWorker, RecordingResult

# Resolution presets: label -> (width, height) or None for camera default.
RESOLUTION_PRESETS: list[tuple[str, tuple[int, int] | None]] = [
    ("Auto (camera default)", None),
    ("1920 x 1080", (1920, 1080)),
    ("1280 x 720", (1280, 720)),
    ("640 x 480", (640, 480)),
]


MAX_ZOOM = 8.0


class PreviewLabel(QLabel):
    """Live preview with digital zoom and drag-to-pan.

    The visible region is a sub-rectangle of the source frame defined by a
    zoom factor and a normalized center. At zoom 1.0 the whole frame is shown;
    zooming in shows a smaller region scaled to fill the panel, and dragging
    pans that region around.
    """

    view_changed = Signal(float)  # current zoom factor

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background-color: #111; color: #ccc;")
        self.setText("No preview")
        self._source: QPixmap | None = None
        self._display_rect = QRect()
        self._zoom = 1.0
        self._cx = 0.5
        self._cy = 0.5
        self._pan_last = None

    def set_frame(self, frame: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        image = QImage(rgb.data, width, height, channels * width, QImage.Format.Format_RGB888)
        self._source = QPixmap.fromImage(image)
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def set_zoom(self, factor: float) -> None:
        factor = max(1.0, min(MAX_ZOOM, float(factor)))
        if abs(factor - self._zoom) < 1e-6:
            return
        self._zoom = factor
        self._clamp_center()
        self.update()
        self.view_changed.emit(self._zoom)

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._cx = 0.5
        self._cy = 0.5
        self.update()
        self.view_changed.emit(self._zoom)

    def visible_roi(self) -> tuple[float, float, float, float]:
        """Return the visible region as normalized (x, y, w, h)."""
        w = 1.0 / self._zoom
        h = 1.0 / self._zoom
        x = min(max(0.0, self._cx - w / 2), 1.0 - w)
        y = min(max(0.0, self._cy - h / 2), 1.0 - h)
        return (x, y, w, h)

    def _clamp_center(self) -> None:
        half_w = 1.0 / self._zoom / 2
        half_h = 1.0 / self._zoom / 2
        self._cx = min(max(self._cx, half_w), 1.0 - half_w)
        self._cy = min(max(self._cy, half_h), 1.0 - half_h)

    def _displayed_pixmap(self) -> QPixmap | None:
        if self._source is None or self._source.isNull():
            return None
        if self._zoom <= 1.0:
            return self._source
        x, y, w, h = self.visible_roi()
        sw = self._source.width()
        sh = self._source.height()
        return self._source.copy(
            int(x * sw), int(y * sh), max(1, int(w * sw)), max(1, int(h * sh))
        )

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        super().resizeEvent(event)
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._zoom > 1.0 and self._source is not None:
            self._pan_last = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._pan_last is None or self._display_rect.isNull():
            return
        pos = event.position()
        dx = pos.x() - self._pan_last.x()
        dy = pos.y() - self._pan_last.y()
        self._pan_last = pos
        w = 1.0 / self._zoom
        h = 1.0 / self._zoom
        # Move the view opposite to the drag so the image follows the cursor.
        self._cx -= dx * (w / self._display_rect.width())
        self._cy -= dy * (h / self._display_rect.height())
        self._clamp_center()
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001, N802
        self._pan_last = None
        self.unsetCursor()

    def wheelEvent(self, event) -> None:  # noqa: ANN001, N802
        if self._source is None:
            return
        steps = event.angleDelta().y() / 120.0
        if steps == 0:
            return
        self.set_zoom(self._zoom * (1.25 ** steps))

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111"))
        pixmap = self._displayed_pixmap()
        self._display_rect = self._rect_for(pixmap)
        if pixmap is not None and not pixmap.isNull():
            painter.drawPixmap(self._display_rect, pixmap)
        else:
            painter.setPen(QColor("#ccc"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No preview")

        if self._zoom > 1.0:
            painter.setPen(QColor("#33ff88"))
            painter.drawText(10, 22, f"{self._zoom:.1f}x  (drag to pan)")
        painter.end()

    def _rect_for(self, pixmap: QPixmap | None) -> QRect:
        if pixmap is None or pixmap.isNull():
            return QRect()
        sw = pixmap.width()
        sh = pixmap.height()
        lw = self.width()
        lh = self.height()
        if sw == 0 or sh == 0:
            return QRect()
        scale = min(lw / sw, lh / sh)
        dw = int(sw * scale)
        dh = int(sh * scale)
        ox = (lw - dw) // 2
        oy = (lh - dh) // 2
        return QRect(ox, oy, dw, dh)


class MainWindow(QMainWindow):
    """Single-window microscope capture UI."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Microscope Capture")
        self.resize(980, 820)

        self._worker = CaptureWorker(self)
        self._devices: list[CaptureDevice] = []
        self._active_camera_label = "Unknown"
        self._recording_started_at: float | None = None
        self._pending_video_collision = False
        self._default_save_dir = Path.home() / "MicroscopeData"
        try:
            self._default_save_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            self._default_save_dir = Path.home()

        self.preview = PreviewLabel()
        self.camera_combo = QComboBox()
        self.resolution_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh")
        self.sample_input = QLineEdit()
        self.id_input = QLineEdit()
        self.condition_input = QLineEdit()
        self.magnification_input = QLineEdit()
        self.notes_input = QLineEdit()
        self.filename_input = QLineEdit()
        self.autofill_button = QPushButton("Auto-fill")
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, int(MAX_ZOOM * 10))
        self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x")
        self.reset_view_button = QPushButton("Reset View")
        self.save_cropped_checkbox = QCheckBox("Save visible region only")
        self.save_cropped_checkbox.setChecked(True)
        self.save_dir_input = QLineEdit(str(self._default_save_dir))
        self.browse_button = QPushButton("Browse")
        self.capture_button = QPushButton("Capture Image")
        self.record_button = QPushButton("Start Recording")
        self.status_label = QLabel("Status: Ready")

        self.capture_button.setMinimumHeight(40)
        self.record_button.setMinimumHeight(40)
        # Cool color for capture, warm color for recording; white bold text
        # keeps the labels legible against the saturated backgrounds.
        self.capture_button.setStyleSheet(
            "QPushButton { background-color: #1565C0; color: #FFFFFF; font-weight: bold;"
            " border: none; border-radius: 6px; padding: 8px; }"
            " QPushButton:hover { background-color: #1976D2; }"
            " QPushButton:pressed { background-color: #0D47A1; }"
            " QPushButton:disabled { background-color: #90A4AE; color: #ECEFF1; }"
        )
        self._apply_record_button_style(recording=False)

        for label, _ in RESOLUTION_PRESETS:
            self.resolution_combo.addItem(label)
        # Default to Full HD when available.
        default_res = next(
            (i for i, (_, r) in enumerate(RESOLUTION_PRESETS) if r == (1920, 1080)), 0
        )
        self.resolution_combo.setCurrentIndex(default_res)

        self._build_layout()
        self._connect_signals()
        self.refresh_devices()

        self._record_timer = QTimer(self)
        self._record_timer.setInterval(500)
        self._record_timer.timeout.connect(self._update_recording_status)

    def _build_layout(self) -> None:
        # --- Left: image panel ---
        image_panel = QGroupBox("Live Image")
        image_layout = QVBoxLayout(image_panel)
        image_layout.setContentsMargins(6, 6, 6, 6)
        image_layout.addWidget(self.preview)

        # --- Right: settings panel ---
        camera_row = QHBoxLayout()
        camera_row.addWidget(QLabel("Camera:"))
        camera_row.addWidget(self.camera_combo, stretch=1)

        resolution_row = QHBoxLayout()
        resolution_row.addWidget(QLabel("Resolution:"))
        resolution_row.addWidget(self.resolution_combo, stretch=1)
        resolution_row.addWidget(self.refresh_button)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom:"))
        zoom_row.addWidget(self.zoom_slider, stretch=1)
        zoom_row.addWidget(self.zoom_value_label)
        zoom_row.addWidget(self.reset_view_button)

        crop_row = QHBoxLayout()
        crop_row.addWidget(self.save_cropped_checkbox)
        crop_row.addStretch(1)

        form = QFormLayout()
        form.addRow("Sample:", self.sample_input)
        form.addRow("ID:", self.id_input)
        form.addRow("Condition:", self.condition_input)
        form.addRow("Magnification:", self.magnification_input)
        form.addRow("Notes:", self.notes_input)

        filename_row = QHBoxLayout()
        filename_row.addWidget(self.filename_input, stretch=1)
        filename_row.addWidget(self.autofill_button)

        save_row = QHBoxLayout()
        save_row.addWidget(self.save_dir_input, stretch=1)
        save_row.addWidget(self.browse_button)

        controls = QGroupBox("Capture Settings")
        controls_layout = QVBoxLayout(controls)
        controls_layout.addLayout(form)
        controls_layout.addWidget(QLabel("Filename (without extension):"))
        controls_layout.addLayout(filename_row)
        controls_layout.addWidget(
            QLabel("Auto-fill: YYYYMMDD_HHMMSS_SAMPLE_ID_CONDITION_MAGNIFICATION")
        )
        controls_layout.addWidget(QLabel("Save Directory:"))
        controls_layout.addLayout(save_row)

        button_row = QHBoxLayout()
        button_row.addWidget(self.capture_button)
        button_row.addWidget(self.record_button)

        settings_panel = QWidget()
        settings_panel.setMaximumWidth(440)
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.addWidget(
            QLabel("Zoom with the slider or mouse wheel; drag the image to pan.")
        )
        settings_layout.addLayout(camera_row)
        settings_layout.addLayout(resolution_row)
        settings_layout.addLayout(zoom_row)
        settings_layout.addLayout(crop_row)
        settings_layout.addWidget(controls)
        settings_layout.addLayout(button_row)
        settings_layout.addStretch(1)
        settings_layout.addWidget(self.status_label)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(image_panel, stretch=3)
        layout.addWidget(settings_panel, stretch=2)
        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh_devices)
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self.autofill_button.clicked.connect(self._autofill_filename)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider)
        self.reset_view_button.clicked.connect(self.preview.reset_view)
        self.preview.view_changed.connect(self._on_view_changed)
        self.browse_button.clicked.connect(self._browse_save_dir)
        self.capture_button.clicked.connect(self.capture_image)
        self.record_button.clicked.connect(self.toggle_recording)

        self._worker.frame_ready.connect(self.preview.set_frame)
        self._worker.error_occurred.connect(self._show_error)
        self._worker.camera_opened.connect(self._on_camera_opened)
        self._worker.recording_started.connect(self._on_recording_started)
        self._worker.recording_stopped.connect(self._on_recording_stopped)

    def _apply_record_button_style(self, recording: bool) -> None:
        # Warm tones: orange-red when idle, deeper red while recording.
        base = "#D84315" if recording else "#E64A19"
        hover = "#BF360C" if recording else "#F4511E"
        self.record_button.setStyleSheet(
            f"QPushButton {{ background-color: {base}; color: #FFFFFF; font-weight: bold;"
            " border: none; border-radius: 6px; padding: 8px; }"
            f" QPushButton:hover {{ background-color: {hover}; }}"
            " QPushButton:disabled { background-color: #BCAAA4; color: #EFEBE9; }"
        )

    def _selected_resolution(self) -> tuple[int, int] | None:
        return RESOLUTION_PRESETS[self.resolution_combo.currentIndex()][1]

    def refresh_devices(self) -> None:
        current_index = self.camera_combo.currentData()
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        self._devices = list_capture_devices()
        if not self._devices:
            self.camera_combo.addItem("No devices found", userData=None)
            self.set_status("No capture devices detected.")
        else:
            selected_row = 0
            for row, device in enumerate(self._devices):
                self.camera_combo.addItem(device.label, userData=device.index)
                if current_index == device.index:
                    selected_row = row
            self.camera_combo.setCurrentIndex(selected_row)
        self.camera_combo.blockSignals(False)
        if self._devices:
            self._on_camera_changed(self.camera_combo.currentIndex())

    def _on_camera_changed(self, _row: int) -> None:
        index = self.camera_combo.currentData()
        if index is None:
            self._worker.close_camera()
            return
        device = next((item for item in self._devices if item.index == index), None)
        self._active_camera_label = device.label if device else str(index)
        self._worker.open_camera(index, self._selected_resolution())
        self.set_status(f"Opening camera {self._active_camera_label}...")

    def _on_resolution_changed(self, _row: int) -> None:
        if self.camera_combo.currentData() is None:
            return
        self._worker.set_resolution(self._selected_resolution())
        label = self.resolution_combo.currentText()
        self.set_status(f"Requested resolution: {label}")

    def _on_zoom_slider(self, value: int) -> None:
        self.preview.set_zoom(value / 10.0)

    def _on_view_changed(self, zoom: float) -> None:
        self.zoom_value_label.setText(f"{zoom:.1f}x")
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(round(zoom * 10)))
        self.zoom_slider.blockSignals(False)
        if zoom > 1.0:
            self.set_status(f"Zoom {zoom:.1f}x (drag image to pan)")
        else:
            self.set_status("View reset to full frame.")

    def _on_camera_opened(self, index: int, fps: float, width: int, height: int) -> None:
        self.set_status(
            f"Camera ready: index {index}, {width}x{height} @ {fps:.1f} FPS"
        )

    def _autofill_filename(self) -> None:
        self.filename_input.setText(
            build_auto_filename(
                self.sample_input.text(),
                self.id_input.text(),
                self.condition_input.text(),
                self.magnification_input.text(),
            )
        )

    def _safe_start_dir(self) -> str:
        """Return an existing directory to open the file dialog at.

        A non-existent path (e.g. a default that was never created) can make
        the native dialog hang, so walk up to the first existing parent.
        """
        candidate = Path(self.save_dir_input.text().strip() or str(self._default_save_dir))
        probe = candidate
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        if not probe.exists():
            probe = Path.home()
        return str(probe)

    def _browse_save_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            self._safe_start_dir(),
        )
        if directory:
            self.save_dir_input.setText(directory)

    def _save_directory(self) -> Path:
        return Path(self.save_dir_input.text().strip() or str(self._default_save_dir))

    def _stem_from_input(self) -> str:
        stem = sanitize_filename(self.filename_input.text())
        if not stem:
            raise ValueError("Enter a filename before saving.")
        return stem

    def _metadata_context(self, media_file: str, media_type: str) -> dict:
        return build_metadata(
            timestamp=datetime.now(),
            sample=self.sample_input.text().strip(),
            record_id=self.id_input.text().strip(),
            condition=self.condition_input.text().strip(),
            magnification=self.magnification_input.text().strip(),
            notes=self.notes_input.text().strip(),
            media_file=media_file,
            media_type=media_type,
            camera=self._active_camera_label,
        )

    def _apply_crop(self, frame: np.ndarray) -> np.ndarray:
        """Crop to the visible (zoomed/panned) region when requested.

        At zoom 1.0 the visible region is the whole frame, so this is a no-op.
        """
        if not self.save_cropped_checkbox.isChecked():
            return frame
        nx, ny, nw, nh = self.preview.visible_roi()
        height, width = frame.shape[:2]
        x0 = max(0, int(nx * width))
        y0 = max(0, int(ny * height))
        x1 = min(width, int((nx + nw) * width))
        y1 = min(height, int((ny + nh) * height))
        if x1 - x0 < 1 or y1 - y0 < 1:
            return frame
        return frame[y0:y1, x0:x1].copy()

    def capture_image(self) -> None:
        try:
            save_dir = self._save_directory()
            validate_save_directory(save_dir)
            dirs = ensure_output_dirs(save_dir)
            stem = self._stem_from_input()
            image_path, renamed = resolve_unique_path(dirs["images"], stem, ".png")
            frame = self._worker.latest_frame()
            if frame is None:
                raise RuntimeError("No frame available to capture.")

            frame = self._apply_crop(frame)
            if not cv2.imwrite(str(image_path), frame):
                raise RuntimeError(f"Failed to save image: {image_path}")

            metadata = self._metadata_context(image_path.name, "image")
            meta_path = write_metadata(dirs["metadata"], image_path.stem, metadata)

            message = f"Saved image: {image_path.name} ({frame.shape[1]}x{frame.shape[0]})"
            if renamed:
                message += " (filename adjusted to avoid overwrite)"
            message += f"; metadata: {meta_path.name}"
            self.set_status(message)
        except Exception as exc:  # noqa: BLE001
            self._show_error(str(exc))

    def toggle_recording(self) -> None:
        if self.record_button.text() == "Stop Recording":
            self._worker.stop_recording()
            return
        try:
            save_dir = self._save_directory()
            validate_save_directory(save_dir)
            dirs = ensure_output_dirs(save_dir)
            stem = self._stem_from_input()
            video_path, renamed = resolve_unique_path(dirs["videos"], stem, ".avi")
            self._pending_video_collision = renamed
            self._pending_video_stem = video_path.stem
            self._worker.start_recording(video_path)
            if renamed:
                self.set_status(
                    f"Recording to {video_path.name} (filename adjusted to avoid overwrite)"
                )
        except Exception as exc:  # noqa: BLE001
            self._show_error(str(exc))

    def _on_recording_started(self, path: str) -> None:
        self._recording_started_at = time.time()
        self.record_button.setText("Stop Recording")
        self._apply_record_button_style(recording=True)
        self.capture_button.setEnabled(False)
        self._record_timer.start()
        self.set_status(f"Recording: {Path(path).name}")

    def _on_recording_stopped(self, result: RecordingResult | None) -> None:
        self._record_timer.stop()
        self._recording_started_at = None
        self.record_button.setText("Start Recording")
        self._apply_record_button_style(recording=False)
        self.capture_button.setEnabled(True)

        if result is None:
            self.set_status("Recording stopped.")
            return

        try:
            save_dir = self._save_directory()
            dirs = ensure_output_dirs(save_dir)
            metadata = self._metadata_context(result.path.name, "video")
            meta_path = write_metadata(dirs["metadata"], result.path.stem, metadata)
            elapsed = result.frame_count / result.fps if result.fps else 0.0
            message = (
                f"Saved video: {result.path.name} "
                f"({result.frame_count} frames, ~{elapsed:.1f}s); metadata: {meta_path.name}"
            )
            if getattr(self, "_pending_video_collision", False):
                message += " (filename adjusted to avoid overwrite)"
            self.set_status(message)
        except Exception as exc:  # noqa: BLE001
            self._show_error(str(exc))

    def _update_recording_status(self) -> None:
        if self._recording_started_at is None:
            return
        elapsed = time.time() - self._recording_started_at
        self.status_label.setText(f"Status: Recording... {elapsed:.1f}s")

    def set_status(self, message: str) -> None:
        self.status_label.setText(f"Status: {message}")

    def _show_error(self, message: str) -> None:
        self.set_status(f"Error: {message}")
        QMessageBox.warning(self, "Microscope Capture", message)

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        self._worker.close_camera()
        self._worker.wait(2000)
        super().closeEvent(event)
