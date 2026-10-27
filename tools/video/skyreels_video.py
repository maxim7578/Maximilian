"""SkyReels-V3 local video generation (reference-to-video and video extension)."""

from __future__ import annotations

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


# OpenMontage operation -> generate_video.py --task_type
OPERATION_TASKS = {
    "reference_to_video": "reference_to_video",
    "video_extension": "single_shot_extension",
    "shot_switching_extension": "shot_switching_extension",
}


class SkyReelsVideo(BaseTool):
    name = "skyreels_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "skyreels"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED
    runtime = ToolRuntime.LOCAL_GPU

    install_instructions = _skyreels.INSTALL_INSTRUCTIONS
    fallback = "kling_official_video"
    fallback_tools = ["kling_official_video", "seedance_video", "wan_video"]
    agent_skills = ["skyreels-v3"]

    capabilities = list(OPERATION_TASKS)
    supports = {
        "reference_to_video": True,
        "video_extension": True,
        "shot_switching": True,
        "text_to_video": False,
        "image_to_video": False,
        "max_reference_images": _skyreels.MAX_REFERENCE_IMAGES,
        "offline": True,
        "native_audio": False,
        "local_gpu": True,
        "multi_gpu": True,
    }
    best_for = [
        "keeping 1-4 characters, products or backgrounds consistent from reference images",
        "continuing an existing clip 5-30s without a visible seam",
        "cinematic cut-in / cut-out / reverse-shot continuations of an existing clip",
    ]
    not_good_for = [
        "plain text-to-video without reference images",
        "CPU-only or Apple Silicon machines (CUDA + flash-attn required)",
        "quick drafts - 14B weights, minutes per clip",
    ]
    provider_matrix = {
        op: {"tool": "skyreels_video", "task_type": task, "mode": "local_gpu", **_skyreels.TASKS[task]}
        for op, task in OPERATION_TASKS.items()
    }

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Scene description. For shot_switching_extension start with a cut tag such as [ZOOM_IN_CUT].",
            },
            "operation": {
                "type": "string",
                "enum": list(OPERATION_TASKS),
                "default": "reference_to_video",
            },
            "reference_image_paths": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "reference_image_urls": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
            "reference_image_path": {"type": "string"},
            "reference_video_path": {"type": "string", "description": "Clip to extend (video_extension / shot_switching_extension)."},
            "reference_video_url": {"type": "string"},
            "duration": {
                "type": "integer",
                "description": "Seconds. reference_to_video and shot_switching_extension: 1-5, video_extension: 5-30.",
                "default": 5,
            },
            "resolution": {"type": "string", "enum": _skyreels.RESOLUTIONS, "default": "720P"},
            "seed": {"type": "integer", "default": 42},
            "offload": {"type": "boolean", "default": True},
            "low_vram": {"type": "boolean", "default": False, "description": "FP8 weights + block offload for GPUs under 24GB."},
            "num_gpus": {"type": "integer", "default": 1, "description": "> 1 runs xDiT USP via torchrun."},
            "model_id": {"type": "string", "description": "Local weights dir or Hugging Face id; defaults to the script's choice."},
            "timeout_seconds": {"type": "integer", "default": 3600},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=64000, vram_mb=24000, disk_mb=80000, network_required=False)
    retry_policy = RetryPolicy(max_retries=0)
    idempotency_key_fields = ["prompt", "operation", "reference_image_paths", "reference_image_urls", "reference_video_path", "duration", "resolution", "seed"]
    side_effects = ["writes video file to output_path", "may download SkyReels-V3 weights from Hugging Face"]
    user_visible_verification = [
        "Check that every reference subject keeps its identity",
        "For extensions: the clip contains only the new footage - check the seam when joined to the source",
    ]

    def get_status(self) -> ToolStatus:
        return _skyreels.status()

    def is_operation_available(self, operation: str) -> bool:
        return operation in OPERATION_TASKS and self.get_status() == ToolStatus.AVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        duration = int(inputs.get("duration") or 5)
        per_five_seconds = 300.0 if inputs.get("low_vram") else 180.0
        return per_five_seconds * max(1, -(-duration // 5)) / max(1, int(inputs.get("num_gpus", 1) or 1))

    def _references(self, inputs: dict[str, Any]) -> list[str]:
        refs = list(inputs.get("reference_image_paths") or []) + list(inputs.get("reference_image_urls") or [])
        if not refs and inputs.get("reference_image_path"):
            refs = [inputs["reference_image_path"]]
        return [str(r) for r in refs]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        operation = str(inputs.get("operation") or "reference_to_video")
        task_type = OPERATION_TASKS.get(operation)
        if task_type is None:
            return ToolResult(
                success=False,
                error=f"skyreels_video does not support {operation!r}. Supported: {', '.join(OPERATION_TASKS)}",
            )
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="SkyReels-V3 is unavailable. " + self.install_instructions)
        error = _skyreels.validate_common(task_type, inputs)
        if error:
            return ToolResult(success=False, error=error)

        if task_type == "reference_to_video":
            refs = self._references(inputs)
            if not 1 <= len(refs) <= _skyreels.MAX_REFERENCE_IMAGES:
                return ToolResult(success=False, error=f"reference_to_video needs 1-4 reference images, got {len(refs)}")
            missing = _skyreels.missing_local_files(refs)
            if missing:
                return ToolResult(success=False, error=f"Reference image not found: {missing[0]}")
            # generate_video.py splits --ref_imgs on commas.
            if any("," in r for r in refs):
                return ToolResult(success=False, error="Reference image paths/URLs must not contain commas")
            task_args = ["--ref_imgs", ",".join(_skyreels.resolve_media(r) for r in refs)]
        else:
            video = inputs.get("reference_video_path") or inputs.get("reference_video_url")
            if not video:
                return ToolResult(success=False, error=f"{operation} needs reference_video_path or reference_video_url")
            if _skyreels.missing_local_files([str(video)]):
                return ToolResult(success=False, error=f"Input video not found: {video}")
            task_args = ["--input_video", _skyreels.resolve_media(str(video))]

        output_path = Path(inputs.get("output_path") or f"skyreels_{operation}_{int(time.time())}.mp4")
        start = time.time()
        try:
            result = _skyreels.run(
                tool_name=self.name,
                task_type=task_type,
                inputs=inputs,
                task_args=task_args,
                output_path=output_path,
                run_command=self.run_command,
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"SkyReels-V3 {operation} failed: {exc}")
        if result.success:
            result.data["operation"] = operation
            if task_type != "reference_to_video":
                result.data["contains_source_footage"] = False
        result.duration_seconds = round(time.time() - start, 2)
        return result
