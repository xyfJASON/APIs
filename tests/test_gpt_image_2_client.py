import base64
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from gpt_image_2 import GPTImage2Error, GPTImage2TextToImage


class FakeImages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.images = FakeImages(response)


def image_response(image_bytes=b"image-bytes", *, created=123, revised_prompt="revised prompt"):
    return SimpleNamespace(
        created=created,
        data=[
            SimpleNamespace(
                b64_json=base64.b64encode(image_bytes).decode("ascii"),
                revised_prompt=revised_prompt,
            )
        ],
    )


class GPTImage2ClientTest(unittest.TestCase):
    def make_model(self, response=None):
        fake_client = FakeClient(response or image_response())
        return GPTImage2TextToImage(client=fake_client), fake_client

    def test_from_env_requires_openai_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GPTImage2Error):
                GPTImage2TextToImage.from_env()

    def test_generate_calls_sdk_with_gpt_image_2(self):
        model, fake_client = self.make_model()

        result = model.generate(
            prompt="A glass teapot on a marble counter",
            size="1024x1024",
            quality="auto",
        )

        self.assertEqual(result.b64_json, base64.b64encode(b"image-bytes").decode("ascii"))
        self.assertIsNone(result.path)
        self.assertEqual(result.created, 123)
        self.assertEqual(result.revised_prompt, "revised prompt")
        self.assertEqual(
            fake_client.images.calls[0],
            {
                "model": "gpt-image-2",
                "prompt": "A glass teapot on a marble counter",
                "size": "1024x1024",
                "quality": "auto",
                "output_format": "png",
            },
        )

    def test_output_path_infers_format_and_saves_image(self):
        cases = {
            "output.png": "png",
            "output.jpg": "jpeg",
            "output.jpeg": "jpeg",
            "output.webp": "webp",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            for filename, expected_format in cases.items():
                with self.subTest(filename=filename):
                    model, fake_client = self.make_model(image_response(b"saved-image"))
                    output_path = Path(tmpdir) / filename

                    result = model.generate("prompt", output_path=output_path)

                    self.assertEqual(fake_client.images.calls[0]["output_format"], expected_format)
                    self.assertEqual(output_path.read_bytes(), b"saved-image")
                    self.assertEqual(result.path, str(output_path))

    def test_generate_raises_on_unsupported_output_path_extension(self):
        model, fake_client = self.make_model()

        with self.assertRaises(GPTImage2Error):
            model.generate("prompt", output_path="output.gif")

        self.assertEqual(fake_client.images.calls, [])

    def test_generate_raises_when_response_has_no_data(self):
        model, _ = self.make_model(SimpleNamespace(data=[]))

        with self.assertRaises(GPTImage2Error):
            model.generate("prompt")

    def test_generate_raises_when_response_has_no_b64_json(self):
        model, _ = self.make_model(SimpleNamespace(data=[SimpleNamespace(revised_prompt="prompt")]))

        with self.assertRaises(GPTImage2Error):
            model.generate("prompt")

    def test_generate_raises_when_base64_data_is_invalid(self):
        response = SimpleNamespace(data=[SimpleNamespace(b64_json="not valid base64!")])
        model, _ = self.make_model(response)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(GPTImage2Error):
                model.generate("prompt", output_path=Path(tmpdir) / "output.png")


if __name__ == "__main__":
    unittest.main()
