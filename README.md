## Image Generation

### GPT-Image-2 Text-to-Image

Official documentation: https://developers.openai.com/api/docs/guides/image-generation

#### Environment Variables

- `OPENAI_API_KEY`: Required. Your OpenAI API key.
- `OPENAI_BASE_URL`: Optional. OpenAI API base URL. If omitted, the OpenAI SDK default is used.

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### Usage

```python
from gpt_image_2 import GPTImage2TextToImage

model = GPTImage2TextToImage.from_env()
result = model.generate(
    prompt="A cinematic product photo of a glass teapot on a marble counter.",
    output_path="outputs/teapot.jpg",
    size="1024x1024",
    quality="auto",
)

print(result.path)
print(result.b64_json)
```

#### Parameters

- `prompt`: Required. Text prompt for the generated image.
- `output_path`: Optional. Local path for saving the image. If omitted, the API request defaults to PNG output and only base64 image data is returned.
- `size`: Optional. Image size. Defaults to `auto`.
- `quality`: Optional. Image quality. Defaults to `auto`.

#### Errors

- `GPTImage2Error`: Raised for wrapper-level errors such as missing `OPENAI_API_KEY`, unsupported output file extensions, invalid response data, or image save failures.
- OpenAI SDK API exceptions are raised directly by the `openai` package.


## Video Generation

### Kling V3 Image-to-Video

Official documentation: https://klingai.com/document-api

#### Environment Variables

- `KLING_ACCESS_KEY`: Required. Your Kling API AccessKey.
- `KLING_SECRET_KEY`: Required. Your Kling API SecretKey, used to generate the JWT authorization token.
- `KLING_BASE_URL`: Optional. Kling API base URL. Defaults to `https://api-beijing.klingai.com`.

```bash
export KLING_ACCESS_KEY="your-access-key"
export KLING_SECRET_KEY="your-secret-key"
```

#### Usage

```python
from kling import KlingV3ImageToVideo

model = KlingV3ImageToVideo.from_env()
result = model.generate(
    image="input.png",
    prompt="The camera slowly pushes in while the person smiles.",
    output_path="outputs/kling.mp4",
    duration=5,
    mode="std",
)

print(result.url)
print(result.path)
```

#### Parameters

- `image`: Required. A local image path, image URL, raw base64 string, or data URI.
- `prompt`: Optional. Positive text prompt. Defaults to an empty string.
- `output_path`: Optional. Local path for saving the generated video. If omitted, only the Kling video URL is returned.
- `duration`: Optional. Video duration in seconds. Defaults to `5`.
- `mode`: Optional. Generation mode. Defaults to `std`; use Kling-supported values such as `std` or `pro`.
- `poll_interval`: Optional. Seconds between task status polls. Defaults to `5`.
- `timeout`: Optional. Maximum seconds to wait for the task to finish. Defaults to `600`.

#### Errors

- `KlingError`: Base class for all errors raised by this wrapper. Use it to catch every Kling-related failure.
- `KlingAPIError`: Raised when the Kling HTTP API returns an error, a network request fails, the response format is invalid, or a successful task response does not include a video URL. Includes `code`, `status`, `request_id`, and `response` fields.
- `KlingTaskFailed`: Raised when the generation task reaches the `failed` state. Includes `task_id` and `response` fields.
- `KlingTimeout`: Raised when polling exceeds `timeout`. Includes `task_id` and `timeout` fields.



## Tests

```bash
python -m unittest discover
```
