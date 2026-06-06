"""Video task wrappers for Veo APIs."""

from __future__ import annotations

import dataclasses
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Iterable, Self

from google import genai
from google.genai import types

from .errors import VeoError, VeoTaskFailedError, VeoTimeoutError


__all__ = [
    "BaseVeoVideoGenerationTask",
    "VeoImageToVideo",
    "VeoTextToVideo",
    "VeoVideoExtension",
    "VeoVideoResult",
]


@dataclasses.dataclass
class VeoVideoResult:
    """Generated video result returned by Veo video wrappers."""

    operation_name: str
    status: str
    video_bytes: bytes
    path: str | None
    mime_type: str | None
    uri: str | None
    video: object
    raw: object


class BaseVeoVideoGenerationTask:
    """Base class for Veo video generation tasks."""

    model_name: str

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        model_name: str | None = None,
    ) -> None:
        self.model_name = self.require_model_name(model_name)
        if client is not None:
            self.client = client
            return

        if not api_key:
            raise VeoError("Gemini API key is required")

        self.client = genai.Client(api_key=api_key)

    @classmethod
    def from_env(cls, *, model_name: str | None = None) -> Self:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise VeoError("Missing required environment variable: GEMINI_API_KEY")
        return cls(api_key=api_key, model_name=model_name)

    def run_task(
        self,
        *,
        source: types.GenerateVideosSource,
        config: types.GenerateVideosConfig,
        output_path: str | os.PathLike[str] | None = None,
        poll_interval: float = 10,
        timeout: float = 600,
    ) -> VeoVideoResult:
        operation = self.client.models.generate_videos(
            model=self.model_name,
            source=source,
            config=config,
        )
        final_operation = self.wait_for_operation(operation, poll_interval=poll_interval, timeout=timeout)
        return self.video_result(final_operation, output_path=output_path)

    def wait_for_operation(self, operation: object, *, poll_interval: float, timeout: float) -> object:
        deadline = time.monotonic() + timeout
        current = operation

        while True:
            if self.operation_done(current):
                error = self.field(current, "error")
                if error:
                    raise VeoTaskFailedError(
                        self.operation_name(current),
                        self.error_message(error),
                        response=current,
                    )
                return current

            if time.monotonic() >= deadline:
                raise VeoTimeoutError(self.operation_name(current), timeout)

            time.sleep(poll_interval)
            current = self.client.operations.get(current)

    def video_result(
        self,
        operation: object,
        *,
        output_path: str | os.PathLike[str] | None = None,
    ) -> VeoVideoResult:
        video = self.first_video(operation)
        video_handle = self.require_generated_video_handle(video)
        video_bytes = self.download_video(video)

        saved_path = None
        if output_path is not None:
            saved_path = self.save_video(video_bytes, output_path)

        return VeoVideoResult(
            operation_name=self.operation_name(operation),
            status="succeeded",
            video_bytes=video_bytes,
            path=saved_path,
            mime_type=self.field(video_handle, "mime_type"),
            uri=self.field(video_handle, "uri"),
            video=video_handle,
            raw=operation,
        )

    def download_video(self, video: object) -> bytes:
        downloaded = self.client.files.download(file=video)
        if isinstance(downloaded, bytes | bytearray):
            return bytes(downloaded)

        video_bytes = self.field(video, "video_bytes")
        if isinstance(video_bytes, bytes | bytearray):
            return bytes(video_bytes)

        raise VeoError("Veo generated video download did not return bytes")

    @staticmethod
    def save_video(video_bytes: bytes, output_path: str | os.PathLike[str]) -> str:
        destination = Path(output_path).expanduser()
        try:
            if destination.parent != Path("."):
                destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(video_bytes)
        except OSError as exc:
            raise VeoError(f"Failed to save video to {destination}") from exc

        return str(destination)

    @classmethod
    def first_video(cls, operation: object) -> object:
        response = cls.operation_response(operation)
        generated_videos = cls.field(response, "generated_videos") if response is not None else None
        if not isinstance(generated_videos, list) or not generated_videos:
            raise VeoError(cls.missing_videos_message(response))

        video = cls.field(generated_videos[0], "video") or generated_videos[0]
        if video is None:
            raise VeoError("Veo operation succeeded but did not include a video")

        return video

    @classmethod
    def operation_response(cls, operation: object) -> object | None:
        return cls.field(operation, "response") or cls.field(operation, "result")

    @classmethod
    def missing_videos_message(cls, response: object | None) -> str:
        message = "Veo operation succeeded but did not include generated videos"
        if response is None:
            return message

        filtered_count = cls.field(response, "rai_media_filtered_count")
        filtered_reasons = cls.field(response, "rai_media_filtered_reasons")
        if filtered_count or filtered_reasons:
            details = []
            if filtered_count:
                details.append(f"filtered_count={filtered_count}")
            if filtered_reasons:
                details.append(f"filtered_reasons={filtered_reasons}")
            return f"{message} ({', '.join(details)})"

        return message

    @staticmethod
    def source(
        *,
        prompt: str | None = None,
        image: object | None = None,
        video: object | None = None,
    ) -> types.GenerateVideosSource:
        kwargs = {
            name: value
            for name, value in {
                "prompt": prompt or None,
                "image": image,
                "video": video,
            }.items()
            if value is not None
        }
        return types.GenerateVideosSource(**kwargs)

    @classmethod
    def config(
        cls,
        *,
        number_of_videos: int | None = 1,
        fps: int | None = None,
        duration_seconds: int | None = None,
        seed: int | None = None,
        aspect_ratio: str | None = None,
        resolution: str | None = None,
        person_generation: str | None = None,
        negative_prompt: str | None = None,
        enhance_prompt: bool | None = None,
        generate_audio: bool | None = None,
        last_frame: object | None = None,
        reference_images: list[types.VideoGenerationReferenceImage] | None = None,
    ) -> types.GenerateVideosConfig:
        kwargs = {
            name: value
            for name, value in {
                "number_of_videos": number_of_videos,
                "fps": fps,
                "duration_seconds": duration_seconds,
                "seed": seed,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "person_generation": person_generation,
                "negative_prompt": negative_prompt,
                "enhance_prompt": enhance_prompt,
                "generate_audio": generate_audio,
                "last_frame": last_frame,
                "reference_images": reference_images,
            }.items()
            if value is not None
        }
        return types.GenerateVideosConfig(**kwargs)

    @classmethod
    def normalize_image_input(cls, image: object) -> object:
        if isinstance(image, types.Image):
            return image
        if image is None:
            raise VeoError("Image is required")

        if isinstance(image, (str, os.PathLike)):
            value = os.fspath(image).strip()
            if value.startswith("gs://"):
                return types.Image(gcs_uri=value)

            path = Path(value).expanduser()
            if not path.is_file():
                raise VeoError("Image must be a local image path, gs:// URI, or SDK-compatible Image")

            mime_type = cls.guess_image_mime_type(path)
            return types.Image.from_file(location=str(path), mime_type=mime_type)

        return image

    @classmethod
    def normalize_video_input(cls, video: object) -> object:
        if isinstance(video, VeoVideoResult):
            return cls.require_generated_video_handle(video.video)

        if isinstance(video, types.GeneratedVideo):
            generated_video = cls.field(video, "video")
            if generated_video is None:
                raise VeoError("Veo video extension requires a previously generated Veo video handle")
            return cls.require_generated_video_handle(generated_video)

        if isinstance(video, types.Video):
            return cls.require_generated_video_handle(video)

        raise VeoError("Veo video extension requires a previously generated Veo video handle")

    @classmethod
    def require_generated_video_handle(cls, video: object) -> object:
        if not isinstance(video, types.Video):
            raise VeoError("Veo video extension requires a previously generated Veo video handle")

        uri = cls.field(video, "uri")
        if uri:
            return types.Video(uri=str(uri), mime_type=cls.field(video, "mime_type"))

        raise VeoError("Veo video extension requires a previously generated Veo video handle")

    @classmethod
    def normalize_reference_images(
        cls,
        reference_images: Iterable[object] | None,
        *,
        reference_type: str | types.VideoGenerationReferenceType,
    ) -> list[types.VideoGenerationReferenceImage] | None:
        if reference_images is None:
            return None

        refs = list(reference_images)
        if len(refs) > 3:
            raise VeoError("Veo reference image generation supports at most 3 reference images")

        return [cls.normalize_reference_image(ref, reference_type=reference_type) for ref in refs]

    @classmethod
    def normalize_reference_image(
        cls,
        reference_image: object,
        *,
        reference_type: str | types.VideoGenerationReferenceType,
    ) -> types.VideoGenerationReferenceImage:
        if isinstance(reference_image, types.VideoGenerationReferenceImage):
            return reference_image

        image = reference_image
        image_reference_type = reference_type
        if isinstance(reference_image, tuple) and len(reference_image) == 2:
            image, image_reference_type = reference_image

        return types.VideoGenerationReferenceImage(
            image=cls.normalize_image_input(image),
            reference_type=cls.normalize_reference_type(image_reference_type),
        )

    @staticmethod
    def normalize_reference_type(
        reference_type: str | types.VideoGenerationReferenceType,
    ) -> types.VideoGenerationReferenceType:
        if isinstance(reference_type, types.VideoGenerationReferenceType):
            return reference_type

        value = str(reference_type).strip().upper()
        try:
            return types.VideoGenerationReferenceType(value)
        except ValueError as exc:
            raise VeoError(f"Unsupported Veo reference_type: {reference_type}") from exc

    @staticmethod
    def operation_done(operation: object) -> bool:
        done = BaseVeoVideoGenerationTask.field(operation, "done")
        if done is None:
            return BaseVeoVideoGenerationTask.field(operation, "response") is not None
        return bool(done)

    @staticmethod
    def operation_name(operation: object) -> str:
        return str(BaseVeoVideoGenerationTask.field(operation, "name") or "")

    @staticmethod
    def error_message(error: object) -> str:
        message = BaseVeoVideoGenerationTask.field(error, "message")
        if message:
            return str(message)
        return str(error) if error else ""

    @staticmethod
    def guess_image_mime_type(path: Path) -> str:
        mime_type = mimetypes.guess_type(path.name)[0]
        if not mime_type or not mime_type.startswith("image/"):
            raise VeoError(f"Unsupported image file type: {path}")
        return mime_type

    @staticmethod
    def guess_video_mime_type(path: Path) -> str:
        mime_type = mimetypes.guess_type(path.name)[0]
        if not mime_type or not mime_type.startswith("video/"):
            raise VeoError(f"Unsupported video file type: {path}")
        return mime_type

    @staticmethod
    def field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            if name in value:
                return value.get(name)
            alias = BaseVeoVideoGenerationTask.camel_case(name)
            return value.get(alias)
        return getattr(value, name, None)

    @staticmethod
    def camel_case(name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(part.capitalize() for part in parts[1:])

    @staticmethod
    def require_prompt(prompt: str) -> None:
        if not prompt:
            raise VeoError("Prompt is required")

    @staticmethod
    def require_model_name(model_name: str | None) -> str:
        if not isinstance(model_name, str) or not model_name.strip():
            raise VeoError("model_name is required")
        return model_name.strip()


class VeoTextToVideo(BaseVeoVideoGenerationTask):
    """Veo text-to-video wrapper with a local-model-style API."""

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        reference_images: Iterable[object] | None = None,
        reference_type: str | types.VideoGenerationReferenceType = "asset",
        aspect_ratio: str | None = None,
        resolution: str | None = None,
        duration_seconds: int | None = None,
        negative_prompt: str | None = None,
        person_generation: str | None = None,
        number_of_videos: int | None = 1,
        enhance_prompt: bool | None = None,
        generate_audio: bool | None = None,
        seed: int | None = None,
        fps: int | None = None,
        poll_interval: float = 10,
        timeout: float = 600,
    ) -> VeoVideoResult:
        """Generate a video from text and wait for the finished result."""

        self.require_prompt(prompt)
        refs = self.normalize_reference_images(reference_images, reference_type=reference_type)
        return self.run_task(
            source=self.source(prompt=prompt),
            config=self.config(
                number_of_videos=number_of_videos,
                fps=fps,
                duration_seconds=duration_seconds,
                seed=seed,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                person_generation=person_generation,
                negative_prompt=negative_prompt,
                enhance_prompt=enhance_prompt,
                generate_audio=generate_audio,
                reference_images=refs,
            ),
            output_path=output_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )


