"""Shared video task wrappers for Kling APIs."""

from __future__ import annotations

import dataclasses
import os
import time
import urllib.parse
from typing import Any, Self

from .client import KlingClient
from .errors import KlingAPIError, KlingTaskFailed, KlingTimeout
from .media import normalize_image


@dataclasses.dataclass
class VideoResult:
    """Generated video result returned by Kling video wrappers."""

    task_id: str
    status: str
    url: str
    path: str | None
    duration: str | None
    raw: dict[str, Any]


class BaseKlingVideoTask:
    """Shared lifecycle for Kling async video generation tasks."""

    endpoint: str

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        *,
        client: KlingClient | None = None,
        base_url: str | None = None,
        request_timeout: float = 60,
    ) -> None:
        if not getattr(self, "endpoint", ""):
            raise ValueError("Kling video task endpoint is required")

        if client is not None:
            self.client = client
            return

        kwargs: dict[str, Any] = {"request_timeout": request_timeout}
        if base_url is not None:
            kwargs["base_url"] = base_url
        self.client = KlingClient(access_key or "", secret_key or "", **kwargs)

    @classmethod
    def from_env(cls) -> Self:
        return cls(client=KlingClient.from_env())

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.client.post(self.endpoint, payload)

    def get_task(self, task_id: str) -> dict[str, Any]:
        quoted_id = urllib.parse.quote(task_id, safe="")
        return self.client.get(f"{self.endpoint}/{quoted_id}")

    def wait_for_task(self, task_id: str, *, poll_interval: float, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while True:
            response = self.get_task(task_id)
            data = self.response_data(response)
            status = data.get("task_status")

            if status == "succeed":
                return data
            if status == "failed":
                message = data.get("task_status_msg") or "Kling task failed"
                raise KlingTaskFailed(task_id, message, response=data)
            if time.monotonic() >= deadline:
                raise KlingTimeout(task_id, timeout)

            time.sleep(poll_interval)

    def run_task(
        self,
        payload: dict[str, Any],
        *,
        output_path: str | os.PathLike[str] | None = None,
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> VideoResult:
        create_response = self.create_task(payload)
        task_data = self.response_data(create_response)
        task_id = task_data.get("task_id")
        if not task_id:
            raise KlingAPIError("Kling create task response did not include task_id", response=create_response)

        final_data = self.wait_for_task(task_id, poll_interval=poll_interval, timeout=timeout)
        video = self.first_video(final_data)
        url = video.get("url", "")
        if not url:
            raise KlingAPIError("Kling task succeeded but did not include a video URL", response=final_data)

        saved_path = None
        if output_path is not None:
            saved_path = self.client.download(url, output_path)

        return VideoResult(
            task_id=task_id,
            status=final_data.get("task_status", ""),
            url=url,
            path=saved_path,
            duration=video.get("duration"),
            raw=final_data,
        )

    @staticmethod
    def response_data(response: dict[str, Any]) -> dict[str, Any]:
        data = response.get("data")
        if not isinstance(data, dict):
            raise KlingAPIError("Kling response did not include an object data field", response=response)
        return data

    @staticmethod
    def first_video(task_data: dict[str, Any]) -> dict[str, Any]:
        task_result = task_data.get("task_result")
        if not isinstance(task_result, dict):
            raise KlingAPIError("Kling task result was missing", response=task_data)

        videos = task_result.get("videos")
        if not isinstance(videos, list) or not videos or not isinstance(videos[0], dict):
            raise KlingAPIError("Kling task result did not include videos", response=task_data)

        return videos[0]


class KlingV3ImageToVideo(BaseKlingVideoTask):
    """Kling V3 image-to-video wrapper with a local-model-style API."""

    endpoint = "/v1/videos/image2video"
    model_name = "kling-v3"

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

        payload = {
            "model_name": self.model_name,
            "image": normalize_image(image),
            "prompt": prompt or "",
            "duration": str(duration),
            "mode": mode,
        }
        return self.run_task(
            payload,
            output_path=output_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )


class KlingV3TextToVideo(BaseKlingVideoTask):
    """Kling V3 text-to-video wrapper with a local-model-style API."""

    endpoint = "/v1/videos/text2video"
    model_name = "kling-v3"

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        duration: int | str = 5,
        mode: str = "std",
        aspect_ratio: str = "16:9",
        negative_prompt: str = "",
        sound: str = "off",
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> VideoResult:
        """Generate a video from text and wait for the finished result."""

        payload = {
            "model_name": self.model_name,
            "prompt": prompt,
            "duration": str(duration),
            "mode": mode,
            "aspect_ratio": aspect_ratio,
            "sound": sound,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        return self.run_task(
            payload,
            output_path=output_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )


class KlingVideoExtension(BaseKlingVideoTask):
    """Kling video extension wrapper with a local-model-style API."""

    endpoint = "/v1/videos/video-extend"

    def generate(
        self,
        video_id: str,
        prompt: str = "",
        output_path: str | os.PathLike[str] | None = None,
        negative_prompt: str = "",
        cfg_scale: float | None = None,
        poll_interval: float = 5,
        timeout: float = 600,
    ) -> VideoResult:
        """Extend an existing Kling-generated video and wait for the finished result."""

        payload: dict[str, Any] = {
            "video_id": video_id,
            "prompt": prompt,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if cfg_scale is not None:
            payload["cfg_scale"] = cfg_scale

        return self.run_task(
            payload,
            output_path=output_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )
