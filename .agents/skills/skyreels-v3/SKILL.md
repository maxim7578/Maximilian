---
name: skyreels-v3
description: SkyReels-V3 local video generation (Skywork, open weights) - multi-reference video from 1-4 images, single-shot and shot-switching video extension, and audio-driven talking avatars up to 200s. Use before calling `skyreels_video` or `skyreels_avatar`, when a brief needs subject consistency across references, continuing an existing clip, cinematic cut-in/cut-out continuations, or a lip-synced presenter from one portrait.
---

# SkyReels-V3

Open-weights multimodal video model from Skywork, built on Wan 2.1. Runs locally from a
clone of https://github.com/SkyworkAI/SkyReels-V3; OpenMontage shells out to its
`generate_video.py` and never imports it (the repo pins its own torch 2.8 / flash-attn stack).

| OpenMontage tool | Operation | Script task | Weights | Length | FPS |
|---|---|---|---|---|---|
| `skyreels_video` | `reference_to_video` | `reference_to_video` | R2V 14B | 1-5 s (5 s recommended) | 24 |
| `skyreels_video` | `video_extension` | `single_shot_extension` | V2V 14B | 5-30 s | 24 |
| `skyreels_video` | `shot_switching_extension` | `shot_switching_extension` | V2V 14B | max 5 s | 24 |
| `skyreels_avatar` | - | `talking_avatar` | A2V 19B | follows audio, max 200 s | 25 |

## Setup

```bash
git clone https://github.com/SkyworkAI/SkyReels-V3
cd SkyReels-V3 && python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

`.env`:

```
SKYREELS_V3_PATH=/path/to/SkyReels-V3
SKYREELS_V3_PYTHON=/path/to/SkyReels-V3/.venv/bin/python
```

Needs an NVIDIA GPU (CUDA 12.8+). Weights download from Hugging Face on first run
(tens of GB per task). The tools report `unavailable` without the checkout, the interpreter
or `nvidia-smi` - there is no CPU or Apple Silicon path.

## Memory and speed

- Default: `offload=true`, `resolution="720P"`.
- Under 24 GB VRAM: `low_vram=true` (FP8 weights + block offload) and `resolution="540P"` or `"480P"`.
- Multi-GPU: `num_gpus=N` runs `torchrun --nproc_per_node=N ... --use_usp`. Not combinable with `low_vram`.
- Every call loads a 14B/19B checkpoint. Generate one sample, get approval, then batch.
- Cost is $0 (local), but runtime is minutes per 5 s clip. Say so in the proposal.

## Reference to Video

1-4 reference images (characters, objects, background) + a prompt. The **first reference sets
the output aspect ratio** - order the references so the image with the target framing comes first
(supported ratios: 1:1, 3:4, 4:3, 16:9, 9:16). `aspect_ratio` passed by `video_selector` is ignored.

Prompting:
- Describe every reference subject in the prompt by its visible traits ("girl with teal pigtails and
  white polo shirt"), so the model can bind text to image. Unnamed references drift.
- State the relationship and the action ("two girls talking across a cluttered table"), then the
  setting, then light and lens ("under flickering fluorescent light, high-quality cinematic shot").
- One action per clip. The model keeps identity better than it handles plot.
- Reference images should show the subject alone on a clean background where possible; the model
  composes them into the scene itself.

```python
registry.get("skyreels_video").execute({
    "operation": "reference_to_video",
    "reference_image_paths": ["projects/<id>/assets/images/hero.png", "projects/<id>/assets/images/mascot.png"],
    "prompt": "...",
    "duration": 5,
    "output_path": "projects/<id>/assets/video/scene-03.mp4",
})
```

## Video Extension

`reference_video_path` + prompt. The output contains **only the new footage**, not the source clip.
The edit stage must join source + extension (`video_stitch`), and the asset manifest should
record both files.

- `video_extension` (single shot, 5-30 s): describe how the existing action continues. Do not
  re-describe the scene from scratch; continuity comes from the last frames of the source.
- `shot_switching_extension` (max 5 s): the next shot after a cut. Start the prompt with a cut tag,
  then describe the new framing in full:

  ```
  [ZOOM_IN_CUT] The scene cuts from a medium shot of the man walking in the park to a close-up of
  his face and upper torso. He wears dark sunglasses ... The lighting is natural and bright.
  ```

  Documented tags: `[ZOOM_IN_CUT]` (cut-in), `[ZOOM_OUT_CUT]` (cut-out). The model also handles
  shot/reverse shot, multi-angle and cut-away when the prompt names them explicitly; describe the
  new camera position and what is now in frame.

## Talking Avatar

`skyreels_avatar` with `image_path` (jpg/png/gif/bmp) + `audio_path` (mp3/wav, max 200 s, one
speaker). Works with real people, cartoon, animal and stylized characters; many languages.

- Prompt sets demeanour and camera: "A woman is giving a speech. She is confident, poised and
  joyful. Use a static shot." Say "static shot" for presenter work; camera moves (crane up, slow
  push-in) are honoured but cost lip-sync stability.
- The portrait becomes the first frame: frame it the way the shot should look (head-and-shoulders,
  eyes on camera, mouth closed, neutral background).
- Narration longer than 200 s: render per scene from the script sections, not one long call.
- The output already has the audio muxed in. Do not mix the narration a second time in edit.

## Review checklist

- Identity: each reference subject / the portrait is recognisable in every frame.
- Extension seam: play source + extension back to back and look at the join.
- Lip sync: check the last third of long avatar clips, where drift shows first.
- Record `seed`, `task_type`, `resolution` and `model_id` from `ToolResult` in the asset manifest.
