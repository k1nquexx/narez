from __future__ import annotations

import gc
import importlib.util
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class HardwareInfo:
    os_name: str
    python_version: str
    ffmpeg_path: str | None
    ffprobe_path: str | None
    cuda_available: bool
    gpu_name: str | None
    vram_gb: float | None
    nvenc_available: bool
    video_encoder: str
    whisper_device: str
    whisper_compute_type: str
    diffusers_available: bool
    torch_available: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def find_binary(name: str) -> str | None:
    """Locate an executable on PATH or common user-space directories (~/.local/bin)."""
    found = shutil.which(name)
    if found:
        return found

    home_bin = Path.home() / ".local" / "bin"
    for candidate_name in (name, f"{name}.exe"):
        candidate = home_bin / candidate_name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _probe_nvenc(ffmpeg_path: str | None) -> bool:
    """
    Verify h264_nvenc actually works by encoding a 1-frame dummy video.
    Checking `-encoders` alone is insufficient because FFmpeg lists NVENC even
    when no NVIDIA driver/GPU is present.
    """
    if not ffmpeg_path:
        return False

    cmd = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=256x256:d=0.1",
        "-vframes",
        "1",
        "-c:v",
        "h264_nvenc",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _detect_cuda() -> tuple[bool, bool, str | None, float | None]:
    """Detect CUDA via PyTorch (preferred) or ctranslate2."""
    torch_available = importlib.util.find_spec("torch") is not None
    if torch_available:
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                vram_gb = round(props.total_memory / (1024**3), 2)
                return True, True, str(props.name), vram_gb
        except Exception:
            pass

    # Fallback check via ctranslate2 (bundled with faster-whisper)
    try:
        import ctranslate2  # type: ignore

        if ctranslate2.get_cuda_device_count() > 0:
            return torch_available, True, "NVIDIA CUDA Device", None
    except Exception:
        pass

    return torch_available, False, None, None


@lru_cache(maxsize=1)
def detect_hardware() -> HardwareInfo:
    """Detect FFmpeg/FFprobe, CUDA GPU, NVENC hardware encoder, and AI runtime support."""
    ffmpeg_path = find_binary("ffmpeg")
    ffprobe_path = find_binary("ffprobe")
    torch_available, cuda_available, gpu_name, vram_gb = _detect_cuda()
    nvenc_available = _probe_nvenc(ffmpeg_path)
    video_encoder = "h264_nvenc" if nvenc_available else "libx264"

    whisper_device = "cuda" if cuda_available else "cpu"
    whisper_compute_type = "float16" if cuda_available else "int8"
    diffusers_available = importlib.util.find_spec("diffusers") is not None

    return HardwareInfo(
        os_name=f"{platform.system()} {platform.release()}",
        python_version=platform.python_version(),
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        cuda_available=cuda_available,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        nvenc_available=nvenc_available,
        video_encoder=video_encoder,
        whisper_device=whisper_device,
        whisper_compute_type=whisper_compute_type,
        diffusers_available=diffusers_available,
        torch_available=torch_available,
    )


def cleanup_vram() -> None:
    """Release Python garbage and clear CUDA memory caches if PyTorch CUDA is available."""
    gc.collect()
    if importlib.util.find_spec("torch") is not None:
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass


if __name__ == "__main__":
    import json

    detect_hardware.cache_clear()
    info = detect_hardware()
    print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
