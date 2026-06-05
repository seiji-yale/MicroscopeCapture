"""Enumerate video capture devices with platform-specific backends."""

from __future__ import annotations

import sys
from dataclasses import dataclass

import cv2

# Quiet OpenCV's videoio logger. Probing indices that do not map to a real
# device makes DSHOW print "backend is generally available but can't be used
# to capture by index" for every miss; those messages are harmless noise.
try:  # pragma: no cover - depends on OpenCV build
    cv2.setLogLevel(0)
except Exception:  # noqa: BLE001
    pass


@dataclass(frozen=True)
class CaptureDevice:
    """A discoverable camera or HDMI capture device."""

    index: int
    name: str

    @property
    def label(self) -> str:
        return f"{self.index}: {self.name}"


def _capture_backend() -> int:
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY


def _probe_device(index: int) -> bool:
    backend = _capture_backend()
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
    # On macOS, reading without Camera permission spams the terminal and is slow.
    # Treat a successfully opened device as present; preview will prompt for access.
    if sys.platform == "darwin":
        cap.release()
        return True
    ok, _ = cap.read()
    cap.release()
    return ok


def _windows_device_names(max_index: int = 10) -> dict[int, str]:
    try:
        from pygrabber.dshow_graph import FilterGraph  # type: ignore[import-untyped]

        graph = FilterGraph()
        names = graph.get_input_devices()
        return {idx: name for idx, name in enumerate(names) if idx < max_index}
    except Exception:  # noqa: BLE001
        return {}


def list_capture_devices(max_index: int = 10) -> list[CaptureDevice]:
    """Return devices that OpenCV can open on this platform.

    On Windows we only probe indices that pygrabber actually reports, which
    avoids opening (and warning about) non-existent device indices.
    """
    if sys.platform == "darwin":
        max_index = min(max_index, 2)

    names: dict[int, str] = {}
    probe_count = max_index
    if sys.platform == "win32":
        names = _windows_device_names(max_index=max_index)
        if names:
            probe_count = max(names) + 1

    devices: list[CaptureDevice] = []
    for index in range(probe_count):
        if not _probe_device(index):
            continue
        name = names.get(index, f"Camera {index}")
        devices.append(CaptureDevice(index=index, name=name))
    return devices


def open_capture(index: int) -> cv2.VideoCapture:
    """Open a capture device using the platform-preferred backend."""
    cap = cv2.VideoCapture(index, _capture_backend())
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open capture device at index {index}.")
    return cap
