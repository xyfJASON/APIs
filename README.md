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



## Tests

```bash
conda run -n apis python -m unittest discover
```