class VeoImageToVideo(BaseVeoVideoGenerationTask):
    """Veo image-to-video wrapper with a local-model-style API."""

    def generate(
        self,
        image: object,
        prompt: str = "",
        output_path: str | os.PathLike[str] | None = None,
        *,
        last_frame: object | None = None,
        aspect_ratio: str | None = None,
        resolution: str | None = None,
        duration_seconds: int | None = None,
        negative_prompt: str | None = None,
        person_generation: str | None = None,
        number_of_videos: int | None = 1,
        enhance_prompt: bool | None = None,
        generate_audio: bool | None = None,
        seed: int | None = None,
        fps: int | None = None,
        poll_interval: float = 10,
        timeout: float = 600,
    ) -> VeoVideoResult:
        """Generate a video from an image, with optional first/last-frame interpolation."""

        first_frame = self.normalize_image_input(image)
        normalized_last_frame = self.normalize_image_input(last_frame) if last_frame is not None else None
        return self.run_task(
            source=self.source(prompt=prompt, image=first_frame),
            config=self.config(
                number_of_videos=number_of_videos,
                fps=fps,
                duration_seconds=duration_seconds,
                seed=seed,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                person_generation=person_generation,
                negative_prompt=negative_prompt,
                enhance_prompt=enhance_prompt,
                generate_audio=generate_audio,
                last_frame=normalized_last_frame,
            ),
            output_path=output_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )


class VeoVideoExtension(BaseVeoVideoGenerationTask):
    """Veo video extension wrapper with a local-model-style API."""

    def generate(
        self,
        video: object,
        prompt: str = "",
        output_path: str | os.PathLike[str] | None = None,
        *,
        resolution: str | None = "720p",
        duration_seconds: int | None = None,
        number_of_videos: int | None = 1,
        negative_prompt: str | None = None,
        person_generation: str | None = None,
        enhance_prompt: bool | None = None,
        generate_audio: bool | None = None,
        seed: int | None = None,
        poll_interval: float = 10,
        timeout: float = 600,
    ) -> VeoVideoResult:
        """Extend an existing video and wait for the finished result."""

        normalized_video = self.normalize_video_input(video)
        return self.run_task(
            source=self.source(prompt=prompt, video=normalized_video),
            config=self.config(
                number_of_videos=number_of_videos,
                duration_seconds=duration_seconds,
                seed=seed,
                resolution=resolution,
                person_generation=person_generation,
                negative_prompt=negative_prompt,
                enhance_prompt=enhance_prompt,
                generate_audio=generate_audio,
            ),
            output_path=output_path,
            poll_interval=poll_interval,
            timeout=timeout,
        )
