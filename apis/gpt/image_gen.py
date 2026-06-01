"""Image task wrappers for GPT Image APIs."""

from __future__ import annotations

import contextlib
import base64
import binascii
import dataclasses
import os
from pathlib import Path
from typing import Any, Self

from openai import OpenAI

from .errors import GPTError


@dataclasses.dataclass
class GPTImageResult:
    """Generated image result returned by GPT image wrappers."""

    b64_json: str
    path: str | None
    created: int | None
    revised_prompt: str | None
    raw: object


class BaseGPTImageGenerationTask:
    """Base class for GPT image generation tasks."""

    model_name: str

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: Any | None = None,
        base_url: str | None = None,
        request_timeout: float | None = None,
        model_name: str | None = None,
    ) -> None:
        self.model_name = self.require_model_name(model_name)
        if client is not None:
            self.client = client
            return

        if not api_key:
            raise GPTError("OpenAI API key is required")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url is not None:
            kwargs["base_url"] = self.normalize_base_url(base_url)
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout
        self.client = OpenAI(**kwargs)

    @classmethod
    def from_env(cls, *, model_name: str | None = None) -> Self:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key:
            raise GPTError("Missing required environment variable: OPENAI_API_KEY")
        return cls(api_key=api_key, base_url=base_url, model_name=model_name)

    def image_result(self, response: object, output_path: str | os.PathLike[str] | None = None) -> GPTImageResult:
        image = self.first_image(response)
        b64_json = self.field(image, "b64_json")
        if not b64_json:
            raise GPTError("OpenAI image response did not include b64_json")

        saved_path = None
        if output_path is not None:
            saved_path = self.save_base64_image(b64_json, output_path)

        return GPTImageResult(
            b64_json=b64_json,
            path=saved_path,
            created=self.field(response, "created"),
            revised_prompt=self.field(image, "revised_prompt"),
            raw=response,
        )

    @staticmethod
    def output_format(output_path: str | os.PathLike[str] | None) -> str:
        if output_path is None:
            return "png"

        suffix = Path(output_path).suffix.lower()
        if suffix == ".png":
            return "png"
        if suffix in (".jpg", ".jpeg"):
            return "jpeg"
        if suffix == ".webp":
            return "webp"

        raise GPTError(
            "Unsupported output_path extension. Use .png, .jpg, .jpeg, or .webp."
        )

    @staticmethod
    def save_base64_image(b64_json: str, output_path: str | os.PathLike[str]) -> str:
        destination = Path(output_path).expanduser()
        try:
            image_bytes = base64.b64decode(b64_json, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise GPTError("OpenAI image response included invalid base64 data") from exc

        try:
            if destination.parent != Path("."):
                destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(image_bytes)
        except OSError as exc:
            raise GPTError(f"Failed to save image to {destination}") from exc

        return str(destination)

    @classmethod
    def first_image(cls, response: object) -> object:
        data = cls.field(response, "data")
        if not isinstance(data, list) or not data:
            raise GPTError("OpenAI image response did not include data")
        return data[0]

    @staticmethod
    def field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def require_prompt(prompt: str) -> None:
        if not prompt:
            raise GPTError("Prompt is required")

    @staticmethod
    def require_model_name(model_name: str | None) -> str:
        if not isinstance(model_name, str) or not model_name.strip():
            raise GPTError("model_name is required")
        return model_name.strip()

    @staticmethod
    def normalize_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/v1"):
            normalized = f"{normalized}/v1"
        return normalized

    @staticmethod
    def open_file_input(value: object, stack: contextlib.ExitStack) -> object:
        if isinstance(value, (str, os.PathLike)):
            path = Path(value).expanduser()
            if path.is_file():
                return stack.enter_context(path.open("rb"))
        return value

    @classmethod
    def open_image_input(cls, image: object, stack: contextlib.ExitStack) -> object:
        if isinstance(image, (str, bytes, os.PathLike)):
            return cls.open_file_input(image, stack)
        if isinstance(image, list | tuple):
            return [cls.open_file_input(item, stack) for item in image]
        return image


class GPTImageTextToImage(BaseGPTImageGenerationTask):
    """GPT image text-to-image wrapper with a local-model-style API."""

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        size: str = "auto",
        quality: str = "auto",
    ) -> GPTImageResult:
        """Generate one image from a text prompt."""

        self.require_prompt(prompt)
        response = self.client.images.generate(
            model=self.model_name,
            prompt=prompt,
            size=size,
            quality=quality,
            output_format=self.output_format(output_path),
        )
        return self.image_result(response, output_path=output_path)


class GPTImageEditing(BaseGPTImageGenerationTask):
    """GPT image editing wrapper with a local-model-style API."""

    def generate(
        self,
        image: object,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        mask: object | None = None,
        size: str = "auto",
        quality: str = "auto",
        input_fidelity: str | None = None,
    ) -> GPTImageResult:
        """Generate an edited image from an input image and text prompt."""

        self.require_prompt(prompt)
        with contextlib.ExitStack() as stack:
            payload: dict[str, Any] = {
                "model": self.model_name,
                "image": self.open_image_input(image, stack),
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "output_format": self.output_format(output_path),
            }
            if mask is not None:
                payload["mask"] = self.open_file_input(mask, stack)
            if input_fidelity is not None:
                payload["input_fidelity"] = input_fidelity

            response = self.client.images.edit(**payload)

        return self.image_result(response, output_path=output_path)
