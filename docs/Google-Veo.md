## Veo

Official documentation: https://ai.google.dev/gemini-api/docs/video

### Environment Variables

- `GEMINI_API_KEY`: Required. Your Gemini API key.

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### Model List

- `veo-3.1-generate-preview`
- `veo-3.1-fast-generate-preview`

### Text-to-Video

```python
from apis import VeoTextToVideo

model = VeoTextToVideo.from_env(model_name="veo-3.1-generate-preview")
result = model.generate(
    prompt="A cinematic shot of a glass greenhouse in a rainstorm.",
    output_path="outputs/veo-text2video.mp4",
    aspect_ratio="16:9",
    resolution="720p",
    duration_seconds=8,
)

print(result.path)
print(result.uri)
```

- `prompt`: Required. Text prompt for the generated video.
- `output_path`: Optional. Local path for saving the generated video.
- `reference_images`: Optional. Up to three reference images for text-to-video reference generation.
- `reference_type`: Optional. Default reference image type for bare reference image inputs. Use `asset` or `style`.
- `aspect_ratio`: Optional. Supported values include `16:9` and `9:16`.
- `resolution`: Optional. Supported values include `720p` and `1080p`, depending on the model and task.
- `duration_seconds`: Optional. Duration of the generated clip.
- `negative_prompt`: Optional. Description of what to avoid.
- `person_generation`: Optional. Person generation policy, such as `dont_allow` or `allow_adult`.
- `number_of_videos`: Optional. Number of videos to request. Defaults to `1`.
- `enhance_prompt`: Optional. Enable prompt rewriting when supported.
- `generate_audio`: Optional. Generate audio when supported.
- `seed`: Optional. RNG seed.
- `fps`: Optional. Frames per second when supported.
- `poll_interval`: Optional. Seconds between operation polls. Defaults to `10`.
- `timeout`: Optional. Maximum seconds to wait for completion. Defaults to `600`.

### Image-to-Video

```python
from apis import VeoImageToVideo

model = VeoImageToVideo.from_env(model_name="veo-3.1-generate-preview")
result = model.generate(
    image="first-frame.png",
    prompt="The camera slowly pushes in as the lanterns begin to glow.",
    output_path="outputs/veo-image2video.mp4",
    duration_seconds=8,
)

print(result.path)
```

- `image`: Required. A local image path, `gs://` URI, or SDK-compatible `types.Image`.
- `prompt`: Optional. Text prompt for the motion and scene.
- Other generation options match `VeoTextToVideo`.

### Video Extension

```python
from apis import VeoTextToVideo, VeoVideoExtension

generator = VeoTextToVideo.from_env(model_name="veo-3.1-generate-preview")
source = generator.generate(
    prompt="A drone shot flying toward a glass greenhouse in a rainstorm.",
    output_path="outputs/veo-source.mp4",
    aspect_ratio="16:9",
    resolution="720p",
    duration_seconds=4,
)

extension = VeoVideoExtension.from_env(model_name="veo-3.1-generate-preview")
result = extension.generate(
    video=source,
    prompt="Continue the camera movement into a wider establishing shot.",
    output_path="outputs/veo-extension.mp4",
)
```

- `video`: Required. A previously generated Veo video handle, such as `VeoVideoResult`, SDK `types.GeneratedVideo`, or URI-only SDK `types.Video` returned by a Veo generation operation.
- `resolution`: Optional. Defaults to `720p`.

### Errors

- `VeoError`: Raised for wrapper-level errors such as missing `GEMINI_API_KEY`, missing prompts, unsupported inputs, missing generated videos, invalid reference image settings, or save failures.
- `VeoTaskFailedError`: Raised when the Veo operation finishes with an API error.
- `VeoTimeoutError`: Raised when operation polling exceeds the configured timeout.
- Google Gen AI SDK API exceptions are raised directly by the `google-genai` package.
