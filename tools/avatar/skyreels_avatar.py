"""SkyReels-V3 talking avatar: one portrait plus one voice track to a lip-synced clip."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)
from tools.video import _skyreels


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
AUDIO_SUFFIXES = {".mp3", ".wav"}


def _audio_seconds(path: str) -> float | None:
    """Probe local audio length; None when ffprobe is missing or the file is remote."""
    if path.startswith(("http://", "https://")) or shutil.which("ffprobe") is None:
        return None
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(json.loads(probe.stdout)["format"]["duration"])
    except (subprocess.SubprocessError, KeyError, ValueError):
        return None


class SkyReelsAvatar(BaseTool):
    name = "skyreels_avatar"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "avatar"
    provider = "skyreels"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.LOCAL_GPU

    install_instructions = _skyreels.INSTALL_INSTRUCTIONS
    fallback = "talking_head"
    fallback_tools = ["talking_head", "kling_avatar", "heygen_avatar"]
    agent_skills = ["skyreels-v3"]

    capabilities = ["photo_to_video", "audio_driven_animation", "talking_avatar"]
    supports = {
        "lip_sync": True,
        "max_audio_seconds": _skyreels.MAX_AVATAR_AUDIO_SECONDS,
        "stylized_characters": True,
        "prompted_camera": True,
        "offline": True,
        "local_gpu": True,
        "multi_gpu": True,
    }
    best_for = [
        "presenter clips up to 200s from a single portrait and a narration track",
        "cartoon, animal and stylized characters, not only real faces",
        "prompt-directed expression and camera (e.g. 'static shot', 'slow crane up')",
    ]
    not_good_for = [
        "more than one voice track (one speaker per call)",
        "CPU-only or Apple Silicon machines (CUDA + flash-attn required)",
    ]

    input_schema = {
        "type": "object",
        "required": ["image_path", "audio_path"],
        "properties": {
            "image_path": {"type": "string", "description": "Portrait / first frame (jpg, png, gif, bmp) - local path or URL."},
            "audio_path": {"type": "string", "description": "Driving voice track (mp3, wav), at most 200s - local path or URL."},
            "prompt": {
                "type": "string",
                "default": "A person is speaking to the camera. Use a static shot.",
                "description": "Demeanour and camera direction for the clip.",
            },
            "resolution": {"type": "string", "enum": _skyreels.RESOLUTIONS, "default": "720P"},
            "seed": {"type": "integer", "default": 42},
            "offload": {"type": "boolean", "default": True},
            "low_vram": {"type": "boolean", "default": False},
            "num_gpus": {"type": "integer", "default": 1},
            "model_id": {"type": "string"},
            "timeout_seconds": {"type": "integer", "default": 7200},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=64000, vram_mb=24000, disk_mb=90000, network_required=False)
    retry_policy = RetryPolicy(max_retries=0)
    idempotency_key_fields = ["image_path", "audio_path", "prompt", "resolution", "seed"]
    side_effects = ["writes video file to output_path", "may download SkyReels-V3 weights from Hugging Face"]
    user_visible_verification = [
        "Watch the clip for lip-sync drift, especially in the last third",
        "Check that the face keeps the portrait's identity",
    ]

    def get_status(self) -> ToolStatus:
        return _skyreels.status()

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        seconds = _audio_seconds(str(inputs.get("audio_path", ""))) or 30.0
        return (120.0 + seconds * 20.0) / max(1, int(inputs.get("num_gpus", 1) or 1))

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="SkyReels-V3 is unavailable. " + self.install_instructions)
        error = _skyreels.validate_common("talking_avatar", inputs)
        if error:
            return ToolResult(success=False, error=error)

        image = str(inputs["image_path"])
        audio = str(inputs["audio_path"])
        missing = _skyreels.missing_local_files([image, audio])
        if missing:
            return ToolResult(success=False, error=f"Input not found: {missing[0]}")
        if Path(image.split("?")[0]).suffix.lower() not in IMAGE_SUFFIXES:
            return ToolResult(success=False, error=f"Portrait must be one of {sorted(IMAGE_SUFFIXES)}: {image}")
        if Path(audio.split("?")[0]).suffix.lower() not in AUDIO_SUFFIXES:
            return ToolResult(success=False, error=f"Audio must be mp3 or wav: {audio}")
        seconds = _audio_seconds(audio)
        if seconds is not None and seconds > _skyreels.MAX_AVATAR_AUDIO_SECONDS:
            return ToolResult(
                success=False,
                error=f"Audio is {seconds:.0f}s; SkyReels-V3 talking avatar accepts at most "
                f"{_skyreels.MAX_AVATAR_AUDIO_SECONDS}s - split the narration per scene",
            )

        params = {**inputs, "prompt": inputs.get("prompt") or self.input_schema["properties"]["prompt"]["default"]}
        task_args = ["--input_image", _skyreels.resolve_media(image), "--input_audio", _skyreels.resolve_media(audio)]
        if inputs.get("output_path"):
            output_path = Path(inputs["output_path"])
        elif not image.startswith(("http://", "https://")):
            output_path = Path(image).with_name(f"{Path(image).stem}_skyreels_avatar.mp4")
        else:
            output_path = Path(f"skyreels_avatar_{int(time.time())}.mp4")

        start = time.time()
        try:
            result = _skyreels.run(
                tool_name=self.name,
                task_type="talking_avatar",
                inputs=params,
                task_args=task_args,
                output_path=output_path,
                run_command=self.run_command,
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"SkyReels-V3 talking avatar failed: {exc}")
        if result.success:
            result.data.update({"image": image, "audio": audio, "audio_seconds": seconds})
        result.duration_seconds = round(time.time() - start, 2)
        return result
