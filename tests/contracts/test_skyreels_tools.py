"""Vertragstests für die lokalen SkyReels-V3-Tools (skyreels_video, skyreels_avatar).

Kein Test lädt Gewichte oder braucht eine GPU: Das Repo wird als leeres
Verzeichnis mit `generate_video.py` vorgetäuscht, `nvidia-smi` per Monkeypatch
gefunden und `run_command` durch eine Attrappe ersetzt, die die Ausgabedatei
dort anlegt, wo das echte Skript sie schreibt.

Ausführen: pytest tests/contracts/test_skyreels_tools.py -v
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.avatar import skyreels_avatar as avatar_module
from tools.avatar.skyreels_avatar import SkyReelsAvatar
from tools.base_tool import BaseTool, ToolRuntime, ToolStatus
from tools.video import _skyreels
from tools.video.skyreels_video import SkyReelsVideo

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def skyreels_repo(tmp_path, monkeypatch):
    """Täuscht einen installierten SkyReels-V3-Checkout auf einer CUDA-Maschine vor."""
    repo = tmp_path / "SkyReels-V3"
    repo.mkdir()
    (repo / "generate_video.py").write_text("# Attrappe\n")
    monkeypatch.setenv("SKYREELS_V3_PATH", str(repo))
    monkeypatch.delenv("SKYREELS_V3_PYTHON", raising=False)
    real_which = _skyreels.shutil.which
    monkeypatch.setattr(
        _skyreels.shutil, "which", lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else real_which(name)
    )
    return repo


def _fake_runner(calls, *, filename="42_2026-01-01_00-00-00.mp4"):
    """Ersetzt run_command: merkt sich den Befehl und schreibt die Ausgabe wie generate_video.py."""

    def run(cmd, cwd=None, timeout=None):
        task_type = cmd[cmd.index("--task_type") + 1]
        out_dir = Path(cwd) / "result" / task_type
        out_dir.mkdir(parents=True, exist_ok=True)
        if filename:
            (out_dir / filename).write_bytes(b"mp4")
        calls.append({"cmd": cmd, "cwd": Path(cwd), "timeout": timeout})
        return subprocess.CompletedProcess(cmd, 0, stdout="fertig\n", stderr="")

    return run


def _image(tmp_path, name="ref.png"):
    path = tmp_path / name
    path.write_bytes(b"png")
    return str(path)


def _arg(cmd, flag):
    return cmd[cmd.index(flag) + 1]


class TestVertrag:
    @pytest.mark.parametrize("tool_cls", [SkyReelsVideo, SkyReelsAvatar])
    def test_erbt_von_basetool_und_laeuft_lokal_auf_gpu(self, tool_cls):
        tool = tool_cls()
        assert isinstance(tool, BaseTool)
        assert tool.runtime == ToolRuntime.LOCAL_GPU
        assert tool.provider == "skyreels"
        assert tool.estimate_cost({}) == 0.0

    def test_capabilities_passen_zum_zweck(self):
        assert SkyReelsVideo().capability == "video_generation"
        assert SkyReelsAvatar().capability == "avatar"

    @pytest.mark.parametrize("tool_cls", [SkyReelsVideo, SkyReelsAvatar])
    def test_layer_3_skill_existiert(self, tool_cls):
        for skill in tool_cls().agent_skills:
            assert (REPO_ROOT / ".agents" / "skills" / skill / "SKILL.md").is_file()

    def test_registry_findet_beide_tools(self, isolated_tool_registry):
        isolated_tool_registry.discover()
        assert isolated_tool_registry.get("skyreels_video") is not None
        assert isolated_tool_registry.get("skyreels_avatar") is not None


class TestStatus:
    def test_ohne_repo_pfad_nicht_verfuegbar(self, monkeypatch):
        monkeypatch.delenv("SKYREELS_V3_PATH", raising=False)
        assert SkyReelsVideo().get_status() == ToolStatus.UNAVAILABLE
        assert SkyReelsAvatar().get_status() == ToolStatus.UNAVAILABLE

    def test_verzeichnis_ohne_generate_video_zaehlt_nicht(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKYREELS_V3_PATH", str(tmp_path))
        assert SkyReelsVideo().get_status() == ToolStatus.UNAVAILABLE

    def test_ohne_nvidia_treiber_nicht_verfuegbar(self, skyreels_repo, monkeypatch):
        monkeypatch.setattr(_skyreels.shutil, "which", lambda name: None)
        assert SkyReelsVideo().get_status() == ToolStatus.UNAVAILABLE

    def test_fehlender_interpreter_macht_tool_unverfuegbar(self, skyreels_repo, monkeypatch):
        monkeypatch.setenv("SKYREELS_V3_PYTHON", str(skyreels_repo / "gibt-es-nicht" / "python"))
        assert SkyReelsVideo().get_status() == ToolStatus.UNAVAILABLE

    def test_mit_repo_und_gpu_verfuegbar(self, skyreels_repo):
        assert SkyReelsVideo().get_status() == ToolStatus.AVAILABLE
        assert SkyReelsAvatar().get_status() == ToolStatus.AVAILABLE

    def test_ohne_installation_kommt_installationshinweis(self, monkeypatch):
        monkeypatch.delenv("SKYREELS_V3_PATH", raising=False)
        result = SkyReelsVideo().execute({"prompt": "x", "reference_image_paths": ["a.png"]})
        assert not result.success
        assert "SKYREELS_V3_PATH" in result.error


class TestSelectorRouting:
    def test_kein_text_to_video_angeboten(self, skyreels_repo):
        tool = SkyReelsVideo()
        assert not tool.is_operation_available("text_to_video")
        assert not tool.is_operation_available("image_to_video")
        assert tool.is_operation_available("reference_to_video")
        assert tool.supports["reference_to_video"] is True

    def test_selector_waehlt_skyreels_nicht_fuer_text_to_video(self, skyreels_repo):
        from tools.video.video_selector import VideoSelector

        tool = SkyReelsVideo()
        candidates = VideoSelector()._filter_candidates({"operation": "text_to_video"}, [tool])
        assert tool not in candidates

    def test_selector_beruecksichtigt_skyreels_fuer_referenzvideo(self, skyreels_repo):
        from tools.video.video_selector import VideoSelector

        tool = SkyReelsVideo()
        candidates = VideoSelector()._filter_candidates({"operation": "reference_to_video"}, [tool])
        assert tool in candidates


class TestReferenceToVideo:
    def test_baut_befehl_und_verschiebt_ausgabe(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        refs = [_image(tmp_path, "a.png"), _image(tmp_path, "b.png")]
        out = tmp_path / "projects" / "demo" / "assets" / "video" / "scene-01.mp4"

        result = tool.execute({"prompt": "Zwei Figuren reden", "reference_image_paths": refs, "output_path": str(out)})

        assert result.success, result.error
        assert out.read_bytes() == b"mp4"
        cmd = calls[0]["cmd"]
        assert cmd[1] == str(skyreels_repo / "generate_video.py")
        assert _arg(cmd, "--task_type") == "reference_to_video"
        assert _arg(cmd, "--ref_imgs") == ",".join(str(Path(r).resolve()) for r in refs)
        assert _arg(cmd, "--resolution") == "720P"
        assert "--offload" in cmd
        assert result.seed == 42
        assert result.data["fps"] == 24
        assert not calls[0]["cwd"].exists(), "Arbeitsverzeichnis muss aufgeräumt werden"

    def test_urls_werden_unveraendert_durchgereicht(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        url = "https://example.com/held.png"
        result = tool.execute({"prompt": "x", "reference_image_urls": [url], "output_path": str(tmp_path / "o.mp4")})
        assert result.success, result.error
        assert _arg(calls[0]["cmd"], "--ref_imgs") == url

    def test_mehr_als_vier_referenzen_abgelehnt(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        refs = [_image(tmp_path, f"{i}.png") for i in range(5)]
        result = tool.execute({"prompt": "x", "reference_image_paths": refs})
        assert not result.success
        assert "1-4" in result.error
        assert calls == []

    def test_ohne_referenz_abgelehnt(self, skyreels_repo):
        result = SkyReelsVideo().execute({"prompt": "x"})
        assert not result.success
        assert "got 0" in result.error

    def test_fehlende_bilddatei_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsVideo().execute({"prompt": "x", "reference_image_paths": [str(tmp_path / "fehlt.png")]})
        assert not result.success
        assert "not found" in result.error

    def test_komma_im_pfad_abgelehnt(self, skyreels_repo, tmp_path):
        ref = _image(tmp_path, "a,b.png")
        result = SkyReelsVideo().execute({"prompt": "x", "reference_image_paths": [ref]})
        assert not result.success
        assert "commas" in result.error

    def test_dauer_ueber_fuenf_sekunden_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsVideo().execute({"prompt": "x", "reference_image_paths": [_image(tmp_path)], "duration": 6})
        assert not result.success
        assert "1-5" in result.error

    def test_unbekannte_operation_abgelehnt(self, skyreels_repo):
        result = SkyReelsVideo().execute({"prompt": "x", "operation": "text_to_video"})
        assert not result.success
        assert "does not support" in result.error

    def test_skript_ohne_ausgabe_liefert_fehler_mit_log(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls, filename=None)
        result = tool.execute({"prompt": "x", "reference_image_paths": [_image(tmp_path)], "output_path": str(tmp_path / "o.mp4")})
        assert not result.success
        assert "fertig" in result.error
        assert not calls[0]["cwd"].exists()


class TestVideoExtension:
    def test_verlaengerung_nutzt_single_shot_task(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        source = _image(tmp_path, "quelle.mp4")
        result = tool.execute({
            "prompt": "Er geht weiter",
            "operation": "video_extension",
            "reference_video_path": source,
            "duration": "20",
            "output_path": str(tmp_path / "ext.mp4"),
        })
        assert result.success, result.error
        cmd = calls[0]["cmd"]
        assert _arg(cmd, "--task_type") == "single_shot_extension"
        assert _arg(cmd, "--input_video") == str(Path(source).resolve())
        assert _arg(cmd, "--duration") == "20"
        assert result.data["contains_source_footage"] is False

    def test_verlaengerung_ueber_30_sekunden_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsVideo().execute({
            "prompt": "x", "operation": "video_extension",
            "reference_video_path": _image(tmp_path, "q.mp4"), "duration": 31,
        })
        assert not result.success
        assert "5-30" in result.error

    def test_shot_switching_hoechstens_fuenf_sekunden(self, skyreels_repo, tmp_path):
        result = SkyReelsVideo().execute({
            "prompt": "[ZOOM_IN_CUT] Nahaufnahme", "operation": "shot_switching_extension",
            "reference_video_path": _image(tmp_path, "q.mp4"), "duration": 8,
        })
        assert not result.success
        assert "1-5" in result.error

    def test_verlaengerung_ohne_quellvideo_abgelehnt(self, skyreels_repo):
        result = SkyReelsVideo().execute({"prompt": "x", "operation": "video_extension"})
        assert not result.success
        assert "reference_video_path" in result.error


class TestSpeicherUndMultiGpu:
    def test_low_vram_ersetzt_offload(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        result = tool.execute({
            "prompt": "x", "reference_image_paths": [_image(tmp_path)],
            "low_vram": True, "resolution": "540P", "output_path": str(tmp_path / "o.mp4"),
        })
        assert result.success, result.error
        cmd = calls[0]["cmd"]
        assert "--low_vram" in cmd
        assert "--offload" not in cmd
        assert _arg(cmd, "--resolution") == "540P"

    def test_mehrere_gpus_starten_torchrun_mit_usp(self, skyreels_repo, tmp_path):
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        result = tool.execute({
            "prompt": "x", "reference_image_paths": [_image(tmp_path)],
            "num_gpus": 4, "output_path": str(tmp_path / "o.mp4"),
        })
        assert result.success, result.error
        cmd = calls[0]["cmd"]
        assert cmd[1:4] == ["-m", "torch.distributed.run", "--nproc_per_node=4"]
        assert "--use_usp" in cmd

    def test_low_vram_mit_mehreren_gpus_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsVideo().execute({
            "prompt": "x", "reference_image_paths": [_image(tmp_path)], "num_gpus": 2, "low_vram": True,
        })
        assert not result.success
        assert "low_vram" in result.error

    def test_unbekannte_aufloesung_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsVideo().execute({"prompt": "x", "reference_image_paths": [_image(tmp_path)], "resolution": "1080P"})
        assert not result.success
        assert "resolution" in result.error

    def test_eigener_interpreter_wird_verwendet(self, skyreels_repo, tmp_path, monkeypatch):
        interpreter = tmp_path / "venv-python"
        interpreter.write_text("")
        monkeypatch.setenv("SKYREELS_V3_PYTHON", str(interpreter))
        calls = []
        tool = SkyReelsVideo()
        tool.run_command = _fake_runner(calls)
        result = tool.execute({"prompt": "x", "reference_image_paths": [_image(tmp_path)], "output_path": str(tmp_path / "o.mp4")})
        assert result.success, result.error
        assert calls[0]["cmd"][0] == str(interpreter)


class TestTalkingAvatar:
    def test_nimmt_clip_mit_tonspur(self, skyreels_repo, tmp_path, monkeypatch):
        monkeypatch.setattr(avatar_module, "_audio_seconds", lambda path: 12.0)
        calls = []
        tool = SkyReelsAvatar()
        tool.run_command = _fake_runner(calls, filename="42_2026-01-01_00-00-00_with_audio.mp4")
        image = _image(tmp_path, "portrait.png")
        audio = _image(tmp_path, "sprecher.wav")
        out = tmp_path / "avatar.mp4"

        result = tool.execute({"image_path": image, "audio_path": audio, "output_path": str(out)})

        assert result.success, result.error
        assert out.exists()
        cmd = calls[0]["cmd"]
        assert _arg(cmd, "--task_type") == "talking_avatar"
        assert _arg(cmd, "--input_image") == str(Path(image).resolve())
        assert _arg(cmd, "--input_audio") == str(Path(audio).resolve())
        assert "static shot" in _arg(cmd, "--prompt")
        assert "--duration" not in cmd
        assert result.data["fps"] == 25
        assert result.data["audio_seconds"] == 12.0

    def test_ohne_tonspur_clip_fehler(self, skyreels_repo, tmp_path, monkeypatch):
        monkeypatch.setattr(avatar_module, "_audio_seconds", lambda path: 12.0)
        tool = SkyReelsAvatar()
        tool.run_command = _fake_runner([], filename="42_stumm.mp4")
        result = tool.execute({
            "image_path": _image(tmp_path, "p.png"), "audio_path": _image(tmp_path, "a.mp3"),
            "output_path": str(tmp_path / "o.mp4"),
        })
        assert not result.success
        assert "ffmpeg" in result.error

    def test_audio_ueber_200_sekunden_abgelehnt(self, skyreels_repo, tmp_path, monkeypatch):
        monkeypatch.setattr(avatar_module, "_audio_seconds", lambda path: 201.0)
        calls = []
        tool = SkyReelsAvatar()
        tool.run_command = _fake_runner(calls)
        result = tool.execute({"image_path": _image(tmp_path, "p.png"), "audio_path": _image(tmp_path, "a.mp3")})
        assert not result.success
        assert "200s" in result.error
        assert calls == []

    def test_falsches_audioformat_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsAvatar().execute({"image_path": _image(tmp_path, "p.png"), "audio_path": _image(tmp_path, "a.ogg")})
        assert not result.success
        assert "mp3 or wav" in result.error

    def test_falsches_bildformat_abgelehnt(self, skyreels_repo, tmp_path):
        result = SkyReelsAvatar().execute({"image_path": _image(tmp_path, "p.webp"), "audio_path": _image(tmp_path, "a.wav")})
        assert not result.success
        assert "Portrait" in result.error

    def test_standardausgabe_neben_dem_portrait(self, skyreels_repo, tmp_path, monkeypatch):
        monkeypatch.setattr(avatar_module, "_audio_seconds", lambda path: 5.0)
        tool = SkyReelsAvatar()
        tool.run_command = _fake_runner([], filename="42_x_with_audio.mp4")
        image = _image(tmp_path, "portrait.png")
        result = tool.execute({"image_path": image, "audio_path": _image(tmp_path, "a.wav")})
        assert result.success, result.error
        assert result.data["output"] == str(tmp_path / "portrait_skyreels_avatar.mp4")


def test_pipeline_avatar_spokesperson_kennt_skyreels_avatar():
    from lib.pipeline_loader import load_pipeline

    manifest = load_pipeline("avatar-spokesperson")
    stages = {stage["name"]: stage for stage in manifest["stages"]}
    assert "skyreels_avatar" in stages["assets"]["tools_available"]
