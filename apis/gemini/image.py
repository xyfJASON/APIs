"""Image task wrappers for Gemini Image APIs."""

from __future__ import annotations

import base64
import binascii
import dataclasses
import io
import os
from pathlib import Path
from typing import Any, Iterable, Self
from PIL import Image, UnidentifiedImageError

from google import genai
from google.genai import types

from .errors import GeminiError


__all__ = [
    "GeminiImageResult",
    "NanoBananaTextToImage",
    "NanoBananaImageEditing",
    "NanoBananaProTextToImage",
    "NanoBananaProImageEditing",
    "NanoBanana2TextToImage",
    "NanoBanana2ImageEditing",
]


@dataclasses.dataclass
class GeminiImageResult:
    """Generated image result returned by Gemini image wrappers."""

    b64_json: str
    path: str | None
    mime_type: str | None
    text: str | None
    raw: object


class BaseGeminiImageTask:
    """Base class for Gemini image generation tasks."""

    model_name = "gemini-3.1-flash-image"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        model_name: str | None = None,
    ) -> None:
        self.model_name = model_name or self.model_name
        if client is not None:
            self.client = client
            return

        if not api_key:
            raise GeminiError("Gemini API key is required")

        self.client = genai.Client(api_key=api_key)

    @classmethod
    def from_env(cls) -> Self:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise GeminiError("Missing required environment variable: GEMINI_API_KEY")
        return cls(api_key=api_key)

    @staticmethod
    def content_config(
        *,
        response_modalities: Iterable[str],
        aspect_ratio: str | None = None,
        image_size: str | None = None,
    ) -> types.GenerateContentConfig:
        config: dict[str, Any] = {
            "response_modalities": list(response_modalities),
        }

        image_config_kwargs = {
            name: value
            for name, value in {
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
            }.items()
            if value is not None
        }
        if image_config_kwargs:
            config["image_config"] = types.ImageConfig(**image_config_kwargs)

        return types.GenerateContentConfig(**config)

    def image_result(
        self,
        response: object,
        output_path: str | os.PathLike[str] | None = None,
    ) -> GeminiImageResult:
        text_parts: list[str] = []
        first_image: tuple[bytes, str, str | None, object] | None = None

        for part in self.response_parts(response):
            text = self.field(part, "text")
            if text:
                text_parts.append(str(text))

            if first_image is None:
                image = self.image_from_part(part)
                if image is not None:
                    image_bytes, b64_json, mime_type = image
                    first_image = (image_bytes, b64_json, mime_type, part)

        if first_image is not None:
            image_bytes, b64_json, mime_type, part = first_image
            saved_path = None
            if output_path is not None:
                saved_path = self.save_image(image_bytes, output_path, part=part)

            return GeminiImageResult(
                b64_json=b64_json,
                path=saved_path,
                mime_type=mime_type,
                text="\n".join(text_parts) or None,
                raw=response,
            )

        raise GeminiError("Gemini image response did not include image data")

    @classmethod
    def image_from_part(cls, part: object) -> tuple[bytes, str, str | None] | None:
        inline_data = cls.field(part, "inline_data") or cls.field(part, "inlineData")
        data = cls.field(inline_data, "data") if inline_data is not None else None
        mime_type = (
            cls.field(inline_data, "mime_type")
            or cls.field(inline_data, "mimeType")
            if inline_data is not None
            else None
        )

        if data is not None:
            image_bytes, b64_json = cls.decode_inline_data(data)
            return image_bytes, b64_json, mime_type

        as_image = getattr(part, "as_image", None)
        if not callable(as_image):
            return None

        try:
            image = as_image()
        except Exception:
            return None
        if image is None:
            return None

        image_bytes = cls.pillow_image_bytes(image)
        return image_bytes, base64.b64encode(image_bytes).decode("ascii"), "image/png"

    @staticmethod
    def decode_inline_data(data: object) -> tuple[bytes, str]:
        if isinstance(data, bytes | bytearray):
            image_bytes = bytes(data)
            return image_bytes, base64.b64encode(image_bytes).decode("ascii")

        if isinstance(data, str):
            try:
                image_bytes = base64.b64decode(data, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise GeminiError("Gemini image response included invalid base64 data") from exc
            return image_bytes, data

        raise GeminiError("Gemini image response included unsupported image data")

    @staticmethod
    def pillow_image_bytes(image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def save_image(
        image_bytes: bytes,
        output_path: str | os.PathLike[str],
        *,
        part: object | None = None,
    ) -> str:
        destination = Path(output_path).expanduser()
        try:
            if destination.parent != Path("."):
                destination.parent.mkdir(parents=True, exist_ok=True)

            as_image = getattr(part, "as_image", None)
            if callable(as_image):
                try:
                    image = as_image()
                except Exception:
                    image = None
                if image is not None:
                    image.save(destination)
                    return str(destination)

            destination.write_bytes(image_bytes)
        except (OSError, ValueError) as exc:
            raise GeminiError(f"Failed to save image to {destination}") from exc

        return str(destination)

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

    @staticmethod
    def normalize_image_input(image: object) -> object:
        if isinstance(image, Image.Image):
            return image

        if isinstance(image, (str, os.PathLike)):
            path = Path(image).expanduser()
            if not path.is_file():
                raise GeminiError("Image must be a local image path, PIL image, or Gemini SDK-compatible object")
            try:
                with Image.open(path) as opened:
                    return opened.copy()
            except (OSError, UnidentifiedImageError) as exc:
                raise GeminiError(f"Failed to open image: {path}") from exc

        if isinstance(image, list | tuple):
            return [BaseGeminiImageTask.normalize_image_input(item) for item in image]

        return image

    @staticmethod
    def field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def require_prompt(prompt: str) -> None:
        if not prompt:
            raise GeminiError("Prompt is required")


class GeminiImageTextToImage(BaseGeminiImageTask):
    """Gemini text-to-image wrapper with a local-model-style API."""

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        response_modalities: Iterable[str] = ("IMAGE",),
        aspect_ratio: str | None = None,
        image_size: str | None = None,
    ) -> GeminiImageResult:
        """Generate one image from a text prompt."""

        self.require_prompt(prompt)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=self.content_config(
                response_modalities=response_modalities,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        )
        return self.image_result(response, output_path=output_path)


class GeminiImageEditing(BaseGeminiImageTask):
    """Gemini image editing wrapper with a local-model-style API."""

    def generate(
        self,
        image: object,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        response_modalities: Iterable[str] = ("IMAGE",),
        aspect_ratio: str | None = None,
        image_size: str | None = None,
    ) -> GeminiImageResult:
        """Generate an edited image from an input image and text prompt."""

        self.require_prompt(prompt)
        normalized_image = self.normalize_image_input(image)
        images = normalized_image if isinstance(normalized_image, list) else [normalized_image]
        contents = [prompt, *images]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=self.content_config(
                response_modalities=response_modalities,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        )
        return self.image_result(response, output_path=output_path)


class NanoBananaTextToImage(GeminiImageTextToImage):
    """Nano Banana text-to-image wrapper for gemini-2.5-flash-image."""

    model_name = "gemini-2.5-flash-image"


class NanoBananaImageEditing(GeminiImageEditing):
    """Nano Banana image editing wrapper for gemini-2.5-flash-image."""

    model_name = "gemini-2.5-flash-image"


class NanoBananaProTextToImage(GeminiImageTextToImage):
    """Nano Banana Pro text-to-image wrapper for gemini-3-pro-image."""

    model_name = "gemini-3-pro-image"


class NanoBananaProImageEditing(GeminiImageEditing):
    """Nano Banana Pro image editing wrapper for gemini-3-pro-image."""

    model_name = "gemini-3-pro-image"


class NanoBanana2TextToImage(GeminiImageTextToImage):
    """Nano Banana 2 text-to-image wrapper for gemini-3.1-flash-image."""

    model_name = "gemini-3.1-flash-image"


class NanoBanana2ImageEditing(GeminiImageEditing):
    """Nano Banana 2 image editing wrapper for gemini-3.1-flash-image."""

    model_name = "gemini-3.1-flash-image"
