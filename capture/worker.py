"""Background capture thread for preview and uncompressed AVI recording."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal

from capture.devices import open_capture

# Uncompressed AVI on Windows; fallback codecs tried in order if unavailable.
VIDEO_CODEC_CANDIDATES: tuple[int, ...] = (
    cv2.VideoWriter_fourcc(*"DIB "),  # uncompressed RGB/BMP in AVI (Windows)
    cv2.VideoWriter_fourcc(*"IYUV"),  # uncompressed YUV 4:2:0
    0,
)


@dataclass
class RecordingResult:
    path: Path
    frame_count: int
    fps: float
    width: int
    height: int


class CaptureWorker(QThread):
    """Reads frames from a capture device on a dedicated thread."""

    frame_ready = Signal(object)  # numpy.ndarray (BGR)
    error_occurred = Signal(str)
    camera_opened = Signal(int, float, int, int)  # index, fps, width, height
    camera_closed = Signal()
    recording_started = Signal(str)
    recording_stopped = Signal(object)  # RecordingResult | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mutex = QMutex()
        self._running = False
        self._device_index: int | None = None
        self._desired_size: tuple[int, int] | None = None
        self._desired_fps: float | None = None
        self._reopen_requested = False
        self._cap: cv2.VideoCapture | None = None
        self._latest_frame: np.ndarray | None = None
        self._recording = False
        self._writer: cv2.VideoWriter | None = None
        self._record_path: Path | None = None
        self._record_frame_count = 0
        self._record_fps = 30.0
        self._record_size: tuple[int, int] = (0, 0)
        self._consecutive_failures = 0

    def open_camera(
        self,
        index: int,
        size: tuple[int, int] | None = None,
        fps: float | None = None,
    ) -> None:
        with QMutexLocker(self._mutex):
            self._device_index = index
            self._desired_size = size
            self._desired_fps = fps
            self._running = True
            self._reopen_requested = True
            if not self.isRunning():
                self.start()

    def set_format(
        self, size: tuple[int, int] | None, fps: float | None
    ) -> None:
        """Request a new capture resolution and/or frame rate (None = device default)."""
        with QMutexLocker(self._mutex):
            self._desired_size = size
            self._desired_fps = fps
            self._reopen_requested = True

    def close_camera(self) -> None:
        """Ask the worker thread to stop; capture is released on the worker thread only."""
        with QMutexLocker(self._mutex):
            self._running = False
            self._device_index = None
            self._reopen_requested = False
            self._stop_recording_locked()

    def latest_frame(self) -> np.ndarray | None:
        with QMutexLocker(self._mutex):
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def start_recording(self, output_path: Path) -> None:
        with QMutexLocker(self._mutex):
            if self._recording:
                raise RuntimeError("Recording is already in progress.")
            if self._latest_frame is None:
                raise RuntimeError("No frame available to start recording.")
            height, width = self._latest_frame.shape[:2]
            fps = self._capture_fps_locked()
            writer = self._create_writer(output_path, fps, width, height)
            if writer is None or not writer.isOpened():
                raise RuntimeError("Unable to open video writer for uncompressed AVI.")
            self._writer = writer
            self._record_path = output_path
            self._record_frame_count = 0
            self._record_fps = fps
            self._record_size = (width, height)
            self._recording = True
            self.recording_started.emit(str(output_path))

    def stop_recording(self) -> RecordingResult | None:
        with QMutexLocker(self._mutex):
            return self._stop_recording_locked()

    def run(self) -> None:
        while True:
            open_error: str | None = None
            with QMutexLocker(self._mutex):
                if not self._running:
                    break
                index = self._device_index
                desired = self._desired_size
                desired_fps = self._desired_fps
                if self._reopen_requested:
                    self._reopen_requested = False
                    self._stop_recording_locked()
                    self._close_capture_locked()
                if index is None:
                    cap = None
                else:
                    try:
                        self._ensure_capture_open_locked(index, desired, desired_fps)
                    except Exception as exc:  # noqa: BLE001
                        open_error = str(exc)
                        cap = None
                    else:
                        cap = self._cap

            if open_error is not None:
                self.error_occurred.emit(open_error)
                time.sleep(0.5)
                continue

            if index is None:
                time.sleep(0.05)
                continue

            if cap is None or not cap.isOpened():
                time.sleep(0.05)
                continue

            ok, frame = cap.read()
            with QMutexLocker(self._mutex):
                if not self._running:
                    break
                if not ok or frame is None:
                    pass
                else:
                    self._latest_frame = frame
                    if self._recording and self._writer is not None:
                        self._writer.write(frame)
                        self._record_frame_count += 1

            if not self._running:
                break

            if not ok or frame is None:
                self._consecutive_failures += 1
                if self._consecutive_failures >= 30:
                    self.error_occurred.emit(
                        "Camera disconnected or stopped delivering frames."
                    )
                    with QMutexLocker(self._mutex):
                        self._stop_recording_locked()
                        self._close_capture_locked()
                    self._consecutive_failures = 0
                time.sleep(0.03)
                continue

            self._consecutive_failures = 0
            self.frame_ready.emit(frame)
            time.sleep(0.001)

        with QMutexLocker(self._mutex):
            self._stop_recording_locked()
            self._close_capture_locked()

    def _ensure_capture_open_locked(
        self,
        index: int,
        desired: tuple[int, int] | None,
        desired_fps: float | None,
    ) -> None:
        """Open the capture device. Caller must hold ``self._mutex``."""
        if self._cap is not None and self._cap.isOpened():
            return
        self._close_capture_locked()
        cap = open_capture(index)
        # Request MJPG first: most UVC/HDMI capture dongles can only deliver
        # full resolution at usable frame rates in MJPG. The raw (YUYV) default
        # exceeds USB bandwidth at 1080p/4K, so the device silently drops FPS.
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        if desired is not None:
            target_w, target_h = desired
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(target_w))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(target_h))
        if desired_fps is not None:
            cap.set(cv2.CAP_PROP_FPS, float(desired_fps))
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:  # noqa: BLE001
            pass
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 1:
            fps = desired_fps if desired_fps and desired_fps > 1 else 30.0
        self._cap = cap
        self.camera_opened.emit(index, fps, width, height)

    def _capture_fps_locked(self) -> float:
        if self._cap is None:
            return 30.0
        fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        return fps if fps > 1 else 30.0

    def _create_writer(
        self, output_path: Path, fps: float, width: int, height: int
    ) -> cv2.VideoWriter | None:
        for fourcc in VIDEO_CODEC_CANDIDATES:
            writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            if writer.isOpened():
                return writer
            writer.release()
        return None

    def _stop_recording_locked(self) -> RecordingResult | None:
        if not self._recording:
            return None
        result: RecordingResult | None = None
        if self._record_path is not None:
            result = RecordingResult(
                path=self._record_path,
                frame_count=self._record_frame_count,
                fps=self._record_fps,
                width=self._record_size[0],
                height=self._record_size[1],
            )
        if self._writer is not None:
            self._writer.release()
        self._writer = None
        self._recording = False
        self._record_path = None
        self._record_frame_count = 0
        self.recording_stopped.emit(result)
        return result

    def _close_capture_locked(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self.camera_closed.emit()
