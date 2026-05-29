"""Transport client shared by GPT API wrappers."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from openai import OpenAI

from .errors import GPTImage2Error


class GPTClient:
    """Authenticated OpenAI SDK client for GPT API wrappers."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        request_timeout: float | None = None,
        client: Any | None = None,
    ) -> None:
        self.request_timeout = request_timeout
        if client is not None:
            self.sdk = client
            return

        if not api_key:
            raise GPTImage2Error("OpenAI API key is required")

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = self.normalize_base_url(base_url)
        if request_timeout is not None:
            kwargs["timeout"] = request_timeout

        self.sdk = OpenAI(**kwargs)

    @classmethod
    def from_env(cls) -> "GPTClient":
        """Build a transport client from OPENAI_API_KEY and optional OPENAI_BASE_URL."""

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL")

        if not api_key:
            raise GPTImage2Error("Missing required environment variable: OPENAI_API_KEY")

        return cls(api_key=api_key, base_url=base_url)

    def download(self, url: str, output_path: str | os.PathLike[str]) -> str:
        destination = Path(output_path).expanduser()
        if destination.parent != Path("."):
            destination.parent.mkdir(parents=True, exist_ok=True)

        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                destination.write_bytes(response.read())
        except urllib.error.URLError as exc:
            raise GPTImage2Error(f"Failed to download OpenAI image: {exc.reason}") from exc

        return str(destination)

    @staticmethod
    def normalize_base_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized == "https://api.openai.com":
            return "https://api.openai.com/v1"
        return normalized
