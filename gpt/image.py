"""Shared image task wrappers for GPT Image APIs."""

from __future__ import annotations

import contextlib
import base64
import binascii
import dataclasses
import os
from pathlib import Path
from typing import Any, Self

from .client import GPTClient
from .errors import GPTImage2Error


@dataclasses.dataclass
class ImageResult:
    """Generated image result returned by GPT image wrappers."""

    b64_json: str
    path: str | None
    created: int | None
    revised_prompt: str | None
    raw: object


class BaseGPTImageTask:
    """Shared response handling for GPT image generation tasks."""

    model_name = "gpt-image-2"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: GPTClient | None = None,
        base_url: str | None = None,
        request_timeout: float | None = None,
    ) -> None:
        if not getattr(self, "model_name", ""):
            raise ValueError("GPT image model name is required")

        if client is not None:
            self.client = client
            return

        self.client = GPTClient(
            api_key=api_key,
            base_url=base_url,
            request_timeout=request_timeout,
        )

    @classmethod
    def from_env(cls) -> Self:
        return cls(client=GPTClient.from_env())

    def image_result(self, response: object, output_path: str | os.PathLike[str] | None = None) -> ImageResult:
        image = self.first_image(response)
        b64_json = self.field(image, "b64_json")
        if not b64_json:
            raise GPTImage2Error("OpenAI image response did not include b64_json")

        saved_path = None
        if output_path is not None:
            saved_path = self.save_base64_image(b64_json, output_path)

        return ImageResult(
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

        raise GPTImage2Error(
            "Unsupported output_path extension. Use .png, .jpg, .jpeg, or .webp."
        )

    @staticmethod
    def save_base64_image(b64_json: str, output_path: str | os.PathLike[str]) -> str:
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

    @classmethod
    def first_image(cls, response: object) -> object:
        data = cls.field(response, "data")
        if not isinstance(data, list) or not data:
            raise GPTImage2Error("OpenAI image response did not include data")
        return data[0]

    @staticmethod
    def field(value: object, name: str) -> Any:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @staticmethod
    def require_prompt(prompt: str) -> None:
        if not prompt:
            raise GPTImage2Error("Prompt is required")

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


class GPTImage2TextToImage(BaseGPTImageTask):
    """GPT-Image-2 text-to-image wrapper with a local-model-style API."""

    def generate(
        self,
        prompt: str,
        output_path: str | os.PathLike[str] | None = None,
        *,
        size: str = "auto",
        quality: str = "auto",
    ) -> ImageResult:
        """Generate one image from a text prompt."""

        self.require_prompt(prompt)
        response = self.client.sdk.images.generate(
            model=self.model_name,
            prompt=prompt,
            size=size,
            quality=quality,
            output_format=self.output_format(output_path),
        )
        return self.image_result(response, output_path=output_path)


class GPTImage2ImageEditing(BaseGPTImageTask):
    """GPT-Image-2 image editing wrapper with a local-model-style API."""

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
    ) -> ImageResult:
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

            response = self.client.sdk.images.edit(**payload)

        return self.image_result(response, output_path=output_path)
