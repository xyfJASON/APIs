"""Transport client shared by Kling API wrappers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .errors import KlingAPIError, KlingError


DEFAULT_BASE_URL = "https://api-beijing.klingai.com"


class KlingClient:
    """Authenticated JSON client for Kling APIs."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        request_timeout: float = 60,
    ) -> None:
        if not access_key:
            raise KlingError("Kling access key is required")
        if not secret_key:
            raise KlingError("Kling secret key is required")

        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout

    @classmethod
    def from_env(cls) -> "KlingClient":
        """Build a transport client from KLING_ACCESS_KEY and KLING_SECRET_KEY."""

        access_key = os.environ.get("KLING_ACCESS_KEY", "")
        secret_key = os.environ.get("KLING_SECRET_KEY", "")
        base_url = os.environ.get("KLING_BASE_URL", DEFAULT_BASE_URL)

        missing = [
            name
            for name, value in (
                ("KLING_ACCESS_KEY", access_key),
                ("KLING_SECRET_KEY", secret_key),
            )
            if not value
        ]
        if missing:
            raise KlingError(f"Missing required environment variable(s): {', '.join(missing)}")

        return cls(access_key, secret_key, base_url=base_url)

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", path, json_body=payload)

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path
        body = None
        headers = {
            "Authorization": f"Bearer {self.encode_jwt_token()}",
            "Content-Type": "application/json",
        }

        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")

        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            payload = self._decode_json(raw, status=exc.code)
            message = payload.get("message") if isinstance(payload, dict) else str(exc)
            raise KlingAPIError(
                message or str(exc),
                code=payload.get("code") if isinstance(payload, dict) else None,
                status=exc.code,
                request_id=payload.get("request_id") if isinstance(payload, dict) else None,
                response=payload,
            ) from exc
        except urllib.error.URLError as exc:
            raise KlingAPIError(f"Kling request failed: {exc.reason}") from exc

        payload = self._decode_json(raw, status=status)
        code = payload.get("code")
        if code not in (None, 0):
            raise KlingAPIError(
                payload.get("message", "Kling API returned an error"),
                code=code,
                status=status,
                request_id=payload.get("request_id"),
                response=payload,
            )
        return payload

    def download(self, url: str, output_path: str | os.PathLike[str]) -> str:
        destination = Path(output_path).expanduser()
        if destination.parent != Path("."):
            destination.parent.mkdir(parents=True, exist_ok=True)

        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                destination.write_bytes(response.read())
        except urllib.error.URLError as exc:
            raise KlingAPIError(f"Failed to download Kling video: {exc.reason}") from exc

        return str(destination)

    def encode_jwt_token(self) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.access_key,
            "exp": now + 1800,
            "nbf": now - 5,
        }

        header_part = self._base64url_json(header)
        payload_part = self._base64url_json(payload)
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        signature = hmac.new(self.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        signature_part = self._base64url_bytes(signature)
        return f"{header_part}.{payload_part}.{signature_part}"

    @staticmethod
    def _decode_json(raw: bytes, *, status: int) -> dict[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KlingAPIError(f"Kling API returned invalid JSON (HTTP {status})", status=status) from exc

        if not isinstance(payload, dict):
            raise KlingAPIError("Kling API returned a non-object JSON payload", status=status, response=payload)
        return payload

    @staticmethod
    def _base64url_json(value: dict[str, Any]) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return KlingClient._base64url_bytes(raw)

    @staticmethod
    def _base64url_bytes(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
