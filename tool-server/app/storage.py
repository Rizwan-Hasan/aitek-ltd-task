"""Saving generated images under unguessable file names."""

import re
import secrets
from pathlib import Path

from PIL import Image

# 128 bits of randomness: the URL itself acts as a capability token.
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{22}\.png$")


def is_valid_name(name: str) -> bool:
    return bool(_NAME_RE.fullmatch(name))


def save_image(image: Image.Image, directory: Path, max_images: int) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_urlsafe(16)}.png"
    image.save(directory / name, format="PNG")
    _prune(directory, max_images)
    return name


def _prune(directory: Path, keep: int) -> None:
    files = sorted(directory.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        old.unlink(missing_ok=True)
