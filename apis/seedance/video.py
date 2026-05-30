"""Video task wrappers for Seedance APIs."""

from __future__ import annotations

import base64
import dataclasses
import mimetypes
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Self

from volcenginesdkarkruntime import Ark

from .errors import SeedanceError, SeedanceTaskFailedError, SeedanceTimeoutError


@dataclasses.dataclass
class SeedanceVideoResult:
    """Generated video result returned by Seedance video wrappers."""

    task_id: str
    status: str
    url: str
    path: str | None
    duration: int | None
    ratio: str | None
    resolution: str | None
    last_frame_url: str | None
    raw: object


def normalize_image(image: str | os.PathLike[str]) -> str:
    """Return a Seedance-compatible image URL, asset ID, data URI, or local-file data URI."""

    value = os.fspath(image)
    stripped = value.strip()

    if stripped.startswith(("http://", "https://", "data:", "asset://")):
        return stripped

    path = Path(value).expanduser()
    if not path.is_file():
        raise SeedanceError("Image must be a public URL, asset:// ID, data URI, or local image path")

    mime_type = mimetypes.guess_type(path.name)[0]
    if mime_type is None or not mime_type.startswith("image/"):
        raise SeedanceError(f"Unsupported image file type: {path}")

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def normalize_video(video: str | os.PathLike[str]) -> str:
    """Return a Seedance-compatible video URL or asset ID."""

    value = os.fspath(video).strip()
    if value.startswith(("http://", "https://", "asset://")):
        return value
    raise SeedanceError("Video must be a public URL or asset:// ID")


class BaseSeedanceVideoTask:
    """Base class for Seedance video generation tasks."""

    model_name: str

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        base_url: str | None = None,
        request_timeout: float | None = None,
    ) -> None:
        if not getattr(self, "model_name", ""):
            raise ValueError("Seedance video task model_name is required")

        self.request_timeout = request_timeout or 60
        if client is not None:
            self.client = client
            return

        if not api_key:
            raise SeedanceError("Ark API key is required")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url is not None:
            kwargs["base_url"] = base_url
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout
        self.client = Ark(**kwargs)

    @classmethod
    def from_env(cls) -> Self:
        api_key = os.environ.get("ARK_API_KEY", "")
        base_url = os.environ.get("ARK_BASE_URL")
        if not api_key:
            raise SeedanceError("Missing required environment variable: ARK_API_KEY")
        return cls(api_key=api_key, base_url=base_url)

    def create_task(self, payload: dict[str, Any]) -> object:
        return self.client.content_generation.tasks.create(**payload)

    def get_task(self, task_id: str) -> object:
        return self.client.content_generation.tasks.get(task_id=task_id)

    def wait_for_task(self, task_id: str, *, poll_interval: float, timeout: float) -> object:
        deadline = time.monotonic() + timeout

        while True:
            response = self.get_task(task_id)
            status = self.field(response, "status")

            if status == "succeeded":
                return response
            if status in {"failed", "expired", "cancelled"}:
                error = self.field(response, "error")
                message = self.field(error, "message") or ""
                raise SeedanceTaskFailedError(task_id, str(status), message, response=response)
            if time.monotonic() >= deadline:
                raise SeedanceTimeoutError(task_id, timeout)

            time.sleep(poll_interval)

    def run_task(
        self,
        payload: dict[str, Any],
        *,
        output_path: str | os.PathLike[str] | None = None,
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> SeedanceVideoResult:
        create_response = self.create_task(payload)
        task_id = self.field(create_response, "id")
        if not task_id:
            raise SeedanceError("Seedance create task response did not include id")

        final_response = self.wait_for_task(str(task_id), poll_interval=poll_interval, timeout=timeout)
        return self.video_result(str(task_id), final_response, output_path=output_path)

    def video_result(
        self,
        task_id: str,
        response: object,
        *,
        output_path: str | os.PathLike[str] | None = None,
    ) -> SeedanceVideoResult:
        content = self.field(response, "content")
        url = self.field(content, "video_url") or ""
        if not url:
            raise SeedanceError("Seedance task succeeded but did not include content.video_url")

        saved_path = None
        if output_path is not None:
            saved_path = self.download(url, output_path)

        return SeedanceVideoResult(
            task_id=task_id,
            status=self.field(response, "status") or "",
            url=url,
            path=saved_path,
            duration=self.field(response, "duration"),
            ratio=self.field(response, "ratio"),
            resolution=self.field(response, "resolution"),
            last_frame_url=self.field(content, "last_frame_url"),
            raw=response,
        )

    def download(self, url: str, output_path: str | os.PathLike[str]) -> str:
        destination = Path(output_path).expanduser()
        if destination.parent != Path("."):
            destination.parent.mkdir(parents=True, exist_ok=True)

        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                destination.write_bytes(response.read())
        except urllib.error.URLError as exc:
            raise SeedanceError(f"Failed to download Seedance video: {exc.reason}") from exc

        return str(destination)

    def task_payload(
        self,
        content: list[dict[str, Any]],
        *,
        callback_url: str | None = None,
        return_last_frame: bool | None = None,
        execution_expires_after: int | None = None,
        priority: int | None = None,
        generate_audio: bool | None = None,
        watermark: bool | None = None,
        seed: int | None = None,
        resolution: str | None = None,
        ratio: str | None = None,
        duration: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        safety_identifier: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "content": content,
        }
        optional = {
            "callback_url": callback_url,
            "return_last_frame": return_last_frame,
            "execution_expires_after": execution_expires_after,
            "priority": priority,
            "generate_audio": generate_audio,
            "watermark": watermark,
            "seed": seed,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "tools": tools,
            "safety_identifier": safety_identifier,
        }
        payload.update({name: value for name, value in optional.items() if value is not None})
        return payload

    @staticmethod
    def field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def require_prompt(prompt: str) -> None:
        if not prompt:
            raise SeedanceError("Prompt is required")


class Seedance20TextToVideo(BaseSeedanceVideoTask):
    """Seedance 2.0 text-to-video wrapper with a local-model-style API."""

    model_name = "doubao-seedance-2-0-260128"

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        duration: int | None = 5,
        ratio: str | None = "adaptive",
        resolution: str | None = None,
        seed: int | None = None,
        generate_audio: bool | None = False,
        watermark: bool | None = False,
        return_last_frame: bool | None = None,
        callback_url: str | None = None,
        execution_expires_after: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        safety_identifier: str | None = None,
        priority: int | None = None,
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> SeedanceVideoResult:
        """Generate a video from text and wait for the finished result."""

        self.require_prompt(prompt)
        payload = self.task_payload(
            [{"type": "text", "text": prompt}],
            duration=duration,
            ratio=ratio,
            resolution=resolution,
            seed=seed,
            generate_audio=generate_audio,
            watermark=watermark,
            return_last_frame=return_last_frame,
            callback_url=callback_url,
            execution_expires_after=execution_expires_after,
            tools=tools,
            safety_identifier=safety_identifier,
            priority=priority,
        )
        return self.run_task(payload, output_path=output_path, poll_interval=poll_interval, timeout=timeout)


class Seedance20ImageToVideo(BaseSeedanceVideoTask):
    """Seedance 2.0 image-to-video wrapper with a local-model-style API."""

    model_name = "doubao-seedance-2-0-260128"

    def generate(
        self,
        image: str | os.PathLike[str],
        prompt: str = "",
        output_path: str | os.PathLike[str] | None = None,
        *,
        last_image: str | os.PathLike[str] | None = None,
        duration: int | None = 5,
        ratio: str | None = "adaptive",
        resolution: str | None = None,
        seed: int | None = None,
        generate_audio: bool | None = False,
        watermark: bool | None = False,
        return_last_frame: bool | None = None,
        callback_url: str | None = None,
        execution_expires_after: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        safety_identifier: str | None = None,
        priority: int | None = None,
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> SeedanceVideoResult:
        """Generate a video from one image, or from first and last frame images."""

        content: list[dict[str, Any]] = []
        if prompt:
            content.append({"type": "text", "text": prompt})

        first_frame = {"type": "image_url", "image_url": {"url": normalize_image(image)}}
        if last_image is None:
            content.append(first_frame)
        else:
            first_frame["role"] = "first_frame"
            content.append(first_frame)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": normalize_image(last_image)},
                    "role": "last_frame",
                }
            )

        payload = self.task_payload(
            content,
            duration=duration,
            ratio=ratio,
            resolution=resolution,
            seed=seed,
            generate_audio=generate_audio,
            watermark=watermark,
            return_last_frame=return_last_frame,
            callback_url=callback_url,
            execution_expires_after=execution_expires_after,
            tools=tools,
            safety_identifier=safety_identifier,
            priority=priority,
        )
        return self.run_task(payload, output_path=output_path, poll_interval=poll_interval, timeout=timeout)


