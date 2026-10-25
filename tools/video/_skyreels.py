"""Shared runner for the local SkyReels-V3 checkout.

SkyReels-V3 (https://github.com/SkyworkAI/SkyReels-V3) ships as a script repo,
not a pip package, and pins its own torch/diffusers/flash-attn stack.  The
tools therefore never import it: they shell out to ``generate_video.py`` with
the interpreter of whatever environment the user installed it into, inside a
scratch working directory, and move the result to ``output_path``.

``generate_video.py`` writes to ``<cwd>/result/<task_type>/<seed>_<time>.mp4``
(talking avatar: ``..._with_audio.mp4`` after its own ffmpeg mux) and drops
downloaded inputs plus preprocessed audio next to it, so each run gets its own
work directory that is removed afterwards.
"""

from __future__ import annotations

import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Callable

from tools.base_tool import ToolResult, ToolStatus


REPO_URL = "https://github.com/SkyworkAI/SkyReels-V3"

# Task contract mirrored from generate_video.py.  ``fps`` is what the script
# hard-codes when writing the clip; ``max_duration`` is enforced here so a
# bad request fails before a 14B/19B checkpoint is loaded.
TASKS: dict[str, dict[str, Any]] = {
    "reference_to_video": {
        "label": "Reference to Video (14B)",
        "fps": 24,
        "min_duration": 1,
        "max_duration": 5,
        "vram_mb": 40000,
    },
    "single_shot_extension": {
        "label": "Single-shot Video Extension (14B)",
        "fps": 24,
        "min_duration": 5,
        "max_duration": 30,
        "vram_mb": 40000,
    },
    "shot_switching_extension": {
        "label": "Shot-switching Video Extension (14B)",
        "fps": 24,
        "min_duration": 1,
        "max_duration": 5,
        "vram_mb": 40000,
    },
    "talking_avatar": {
        "label": "Talking Avatar (19B)",
        "fps": 25,
        "min_duration": None,
        "max_duration": None,
        "vram_mb": 48000,
    },
}

RESOLUTIONS = ["480P", "540P", "720P"]
MAX_REFERENCE_IMAGES = 4
MAX_AVATAR_AUDIO_SECONDS = 200

INSTALL_INSTRUCTIONS = (
    "Clone SkyReels-V3 into its own environment (it pins torch 2.8 + flash-attn):\n"
    f"  git clone {REPO_URL}\n"
    "  cd SkyReels-V3 && python -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
    "Then point OpenMontage at it in .env:\n"
    "  SKYREELS_V3_PATH=/path/to/SkyReels-V3\n"
    "  SKYREELS_V3_PYTHON=/path/to/SkyReels-V3/.venv/bin/python   # optional, defaults to this interpreter\n"
    "Requires an NVIDIA GPU with CUDA 12.8+. Weights (14B/19B) download from Hugging Face on first use;\n"
    "under 24GB VRAM pass low_vram=true and resolution=540P or 480P."
)


