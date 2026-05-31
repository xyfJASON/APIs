## Nano Banana APIs

Official documentation: https://ai.google.dev/gemini-api/docs/image-generation

### Environment Variables

- `GEMINI_API_KEY`: Required. Your Gemini API key.

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### Text-to-Image

```python
from apis import NanoBanana2TextToImage

model = NanoBanana2TextToImage.from_env()
result = model.generate(
    prompt="A serene landscape with mountains and a river at sunset.",
    output_path="outputs/gemini-text2image.png",
    aspect_ratio="1:1",
)

print(result.path)
print(result.b64_json)
```

- `prompt`: Required. Text prompt for the generated image.
- `output_path`: Optional. Local path for saving the image. If omitted, base64 image data is returned.
- `response_modalities`: Optional. Gemini response modalities. Defaults to `("IMAGE",)`.
- `aspect_ratio`: Optional. Gemini image aspect ratio, such as `1:1`, `16:9`, or `9:16`.
- `image_size`: Optional. Gemini image size when supported by the selected model.

### Image Editing

```python
from apis import NanoBanana2ImageEditing

model = NanoBanana2ImageEditing.from_env()
result = model.generate(
    image="input.png",
    prompt="Change the background to a Martian landscape with red rocks and a dusty sky.",
    output_path="outputs/gemini-edited.png",
)

print(result.path)
print(result.b64_json)
```

- `image`: Required. A local image path, `PIL.Image.Image`, SDK-compatible object, or a list of those inputs.
- `prompt`: Required. Text prompt describing the edit.
- `output_path`: Optional. Local path for saving the edited image.
- `response_modalities`: Optional. Gemini response modalities. Defaults to `("IMAGE",)`.
- `aspect_ratio`: Optional. Gemini image aspect ratio, such as `1:1`, `16:9`, or `9:16`.
- `image_size`: Optional. Gemini image size when supported by the selected model.

### Model Aliases

- `NanoBanana`: `gemini-2.5-flash-image`
- `NanoBananaPro`: `gemini-3-pro-image`
- `NanoBanana2`: `gemini-3.1-flash-image`

Each alias has `TextToImage` and `ImageEditing` classes.

```python
# Nano Banana 2 (gemini-3.1-flash-image)
from apis import NanoBanana2TextToImage, NanoBanana2ImageEditing

# Nano Banana Pro (gemini-3-pro-image)
from apis import NanoBananaProTextToImage, NanoBananaProImageEditing

# Nano Banana (gemini-2.5-flash-image)
from apis import NanoBananaTextToImage, NanoBananaImageEditing
```

### Errors

- `GeminiError`: Raised for wrapper-level errors such as missing `GEMINI_API_KEY`, missing prompts, unsupported image inputs, invalid response data, or image save failures.
- Google Gen AI SDK API exceptions are raised directly by the `google-genai` package.
