from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx


def _signature(params: dict[str, str], api_secret: str) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()


def upload_image_bytes(
    *,
    cloud_name: str,
    api_key: str,
    api_secret: str,
    folder: str,
    file_name: str,
    file_bytes: bytes,
    content_type: str | None,
    public_id: str,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    params_to_sign = {
        "folder": folder,
        "public_id": public_id,
        "timestamp": str(int(time.time())),
        "overwrite": "true",
    }
    signature = _signature(params_to_sign, api_secret)

    data = {
        **params_to_sign,
        "api_key": api_key,
        "signature": signature,
    }

    files = {
        "file": (
            file_name,
            file_bytes,
            content_type or "application/octet-stream",
        )
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(endpoint, data=data, files=files)

    if response.status_code >= 400:
        detail = response.text
        raise RuntimeError(f"Cloudinary upload failed: {response.status_code} {detail}")

    payload = response.json()
    if "secure_url" not in payload:
        raise RuntimeError("Cloudinary response did not include secure_url")
    return payload
