"""Filename helpers and metadata serialization."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")


def sanitize_filename(name: str) -> str:
    """Remove invalid path characters and collapse whitespace."""
    cleaned = INVALID_CHARS.sub("", name.strip())
    cleaned = WHITESPACE.sub("_", cleaned)
    cleaned = cleaned.strip("._")
    return cleaned or "capture"


def sanitize_token(value: str) -> str:
    token = sanitize_filename(value)
    return token.replace(" ", "_")


def build_auto_filename(
    sample: str,
    record_id: str,
    condition: str,
    magnification: str,
    when: datetime | None = None,
) -> str:
    """Build YYYYMMDD_HHMMSS_SAMPLE_ID_CONDITION_MAGNIFICATION."""
    moment = when or datetime.now()
    parts = [
        moment.strftime("%Y%m%d_%H%M%S"),
        sanitize_token(sample) if sample else "sample",
        sanitize_token(record_id) if record_id else "id",
        sanitize_token(condition) if condition else "condition",
        sanitize_token(magnification) if magnification else "mag",
    ]
    return "_".join(parts)


def ensure_output_dirs(save_dir: Path) -> dict[str, Path]:
    """Create Images, Videos, and Metadata folders under save_dir."""
    images = save_dir / "Images"
    videos = save_dir / "Videos"
    metadata = save_dir / "Metadata"
    for folder in (images, videos, metadata):
        folder.mkdir(parents=True, exist_ok=True)
    return {"images": images, "videos": videos, "metadata": metadata}


def resolve_unique_path(directory: Path, stem: str, suffix: str) -> tuple[Path, bool]:
    """
    Return a non-colliding file path.

    If stem.suffix exists, append _001, _002, ... and report collision.
    """
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate, False

    counter = 1
    while True:
        numbered = directory / f"{stem}_{counter:03d}{suffix}"
        if not numbered.exists():
            return numbered, True
        counter += 1


def build_metadata(
    *,
    timestamp: datetime,
    sample: str,
    record_id: str,
    condition: str,
    magnification: str,
    notes: str,
    media_file: str,
    media_type: str,
    camera: str,
) -> dict[str, Any]:
    """Build metadata dict with stable field order."""
    return {
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "sample": sample,
        "id": record_id,
        "condition": condition,
        "magnification": magnification,
        "notes": notes,
        "media_file": media_file,
        "media_type": media_type,
        "camera": camera,
    }


def write_metadata(metadata_dir: Path, stem: str, metadata: dict[str, Any]) -> Path:
    path = metadata_dir / f"{stem}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def validate_save_directory(save_dir: Path) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    probe = save_dir / ".write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise PermissionError(f"Save directory is not writable: {save_dir}") from exc
