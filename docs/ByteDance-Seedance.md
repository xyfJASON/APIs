## Seedance

Official documentation: https://www.volcengine.com/docs/82379/1520757?lang=zh

### Environment Variables

- `ARK_API_KEY`: Required. Your Volcano Engine Ark API key.
- `ARK_BASE_URL`: Optional. Ark API base URL. If omitted, the Volcano Engine SDK default is used.

```bash
export ARK_API_KEY="your-ark-api-key"
```

### Model List

- `doubao-seedance-2-0-260128`: Seedance 2.0
- `doubao-seedance-1-5-pro-251215`: Seedance 1.5 Pro
- `doubao-seedance-1-0-pro-250528`: Seedance 1.0 Pro

### Text-to-Video

```python
from apis import SeedanceTextToVideo

model = SeedanceTextToVideo.from_env(model_name="doubao-seedance-2-0-260128")
result = model.generate(
    prompt="A cinematic shot of morning light moving across a quiet greenhouse.",
    output_path="outputs/seedance-text2video.mp4",
    duration=5,
    ratio="16:9",
    resolution="720p",
    generate_audio=False,
)

print(result.url)
print(result.path)
```

- `prompt`: Required. Text prompt for the generated video.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Seedance video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `ratio`: Optional. Output frame aspect ratio. Defaults to `adaptive`; use Seedance-supported values such as `16:9`, `9:16`, or `1:1`.
- `resolution`: Optional. Output resolution such as `480p`, `720p`, or `1080p`.
- `seed`: Optional. Random seed for generation.
- `generate_audio`: Optional. Whether to generate synchronized audio. Defaults to `False`.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

### Image-to-Video

```python
from apis import SeedanceImageToVideo

model = SeedanceImageToVideo.from_env(model_name="doubao-seedance-2-0-260128")
result = model.generate(
    image="input.png",
    prompt="The camera gently pushes in as leaves move in the breeze.",
    output_path="outputs/seedance-image2video.mp4",
    duration=5,
    ratio="adaptive",
)

print(result.url)
print(result.path)
```

- `image`: Required. A local image path, image URL, data URI, or `asset://` ID.
- `prompt`: Optional. Text prompt. Defaults to an empty string.
- `last_image`: Optional. A local image path, image URL, data URI, or `asset://` ID for first/last-frame generation.
- `output_path`: Optional. Local path for saving the generated video.
- Other generation and polling parameters match text-to-video.

### Video Extension

```python
from apis import SeedanceVideoExtension

model = SeedanceVideoExtension.from_env(model_name="doubao-seedance-2-0-260128")
result = model.generate(
    video="https://example.com/input.mp4",
    prompt="Extend the shot forward as the camera enters the hallway.",
    output_path="outputs/seedance-extended.mp4",
    duration=8,
    ratio="16:9",
)

print(result.url)
print(result.path)
```

- `video`: Required. A video URL or `asset://` ID, or a list/tuple of one to three video URLs or `asset://` IDs.
- `prompt`: Optional. Text prompt describing the extension or transition. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the generated video.
- Other generation and polling parameters match text-to-video.

### Errors

- `SeedanceError`: Base class for wrapper-level errors such as missing `ARK_API_KEY`, invalid local media inputs, failed downloads, or missing result URLs.
- `SeedanceTaskFailedError`: Raised when polling reaches `failed`, `expired`, or `cancelled`.
- `SeedanceTimeoutError`: Raised when polling exceeds `timeout`.
- Volcano Engine SDK API exceptions are raised directly by `volcenginesdkarkruntime`.
