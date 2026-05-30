## Image Generation

### GPT-Image-2

Official documentation: https://developers.openai.com/api/docs/guides/image-generation

#### Environment Variables

- `OPENAI_API_KEY`: Required. Your OpenAI API key.
- `OPENAI_BASE_URL`: Optional. OpenAI API base URL. If omitted, the OpenAI SDK default is used.

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### Text-to-Image Usage

```python
from apis import GPTImage2TextToImage

model = GPTImage2TextToImage.from_env()
result = model.generate(
    prompt="A cinematic product photo of a glass teapot on a marble counter.",
    output_path="outputs/gpt-image-2-text2image.jpg",
    size="1024x1024",
    quality="auto",
)

print(result.path)
print(result.b64_json)
```

#### Text-to-Image Parameters

- `prompt`: Required. Text prompt for the generated image.
- `output_path`: Optional. Local path for saving the image. If omitted, the API request defaults to PNG output and only base64 image data is returned.
- `size`: Optional. Image size. Defaults to `auto`.
- `quality`: Optional. Image quality. Defaults to `auto`.

#### Image Editing Usage

```python
from apis import GPTImage2ImageEditing

model = GPTImage2ImageEditing.from_env()
result = model.generate(
    image="input.png",
    prompt="Replace the teapot with a ceramic mug.",
    output_path="outputs/gpt-image-2-edited.webp",
    size="1024x1024",
    quality="auto",
)

print(result.path)
print(result.b64_json)
```

#### Image Editing Parameters

- `image`: Required. A local image path, file object, bytes, or a list of image inputs accepted by the OpenAI SDK.
- `prompt`: Required. Text prompt describing the edit.
- `output_path`: Optional. Local path for saving the edited image.
- `mask`: Optional. A local mask path or file input accepted by the OpenAI SDK.
- `size`: Optional. Image size. Defaults to `auto`.
- `quality`: Optional. Image quality. Defaults to `auto`.
- `input_fidelity`: Optional. Input preservation strength such as `high` or `low`.

#### Errors

- `GPTError`: Raised for wrapper-level errors such as missing `OPENAI_API_KEY`, unsupported output file extensions, invalid response data, or image save failures.
- OpenAI SDK API exceptions are raised directly by the `openai` package.


## Video Generation

### Kling Video APIs

Official documentation: https://klingai.com/document-api

#### Environment Variables

- `KLING_ACCESS_KEY`: Required. Your Kling API AccessKey.
- `KLING_SECRET_KEY`: Required. Your Kling API SecretKey, used to generate the JWT authorization token.
- `KLING_BASE_URL`: Optional. Kling API base URL. Defaults to `https://api-beijing.klingai.com`.

```bash
export KLING_ACCESS_KEY="your-access-key"
export KLING_SECRET_KEY="your-secret-key"
```

#### Text-to-Video Usage

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

#### Text-to-Video Parameters

- `prompt`: Required. Positive text prompt for the generated video.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Kling video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `mode`: Optional. Generation mode. Defaults to `std`; use Kling-supported values such as `std` or `pro`.
- `aspect_ratio`: Optional. Output frame aspect ratio. Defaults to `16:9`; Kling also supports values such as `9:16` and `1:1`.
- `negative_prompt`: Optional. Negative text prompt. Defaults to an empty string.
- `sound`: Optional. Whether to generate sound. Defaults to `off`; use `on` when supported by the selected model/mode.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

#### Image-to-Video Usage

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

#### Image-to-Video Parameters

- `image`: Required. A local image path, image URL, raw base64 string, or data URI.
- `prompt`: Optional. Positive text prompt. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Kling video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `mode`: Optional. Generation mode. Defaults to `std`; use Kling-supported values such as `std` or `pro`.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

#### Video Extension Usage

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

#### Video Extension Parameters

- `video_id`: Required. Kling-generated video ID to extend.
- `prompt`: Optional. Text prompt for the extension. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the extended video. If omitted, only the Kling video URL is returned.
- `negative_prompt`: Optional. Negative text prompt. Defaults to an empty string.
- `cfg_scale`: Optional. Prompt reference strength in Kling's `[0, 1]` range. If omitted, Kling's API default is used.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

#### Errors

- `KlingError`: Base class for all errors raised by this wrapper. Use it to catch every Kling-related failure.
- `KlingAPIError`: Raised when the Kling HTTP API returns an error, a network request fails, the response format is invalid, or a successful task response does not include a video URL.
- `KlingTaskFailedError`: Raised when the generation task reaches the `failed` state.
- `KlingTimeoutError`: Raised when polling exceeds `timeout`.


### Seedance 2.0 Video APIs

Official documentation: https://www.volcengine.com/docs/82379/1520757?lang=zh

#### Environment Variables

- `ARK_API_KEY`: Required. Your Volcano Engine Ark API key.
- `ARK_BASE_URL`: Optional. Ark API base URL. If omitted, the Volcano Engine SDK default is used.

```bash
export ARK_API_KEY="your-ark-api-key"
```

#### Text-to-Video Usage

```python
from apis import Seedance20TextToVideo

model = Seedance20TextToVideo.from_env()
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

#### Text-to-Video Parameters

- `prompt`: Required. Text prompt for the generated video.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Seedance video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `ratio`: Optional. Output frame aspect ratio. Defaults to `adaptive`; use Seedance-supported values such as `16:9`, `9:16`, or `1:1`.
- `resolution`: Optional. Output resolution such as `480p`, `720p`, or `1080p`.
- `seed`: Optional. Random seed for generation.
- `generate_audio`: Optional. Whether to generate synchronized audio. Defaults to `False`.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

#### Image-to-Video Usage

```python
from apis import Seedance20ImageToVideo

model = Seedance20ImageToVideo.from_env()
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

#### Image-to-Video Parameters

- `image`: Required. A local image path, image URL, data URI, or `asset://` ID.
- `prompt`: Optional. Text prompt. Defaults to an empty string.
- `last_image`: Optional. A local image path, image URL, data URI, or `asset://` ID for first/last-frame generation.
- `output_path`: Optional. Local path for saving the generated video.
- Other generation and polling parameters match text-to-video.

#### Video Extension Usage

```python
from apis import Seedance20VideoExtension

model = Seedance20VideoExtension.from_env()
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

#### Video Extension Parameters

- `video`: Required. A video URL or `asset://` ID, or a list/tuple of one to three video URLs or `asset://` IDs.
- `prompt`: Optional. Text prompt describing the extension or transition. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the generated video.
- Other generation and polling parameters match text-to-video.

#### Errors

- `SeedanceError`: Base class for wrapper-level errors such as missing `ARK_API_KEY`, invalid local media inputs, failed downloads, or missing result URLs.
- `SeedanceTaskFailedError`: Raised when polling reaches `failed`, `expired`, or `cancelled`.
- `SeedanceTimeoutError`: Raised when polling exceeds `timeout`.
- Volcano Engine SDK API exceptions are raised directly by `volcenginesdkarkruntime`.
