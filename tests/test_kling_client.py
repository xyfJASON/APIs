import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kling import KlingAPIError, KlingTaskFailed, KlingTimeout, KlingV3ImageToVideo


def decode_jwt_part(part):
    padding = "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part + padding).decode("utf-8"))


class FakeHTTPResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class KlingClientTest(unittest.TestCase):
    def make_client(self):
        return KlingV3ImageToVideo("access-key", "secret-key", base_url="https://example.test")

    def test_jwt_contains_required_claims(self):
        client = self.make_client()

        with mock.patch("time.time", return_value=1_000):
            token = client._encode_jwt_token()

        header, payload, signature = token.split(".")
        self.assertTrue(signature)
        self.assertEqual(decode_jwt_part(header), {"alg": "HS256", "typ": "JWT"})
        self.assertEqual(
            decode_jwt_part(payload),
            {"iss": "access-key", "exp": 2_800, "nbf": 995},
        )

    def test_normalize_image_supports_local_file_and_data_uri(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "input.png"
            image_path.write_bytes(b"image-bytes")

            self.assertEqual(
                KlingV3ImageToVideo._normalize_image(image_path),
                base64.b64encode(b"image-bytes").decode("ascii"),
            )

        self.assertEqual(
            KlingV3ImageToVideo._normalize_image("data:image/png;base64,aW1hZ2U="),
            "aW1hZ2U=",
        )

    def test_generate_polls_until_success(self):
        client = self.make_client()
        calls = []
        responses = [
            {"code": 0, "data": {"task_id": "task-1", "task_status": "submitted"}},
            {"code": 0, "data": {"task_id": "task-1", "task_status": "processing"}},
            {
                "code": 0,
                "data": {
                    "task_id": "task-1",
                    "task_status": "succeed",
                    "task_result": {"videos": [{"url": "https://video.test/out.mp4", "duration": "5"}]},
                },
            },
        ]

        def fake_request(method, path, *, json_body=None):
            calls.append((method, path, json_body))
            return responses.pop(0)

        client._request = fake_request
        with mock.patch("time.sleep", return_value=None):
            result = client.generate(
                image="https://image.test/input.png",
                prompt="slow camera push",
                poll_interval=0,
            )

        self.assertEqual(result.task_id, "task-1")
        self.assertEqual(result.status, "succeed")
        self.assertEqual(result.url, "https://video.test/out.mp4")
        self.assertIsNone(result.path)
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], "/v1/videos/image2video")
        self.assertEqual(calls[0][2]["model_name"], "kling-v3")
        self.assertEqual(calls[0][2]["image"], "https://image.test/input.png")
        self.assertEqual(calls[0][2]["prompt"], "slow camera push")
        self.assertEqual(calls[1][1], "/v1/videos/image2video/task-1")

    def test_generate_downloads_output_path(self):
        client = self.make_client()
        responses = [
            {"code": 0, "data": {"task_id": "task-2"}},
            {
                "code": 0,
                "data": {
                    "task_id": "task-2",
                    "task_status": "succeed",
                    "task_result": {"videos": [{"url": "https://video.test/out.mp4", "duration": "5"}]},
                },
            },
        ]
        client._request = lambda *args, **kwargs: responses.pop(0)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mp4"
            with mock.patch("urllib.request.urlopen", return_value=FakeHTTPResponse(b"mp4-bytes")):
                result = client.generate(image="raw-base64", output_path=output_path, poll_interval=0)

            self.assertEqual(output_path.read_bytes(), b"mp4-bytes")
            self.assertEqual(result.path, str(output_path))

    def test_generate_raises_when_task_fails(self):
        client = self.make_client()
        responses = [
            {"code": 0, "data": {"task_id": "task-3"}},
            {
                "code": 0,
                "data": {
                    "task_id": "task-3",
                    "task_status": "failed",
                    "task_status_msg": "content rejected",
                },
            },
        ]
        client._request = lambda *args, **kwargs: responses.pop(0)

        with self.assertRaises(KlingTaskFailed):
            client.generate(image="raw-base64", poll_interval=0)

    def test_generate_raises_on_timeout(self):
        client = self.make_client()
        responses = [
            {"code": 0, "data": {"task_id": "task-4"}},
            {"code": 0, "data": {"task_id": "task-4", "task_status": "processing"}},
        ]
        client._request = lambda *args, **kwargs: responses.pop(0)

        with self.assertRaises(KlingTimeout):
            client.generate(image="raw-base64", poll_interval=0, timeout=0)

    def test_request_raises_on_nonzero_api_code(self):
        client = self.make_client()

        with mock.patch(
            "urllib.request.urlopen",
            return_value=FakeHTTPResponse({"code": 1201, "message": "bad parameter", "request_id": "req-1"}),
        ):
            with self.assertRaises(KlingAPIError) as context:
                client._request("GET", "/bad")

        self.assertEqual(context.exception.code, 1201)
        self.assertEqual(context.exception.request_id, "req-1")


if __name__ == "__main__":
    unittest.main()
