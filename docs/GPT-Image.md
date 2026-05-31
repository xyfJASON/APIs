## GPT-Image-2 APIs

Official documentation: https://developers.openai.com/api/docs/guides/image-generation

### Environment Variables

- `OPENAI_API_KEY`: Required. Your OpenAI API key.
- `OPENAI_BASE_URL`: Optional. OpenAI API base URL. If omitted, the OpenAI SDK default is used.

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Text-to-Image

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

- `prompt`: Required. Text prompt for the generated image.
- `output_path`: Optional. Local path for saving the image. If omitted, base64 image data is returned.
- `size`: Optional. Image size. Defaults to `auto`.
- `quality`: Optional. Image quality. Defaults to `auto`.

### Image Editing

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

- `image`: Required. A local image path, file object, bytes, or a list of image inputs accepted by the OpenAI SDK.
- `prompt`: Required. Text prompt describing the edit.
- `output_path`: Optional. Local path for saving the edited image.
- `mask`: Optional. A local mask path or file input accepted by the OpenAI SDK.
- `size`: Optional. Image size. Defaults to `auto`.
- `quality`: Optional. Image quality. Defaults to `auto`.
- `input_fidelity`: Optional. Input preservation strength such as `high` or `low`.

### Errors

- `GPTError`: Raised for wrapper-level errors such as missing `OPENAI_API_KEY`, unsupported output file extensions, invalid response data, or image save failures.
- OpenAI SDK API exceptions are raised directly by the `openai` package.