class Seedance20VideoExtension(BaseSeedanceVideoTask):
    """Seedance 2.0 video extension wrapper with a local-model-style API."""

    model_name = "doubao-seedance-2-0-260128"

    def generate(
        self,
        video: str | os.PathLike[str] | list[str | os.PathLike[str]] | tuple[str | os.PathLike[str], ...],
        prompt: str = "",
        output_path: str | os.PathLike[str] | None = None,
        *,
        duration: int | None = 5,
        ratio: str | None = "adaptive",
        resolution: str | None = None,
        seed: int | None = None,
        generate_audio: bool | None = False,
        watermark: bool | None = False,
        return_last_frame: bool | None = None,
        callback_url: str | None = None,
        execution_expires_after: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        safety_identifier: str | None = None,
        priority: int | None = None,
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> SeedanceVideoResult:
        """Extend one video, or stitch up to three reference videos into a continuous video."""

        videos = list(video) if isinstance(video, (list, tuple)) else [video]
        if not 1 <= len(videos) <= 3:
            raise SeedanceError("Seedance video extension requires one to three videos")

        content: list[dict[str, Any]] = []
        if prompt:
            content.append({"type": "text", "text": prompt})

        for item in videos:
            content.append(
                {
                    "type": "video_url",
                    "video_url": {"url": normalize_video(item)},
                    "role": "reference_video",
                }
            )

        payload = self.task_payload(
            content,
            duration=duration,
            ratio=ratio,
            resolution=resolution,
            seed=seed,
            generate_audio=generate_audio,
            watermark=watermark,
            return_last_frame=return_last_frame,
            callback_url=callback_url,
            execution_expires_after=execution_expires_after,
            tools=tools,
            safety_identifier=safety_identifier,
            priority=priority,
        )
        return self.run_task(payload, output_path=output_path, poll_interval=poll_interval, timeout=timeout)
