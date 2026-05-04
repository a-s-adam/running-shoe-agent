from __future__ import annotations

import base64
import io
from typing import Optional, Tuple

import requests


# Keep thumbnails small enough to store directly in a free-tier database row.
def compress_image_bytes(
    raw: bytes,
    max_dim: int = 420,
    quality: int = 62,
    max_bytes: int = 45_000,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Compress image bytes into a small data URI for free-tier database storage.
    Returns (data_uri, mime_type). Pillow is optional so scraping can still run without it.
    """
    try:
        from PIL import Image
    except ImportError:
        return None, None

    try:
        image = Image.open(io.BytesIO(raw))
        image.thumbnail((max_dim, max_dim))

        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")

        for candidate_quality in (quality, 55, 45, 35):
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=candidate_quality, method=6)
            payload = buffer.getvalue()
            if len(payload) <= max_bytes or candidate_quality == 35:
                encoded = base64.b64encode(payload).decode("ascii")
                return f"data:image/webp;base64,{encoded}", "image/webp"
    except Exception:
        return None, None

    return None, None


def fetch_and_compress_image(
    image_url: str,
    max_dim: int = 420,
    quality: int = 62,
    max_bytes: int = 45_000,
    timeout: int = 20,
) -> Tuple[Optional[str], Optional[str]]:
    """Download an image and convert it into the compact thumbnail format."""
    if not image_url:
        return None, None

    response = requests.get(
        image_url,
        timeout=timeout,
        headers={"User-Agent": "running-shoe-agent/0.1 image-cache"},
    )
    response.raise_for_status()
    return compress_image_bytes(response.content, max_dim=max_dim, quality=quality, max_bytes=max_bytes)
