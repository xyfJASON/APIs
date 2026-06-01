## Gemini Video Understanding

Official documentation: https://ai.google.dev/gemini-api/docs/video-understanding

### Environment Variables

- `GEMINI_API_KEY`: Required. Your Gemini API key.

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### Model List

- `gemini-3.5-flash`
- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-2.5-flash`

### Video Understanding

```python
from apis import GeminiVideoUnderstanding

model = GeminiVideoUnderstanding.from_env(model_name="gemini-3.5-flash")
result = model.generate(
    video="input.mp4",
    prompt="Summarize the key events in this video.",
)

print(result.text)
```

- `video`: Required. A local video path, video URL, YouTube URL, raw video bytes, Gemini uploaded File object, or SDK-compatible `Part`.
- `prompt`: Required. Text prompt or question about the video.
- `upload`: Optional. Force File API upload for local videos when `True`, force inline bytes when `False`, or auto-select by file size when omitted.
- `max_inline_bytes`: Optional. Inline-size threshold for local files. Defaults to 20 MiB.
- `mime_type`: Optional for paths and URLs, required when `video` is raw bytes.
- `start_offset`: Optional. Clip start offset, such as `10s`.
- `end_offset`: Optional. Clip end offset, such as `45s`.
- `fps`: Optional. Sampling frame rate for video understanding.
- `media_resolution`: Optional. Use Gemini-supported values such as `low`, `medium`, or `high`.
- `temperature`: Optional. Sampling temperature.
- `max_output_tokens`: Optional. Maximum output tokens.
- `upload_poll_interval`: Optional. Seconds between File API processing polls. Defaults to `2`.
- `upload_timeout`: Optional. Maximum seconds to wait for uploaded video processing. Defaults to `300`.

### Errors

- `GeminiError`: Raised for wrapper-level errors such as missing `GEMINI_API_KEY`, missing prompts, unsupported video inputs, missing MIME types for raw bytes, upload processing failures, timeouts, or responses without text.
- Google Gen AI SDK API exceptions are raised directly by the `google-genai` package.
