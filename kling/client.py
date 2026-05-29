"""Small standard-library client for Kling V3 image-to-video generation."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .errors import KlingAPIError, KlingError, KlingTaskFailed, KlingTimeout


DEFAULT_BASE_URL = "https://api-beijing.klingai.com"


@dataclasses.dataclass
class VideoResult:
    """Result returned by :meth:`KlingV3ImageToVideo.generate`."""

    task_id: str
    status: str
    url: str
    path: str | None
    duration: str | None
    raw: dict[str, Any]


class KlingV3ImageToVideo:
    """Kling V3 image-to-video wrapper with a local-model-style API."""

    model_name = "kling-v3"

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
    def from_env(cls) -> "KlingV3ImageToVideo":
        """Build a model wrapper from KLING_ACCESS_KEY and KLING_SECRET_KEY."""

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

    def generate(
        self,
        image: str | os.PathLike[str],
        prompt: str = "",
        output_path: str | os.PathLike[str] | None = None,
        duration: int | str = 5,
        mode: str = "std",
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> VideoResult:
        """Generate a video from an image and wait for the finished result."""

        create_response = self._create_task(
            image=image,
            prompt=prompt,
            duration=duration,
            mode=mode,
        )
        task_data = self._response_data(create_response)
        task_id = task_data.get("task_id")
        if not task_id:
            raise KlingAPIError("Kling create task response did not include task_id", response=create_response)

        final_data = self._wait_for_task(
            task_id=task_id,
            poll_interval=poll_interval,
            timeout=timeout,
        )
        video = self._first_video(final_data)
        url = video.get("url", "")
        if not url:
            raise KlingAPIError("Kling task succeeded but did not include a video URL", response=final_data)

        saved_path = None
        if output_path is not None:
            saved_path = self._download(url, output_path)

        return VideoResult(
            task_id=task_id,
            status=final_data.get("task_status", ""),
            url=url,
            path=saved_path,
            duration=video.get("duration"),
            raw=final_data,
        )

    def _create_task(
        self,
        *,
        image: str | os.PathLike[str],
        prompt: str,
        duration: int | str,
        mode: str,
    ) -> dict[str, Any]:
        payload = {
            "model_name": self.model_name,
            "image": self._normalize_image(image),
            "prompt": prompt or "",
            "duration": str(duration),
            "mode": mode,
        }
        return self._request("POST", "/v1/videos/image2video", json_body=payload)

    def _get_task(self, task_id: str) -> dict[str, Any]:
        quoted_id = urllib.parse.quote(task_id, safe="")
        return self._request("GET", f"/v1/videos/image2video/{quoted_id}")

    def _wait_for_task(self, *, task_id: str, poll_interval: float, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            response = self._get_task(task_id)
            data = self._response_data(response)
            status = data.get("task_status")

            if status == "succeed":
                return data
            if status == "failed":
                message = data.get("task_status_msg") or "Kling task failed"
                raise KlingTaskFailed(task_id, message, response=data)
            if time.monotonic() >= deadline:
                raise KlingTimeout(task_id, timeout)

            time.sleep(poll_interval)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path
        body = None
        headers = {
            "Authorization": f"Bearer {self._encode_jwt_token()}",
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

    def _encode_jwt_token(self) -> str:
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
    def _normalize_image(image: str | os.PathLike[str]) -> str:
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

    @staticmethod
    def _response_data(response: dict[str, Any]) -> dict[str, Any]:
        data = response.get("data")
        if not isinstance(data, dict):
            raise KlingAPIError("Kling response did not include an object data field", response=response)
        return data

    @staticmethod
    def _first_video(task_data: dict[str, Any]) -> dict[str, Any]:
        task_result = task_data.get("task_result")
        if not isinstance(task_result, dict):
            raise KlingAPIError("Kling task result was missing", response=task_data)

        videos = task_result.get("videos")
        if not isinstance(videos, list) or not videos or not isinstance(videos[0], dict):
            raise KlingAPIError("Kling task result did not include videos", response=task_data)

        return videos[0]

    @staticmethod
    def _decode_json(raw: bytes, *, status: int) -> dict[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KlingAPIError(f"Kling API returned invalid JSON (HTTP {status})", status=status) from exc

        if not isinstance(payload, dict):
            raise KlingAPIError("Kling API returned a non-object JSON payload", status=status, response=payload)
        return payload

    def _download(self, url: str, output_path: str | os.PathLike[str]) -> str:
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

    @staticmethod
    def _base64url_json(value: dict[str, Any]) -> str:
        raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return KlingV3ImageToVideo._base64url_bytes(raw)

    @staticmethod
    def _base64url_bytes(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
