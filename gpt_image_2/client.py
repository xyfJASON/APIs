"""Small OpenAI SDK client for GPT-Image-2 text-to-image generation."""

from __future__ import annotations

import base64
import binascii
import dataclasses
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from .errors import GPTImage2Error


@dataclasses.dataclass
class ImageResult:
    """Result returned by :meth:`GPTImage2TextToImage.generate`."""

    b64_json: str
    path: str | None
    created: int | None
    revised_prompt: str | None
    raw: object


class GPTImage2TextToImage:
    """GPT-Image-2 text-to-image wrapper with a local-model-style API."""

    model_name = "gpt-image-2"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        client: Any | None = None,
        request_timeout: float | None = None,
    ) -> None:
        if client is not None:
            self.client = client
            return

        if not api_key:
            raise GPTImage2Error("OpenAI API key is required")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = self._normalize_base_url(base_url)
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout

        self.client = OpenAI(**kwargs)

    @classmethod
    def from_env(cls) -> "GPTImage2TextToImage":
        """Build a model wrapper from OPENAI_API_KEY and optional OPENAI_BASE_URL."""

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL")

        if not api_key:
            raise GPTImage2Error("Missing required environment variable: OPENAI_API_KEY")

        return cls(api_key=api_key, base_url=base_url)

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        size: str = "auto",
        quality: str = "auto",
    ) -> ImageResult:
        """Generate one image from a text prompt."""

        if not prompt:
            raise GPTImage2Error("Prompt is required")

        output_format = self._output_format(output_path)
        response = self.client.images.generate(
            model=self.model_name,
            prompt=prompt,
            size=size,
            quality=quality,
            output_format=output_format,
        )

        image = self._first_image(response)
        b64_json = self._field(image, "b64_json")
        if not b64_json:
            raise GPTImage2Error("OpenAI image response did not include b64_json")

        saved_path = None
        if output_path is not None:
            saved_path = self._save_image(b64_json, output_path)

        return ImageResult(
            b64_json=b64_json,
            path=saved_path,
            created=self._field(response, "created"),
            revised_prompt=self._field(image, "revised_prompt"),
            raw=response,
        )

    @staticmethod
    def _output_format(output_path: str | os.PathLike[str] | None) -> str:
        if output_path is None:
            return "png"

        suffix = Path(output_path).suffix.lower()
        if suffix == ".png":
            return "png"
        if suffix in (".jpg", ".jpeg"):
            return "jpeg"
        if suffix == ".webp":
            return "webp"

        raise GPTImage2Error(
            "Unsupported output_path extension. Use .png, .jpg, .jpeg, or .webp."
        )

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized == "https://api.openai.com":
            return "https://api.openai.com/v1"
        return normalized

    @classmethod
    def _first_image(cls, response: object) -> object:
        data = cls._field(response, "data")
        if not isinstance(data, list) or not data:
            raise GPTImage2Error("OpenAI image response did not include data")
        return data[0]

    @staticmethod
    def _field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def _save_image(b64_json: str, output_path: str | os.PathLike[str]) -> str:
        destination = Path(output_path).expanduser()
        try:
            image_bytes = base64.b64decode(b64_json, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise GPTImage2Error("OpenAI image response included invalid base64 data") from exc

        try:
            if destination.parent != Path("."):
                destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(image_bytes)
        except OSError as exc:
            raise GPTImage2Error(f"Failed to save image to {destination}") from exc

        return str(destination)
