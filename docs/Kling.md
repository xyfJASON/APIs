## Kling V3 Video APIs

Official documentation: https://klingai.com/document-api

### Environment Variables

- `KLING_ACCESS_KEY`: Required. Your Kling API AccessKey.
- `KLING_SECRET_KEY`: Required. Your Kling API SecretKey, used to generate the JWT authorization token.
- `KLING_BASE_URL`: Optional. Kling API base URL. Defaults to `https://api-beijing.klingai.com`.

```bash
export KLING_ACCESS_KEY="your-access-key"
export KLING_SECRET_KEY="your-secret-key"
```

### Text-to-Video

```python
from apis import KlingV3TextToVideo

model = KlingV3TextToVideo.from_env()
result = model.generate(
    prompt="A small rabbit wearing glasses reads a newspaper at a cafe table.",
    output_path="outputs/kling-text2video.mp4",
    duration=5,
    mode="std",
    aspect_ratio="16:9",
)

print(result.url)
print(result.path)
```

- `prompt`: Required. Positive text prompt for the generated video.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Kling video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `mode`: Optional. Generation mode. Defaults to `std`; use Kling-supported values such as `std` or `pro`.
- `aspect_ratio`: Optional. Output frame aspect ratio. Defaults to `16:9`; Kling also supports values such as `9:16` and `1:1`.
- `negative_prompt`: Optional. Negative text prompt. Defaults to an empty string.
- `sound`: Optional. Whether to generate sound. Defaults to `off`; use `on` when supported by the selected model/mode.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

### Image-to-Video

```python
from apis import KlingV3ImageToVideo

model = KlingV3ImageToVideo.from_env()
result = model.generate(
    image="input.png",
    prompt="The camera slowly pushes in while the person smiles.",
    output_path="outputs/kling-image2video.mp4",
    duration=5,
    mode="std",
)

print(result.url)
print(result.path)
```

- `image`: Required. A local image path, image URL, raw base64 string, or data URI.
- `prompt`: Optional. Positive text prompt. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Kling video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `mode`: Optional. Generation mode. Defaults to `std`; use Kling-supported values such as `std` or `pro`.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

### Video Extension

```python
from apis import KlingVideoExtension

model = KlingVideoExtension.from_env()
result = model.generate(
    video_id="743211632612511839",
    prompt="A puppy appears and runs into the scene.",
    output_path="outputs/kling-extended.mp4",
)

print(result.url)
print(result.path)
```

- `video_id`: Required. Kling-generated video ID to extend.
- `prompt`: Optional. Text prompt for the extension. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the extended video. If omitted, only the Kling video URL is returned.
- `negative_prompt`: Optional. Negative text prompt. Defaults to an empty string.
- `cfg_scale`: Optional. Prompt reference strength in Kling's `[0, 1]` range. If omitted, Kling's API default is used.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

### Errors

- `KlingError`: Base class for all errors raised by this wrapper. Use it to catch every Kling-related failure.
- `KlingAPIError`: Raised when the Kling HTTP API returns an error, a network request fails, the response format is invalid, or a successful task response does not include a video URL.
- `KlingTaskFailedError`: Raised when the generation task reaches the `failed` state.
- `KlingTimeoutError`: Raised when polling exceeds `timeout`.
