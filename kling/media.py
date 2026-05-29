"""Media normalization helpers for Kling API payloads."""

from __future__ import annotations

import base64
import os
from pathlib import Path


def normalize_image(image: str | os.PathLike[str]) -> str:
    """Return a Kling-compatible image string from a URL, path, base64, or data URI."""

    value = os.fspath(image)
    stripped = value.strip()

    if stripped.startswith(("http://", "https://")):
        return stripped
    if stripped.startswith("data:") and "base64," in stripped:
        return stripped.split("base64,", 1)[1].strip()

    path = Path(value).expanduser()
    if path.is_file():
        return base64.b64encode(path.read_bytes()).decode("ascii")

    return stripped