def repo_path() -> Path | None:
    raw = os.environ.get("SKYREELS_V3_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if (path / "generate_video.py").is_file() else None


def python_executable() -> str:
    return os.environ.get("SKYREELS_V3_PYTHON", "").strip() or sys.executable


def status() -> ToolStatus:
    """AVAILABLE only when the checkout, its interpreter and a CUDA driver exist.

    The scripts hard-code ``cuda:<rank>`` devices and flash-attn, so a machine
    without ``nvidia-smi`` cannot run them no matter what is installed.
    """
    if repo_path() is None:
        return ToolStatus.UNAVAILABLE
    interpreter = python_executable()
    if not (Path(interpreter).is_file() or shutil.which(interpreter)):
        return ToolStatus.UNAVAILABLE
    if shutil.which("nvidia-smi") is None:
        return ToolStatus.UNAVAILABLE
    return ToolStatus.AVAILABLE


def validate_common(task_type: str, inputs: dict[str, Any]) -> str | None:
    """Return an error message for invalid shared inputs, else None."""
    if task_type not in TASKS:
        return f"Unknown SkyReels-V3 task {task_type!r}. Supported: {', '.join(TASKS)}"
    resolution = inputs.get("resolution", "720P")
    if resolution not in RESOLUTIONS:
        return f"resolution must be one of {RESOLUTIONS}, got {resolution!r}"
    num_gpus = int(inputs.get("num_gpus", 1) or 1)
    if num_gpus < 1:
        return "num_gpus must be >= 1"
    if num_gpus > 1 and inputs.get("low_vram"):
        return "low_vram cannot be combined with multi-GPU (num_gpus > 1) inference"
    if inputs.get("duration") is not None:
        spec = TASKS[task_type]
        if spec["max_duration"] is None:
            return f"{task_type} takes its length from the driving audio; drop duration"
        duration = int(inputs["duration"])
        if not spec["min_duration"] <= duration <= spec["max_duration"]:
            return (
                f"{task_type} supports duration {spec['min_duration']}-{spec['max_duration']}s, "
                f"got {duration}"
            )
    return None


def resolve_media(value: str) -> str:
    """Absolute path for local files, URLs untouched (the script downloads them)."""
    if value.startswith(("http://", "https://")):
        return value
    return str(Path(value).expanduser().resolve())


def missing_local_files(values: list[str]) -> list[str]:
    return [v for v in values if not v.startswith(("http://", "https://")) and not Path(v).is_file()]


def build_command(task_type: str, inputs: dict[str, Any], task_args: list[str]) -> list[str]:
    script = str(repo_path() / "generate_video.py")
    num_gpus = int(inputs.get("num_gpus", 1) or 1)
    if num_gpus > 1:
        cmd = [python_executable(), "-m", "torch.distributed.run", f"--nproc_per_node={num_gpus}", script]
    else:
        cmd = [python_executable(), script]

    cmd += [
        "--task_type", task_type,
        "--prompt", str(inputs["prompt"]),
        "--resolution", inputs.get("resolution", "720P"),
        "--seed", str(int(inputs.get("seed", 42))),
    ]
    if inputs.get("duration") is not None:
        cmd += ["--duration", str(int(inputs["duration"]))]
    model_id = str(inputs.get("model_id") or "")
    if model_id:
        # A local weights dir must survive the cwd switch; a hub id passes through.
        local = Path(model_id).expanduser()
        cmd += ["--model_id", str(local.resolve()) if local.exists() else model_id]
    if num_gpus > 1:
        cmd.append("--use_usp")
    if inputs.get("low_vram"):
        cmd.append("--low_vram")
    elif inputs.get("offload", True):
        cmd.append("--offload")
    return cmd + task_args


def _find_output(work_dir: Path, task_type: str) -> Path | None:
    result_dir = work_dir / "result" / task_type
    pattern = "*_with_audio.mp4" if task_type == "talking_avatar" else "*.mp4"
    clips = sorted(result_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return clips[0] if clips else None


def run(
    *,
    tool_name: str,
    task_type: str,
    inputs: dict[str, Any],
    task_args: list[str],
    output_path: Path,
    run_command: Callable[..., Any],
) -> ToolResult:
    """Run one generate_video.py job and move its clip to ``output_path``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = output_path.parent / f".skyreels_{uuid.uuid4().hex[:8]}"
    work_dir.mkdir(parents=True)
    cmd = build_command(task_type, inputs, task_args)
    try:
        completed = run_command(cmd, cwd=work_dir, timeout=int(inputs.get("timeout_seconds", 3600)))
        produced = _find_output(work_dir, task_type)
        if produced is None:
            tail = "\n".join(((completed.stdout or "") + (completed.stderr or "")).splitlines()[-15:])
            hint = " (the script's ffmpeg audio mux failed)" if task_type == "talking_avatar" else ""
            return ToolResult(
                success=False,
                error=f"SkyReels-V3 finished without writing a clip{hint}. Last output:\n{tail}",
            )
        shutil.move(str(produced), str(output_path))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    seed = int(inputs.get("seed", 42))
    return ToolResult(
        success=True,
        data={
            "provider": "skyreels",
            "tool": tool_name,
            "task_type": task_type,
            "model": TASKS[task_type]["label"],
            "model_id": inputs.get("model_id") or "generate_video.py default",
            "resolution": inputs.get("resolution", "720P"),
            "fps": TASKS[task_type]["fps"],
            "output": str(output_path),
            "output_path": str(output_path),
            "format": "mp4",
        },
        artifacts=[str(output_path)],
        seed=seed,
        model=f"skyreels-v3/{task_type}",
        cost_usd=0.0,
    )
