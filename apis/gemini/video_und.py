"""Video understanding wrappers for Gemini APIs."""

from __future__ import annotations

import dataclasses
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Self

from google import genai
from google.genai import types

from .errors import GeminiError


__all__ = [
    "BaseGeminiVideoUnderstandingTask",
    "GeminiVideoUnderstanding",
    "GeminiVideoUnderstandingResult",
]


@dataclasses.dataclass
class GeminiVideoUnderstandingResult:
    """Text result returned by Gemini video understanding wrappers."""

    text: str
    raw: object
    uploaded_file: object | None = None


class BaseGeminiVideoUnderstandingTask:
    """Base class for Gemini video understanding tasks."""

    model_name: str
    default_inline_max_bytes = 20 * 1024 * 1024

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
            raise GeminiError("Gemini API key is required")

        self.client = genai.Client(api_key=api_key)

    @classmethod
    def from_env(cls, *, model_name: str | None = None) -> Self:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise GeminiError("Missing required environment variable: GEMINI_API_KEY")
        return cls(api_key=api_key, model_name=model_name)

    def generate_content(
        self,
        video: object,
        prompt: str,
        *,
        upload: bool | None = None,
        max_inline_bytes: int | None = None,
        mime_type: str | None = None,
        start_offset: str | None = None,
        end_offset: str | None = None,
        fps: float | None = None,
        media_resolution: str | types.MediaResolution | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        upload_poll_interval: float = 2,
        upload_timeout: float = 300,
    ) -> GeminiVideoUnderstandingResult:
        """Generate a text response for a video and prompt."""

        self.require_prompt(prompt)
        video_part, uploaded_file = self.video_part(
            video,
            upload=upload,
            max_inline_bytes=max_inline_bytes,
            mime_type=mime_type,
            start_offset=start_offset,
            end_offset=end_offset,
            fps=fps,
            upload_poll_interval=upload_poll_interval,
            upload_timeout=upload_timeout,
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=self.contents(video_part, prompt),
            config=self.content_config(
                media_resolution=media_resolution,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return GeminiVideoUnderstandingResult(
            text=self.response_text(response),
            raw=response,
            uploaded_file=uploaded_file,
        )

    def video_part(
        self,
        video: object,
        *,
        upload: bool | None,
        max_inline_bytes: int | None,
        mime_type: str | None,
        start_offset: str | None,
        end_offset: str | None,
        fps: float | None,
        upload_poll_interval: float,
        upload_timeout: float,
    ) -> tuple[types.Part, object | None]:
        metadata = self.video_metadata(start_offset=start_offset, end_offset=end_offset, fps=fps)

        if isinstance(video, types.Part):
            return video, None

        file_uri = self.field(video, "uri") or self.field(video, "file_uri")
        if file_uri:
            return self.uri_part(str(file_uri), mime_type or self.field(video, "mime_type"), metadata=metadata), None

        if isinstance(video, bytes | bytearray):
            return self.inline_part(bytes(video), self.require_mime_type(mime_type), metadata=metadata), None

        if isinstance(video, (str, os.PathLike)):
            value = os.fspath(video)
            path = Path(value).expanduser()
            if path.is_file():
                resolved_mime_type = mime_type or self.guess_video_mime_type(path)
                if self.should_upload(path, upload=upload, max_inline_bytes=max_inline_bytes):
                    uploaded_file = self.upload_video(
                        path,
                        mime_type=resolved_mime_type,
                        poll_interval=upload_poll_interval,
                        timeout=upload_timeout,
                    )
                    file_uri = self.field(uploaded_file, "uri")
                    if not file_uri:
                        raise GeminiError("Gemini uploaded file response did not include uri")
                    file_mime_type = self.field(uploaded_file, "mime_type") or resolved_mime_type
                    return self.uri_part(str(file_uri), file_mime_type, metadata=metadata), uploaded_file
                return self.inline_part(path.read_bytes(), resolved_mime_type, metadata=metadata), None

            stripped = value.strip()
            if self.is_uri(stripped):
                return self.uri_part(stripped, mime_type or self.guess_uri_mime_type(stripped), metadata=metadata), None

        raise GeminiError("Video must be a local path, URL, bytes, Gemini File, or Gemini Part")

    def upload_video(
        self,
        path: Path,
        *,
        mime_type: str,
        poll_interval: float,
        timeout: float,
    ) -> object:
        config = types.UploadFileConfig(mime_type=mime_type, display_name=path.name)
        uploaded_file = self.client.files.upload(file=path, config=config)
        return self.wait_for_file(uploaded_file, poll_interval=poll_interval, timeout=timeout)

    def wait_for_file(self, file: object, *, poll_interval: float, timeout: float) -> object:
        deadline = time.monotonic() + timeout
        current = file

        while True:
            state = self.file_state_name(self.field(current, "state"))
            if state in {"", "ACTIVE"}:
                return current
            if state == "FAILED":
                raise GeminiError("Gemini uploaded video processing failed")
            if time.monotonic() >= deadline:
                raise GeminiError(f"Timed out waiting {timeout} seconds for Gemini video processing")

            name = self.field(current, "name")
            if not name:
                raise GeminiError("Gemini uploaded file response did not include name")

            time.sleep(poll_interval)
            current = self.client.files.get(name=str(name))

    @staticmethod
    def contents(video_part: types.Part, prompt: str) -> list[types.Content]:
        return [
            types.Content(
                role="user",
                parts=[
                    video_part,
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

    @classmethod
    def inline_part(
        cls,
        video_bytes: bytes,
        mime_type: str,
        *,
        metadata: types.VideoMetadata | None,
    ) -> types.Part:
        return types.Part(
            inline_data=types.Blob(data=video_bytes, mime_type=mime_type),
            video_metadata=metadata,
        )

    @classmethod
    def uri_part(
        cls,
        file_uri: str,
        mime_type: str | None,
        *,
        metadata: types.VideoMetadata | None,
    ) -> types.Part:
        return types.Part(
            file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
            video_metadata=metadata,
        )

    @staticmethod
    def video_metadata(
        *,
        start_offset: str | None = None,
        end_offset: str | None = None,
        fps: float | None = None,
    ) -> types.VideoMetadata | None:
        kwargs = {
            name: value
            for name, value in {
                "start_offset": start_offset,
                "end_offset": end_offset,
                "fps": fps,
            }.items()
            if value is not None
        }
        if not kwargs:
            return None
        return types.VideoMetadata(**kwargs)

    @classmethod
    def content_config(
        cls,
        *,
        media_resolution: str | types.MediaResolution | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> types.GenerateContentConfig:
        config = {
            name: value
            for name, value in {
                "media_resolution": cls.normalize_media_resolution(media_resolution),
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            }.items()
            if value is not None
        }
        return types.GenerateContentConfig(**config)

    @staticmethod
    def normalize_media_resolution(
        media_resolution: str | types.MediaResolution | None,
    ) -> types.MediaResolution | None:
        if media_resolution is None or isinstance(media_resolution, types.MediaResolution):
            return media_resolution

        value = media_resolution.strip().upper()
        if not value.startswith("MEDIA_RESOLUTION_"):
            value = f"MEDIA_RESOLUTION_{value}"

        try:
            return types.MediaResolution(value)
        except ValueError as exc:
            raise GeminiError(f"Unsupported media_resolution: {media_resolution}") from exc

    @classmethod
    def response_text(cls, response: object) -> str:
        text = cls.field(response, "text")
        if text:
            return str(text)

        text_parts = [
            str(part_text)
            for part in cls.response_parts(response)
            if (part_text := cls.field(part, "text"))
        ]
        if text_parts:
            return "\n".join(text_parts)

        raise GeminiError("Gemini video understanding response did not include text")

    @classmethod
    def response_parts(cls, response: object) -> list[object]:
        direct_parts = cls.field(response, "parts")
        if isinstance(direct_parts, list):
            return direct_parts

        candidates = cls.field(response, "candidates")
        if isinstance(candidates, list):
            parts: list[object] = []
            for candidate in candidates:
                content = cls.field(candidate, "content")
                candidate_parts = cls.field(content, "parts")
                if isinstance(candidate_parts, list):
                    parts.extend(candidate_parts)
            if parts:
                return parts

        return []

    @classmethod
    def should_upload(
        cls,
        path: Path,
        *,
        upload: bool | None,
        max_inline_bytes: int | None,
    ) -> bool:
        if upload is not None:
            return upload
        return path.stat().st_size > (max_inline_bytes or cls.default_inline_max_bytes)

    @staticmethod
    def guess_video_mime_type(path: Path) -> str:
        mime_type = mimetypes.guess_type(path.name)[0]
        if not mime_type or not mime_type.startswith("video/"):
            raise GeminiError(f"Unsupported video file type: {path}")
        return mime_type

    @staticmethod
    def guess_uri_mime_type(uri: str) -> str | None:
        if "youtube.com/" in uri or "youtu.be/" in uri:
            return None
        mime_type = mimetypes.guess_type(uri)[0]
        if mime_type and mime_type.startswith("video/"):
            return mime_type
        return None

    @staticmethod
    def require_mime_type(mime_type: str | None) -> str:
        if not mime_type:
            raise GeminiError("mime_type is required when video is bytes")
        if not mime_type.startswith("video/"):
            raise GeminiError(f"Unsupported video MIME type: {mime_type}")
        return mime_type

    @staticmethod
    def is_uri(value: str) -> bool:
        return value.startswith(("http://", "https://", "gs://"))

    @staticmethod
    def file_state_name(state: object) -> str:
        if state is None:
            return ""
        name = getattr(state, "name", None)
        if name:
            return str(name)
        return str(state).rsplit(".", 1)[-1]

    @staticmethod
    def field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def require_prompt(prompt: str) -> None:
        if not prompt:
            raise GeminiError("Prompt is required")

    @staticmethod
    def require_model_name(model_name: str | None) -> str:
        if not isinstance(model_name, str) or not model_name.strip():
            raise GeminiError("model_name is required")
        return model_name.strip()


class GeminiVideoUnderstanding(BaseGeminiVideoUnderstandingTask):
    """Gemini video understanding wrapper with a local-model-style API."""

    def generate(
        self,
        video: object,
        prompt: str,
        *,
        upload: bool | None = None,
        max_inline_bytes: int | None = None,
        mime_type: str | None = None,
        start_offset: str | None = None,
        end_offset: str | None = None,
        fps: float | None = None,
        media_resolution: str | types.MediaResolution | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        upload_poll_interval: float = 2,
        upload_timeout: float = 300,
    ) -> GeminiVideoUnderstandingResult:
        """Generate a text answer from a video and prompt."""

        return self.generate_content(
            video,
            prompt,
            upload=upload,
            max_inline_bytes=max_inline_bytes,
            mime_type=mime_type,
            start_offset=start_offset,
            end_offset=end_offset,
            fps=fps,
            media_resolution=media_resolution,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            upload_poll_interval=upload_poll_interval,
            upload_timeout=upload_timeout,
        )
