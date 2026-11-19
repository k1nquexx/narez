from __future__ import annotations

import subprocess
import urllib.request
from pathlib import Path

from backend.core.hardware import find_binary
from backend.core.paths import (
    FONTS_DIR,
    MUSIC_DIR,
    PRIMARY_FONT_FILE,
    SECONDARY_FONT_FILE,
    ensure_directories,
)

FONT_URLS: dict[str, str] = {
    PRIMARY_FONT_FILE: "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-ExtraBold.ttf",
    SECONDARY_FONT_FILE: "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-SemiBold.ttf",
}

DEFAULT_MUSIC_FILE: str = "ambient_pulse.mp3"


def ensure_fonts() -> dict[str, Path]:
    """Download bundled Cyrillic+Latin Montserrat TTF fonts into assets/fonts/ if missing."""
    ensure_directories()
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}

    for filename, url in FONT_URLS.items():
        target = FONTS_DIR / filename
        if not target.exists() or target.stat().st_size < 10_000:
            print(f"[assets] Downloading font {filename}...")
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ShortsFactory/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            target.write_bytes(data)
            print(f"[assets] Saved {target} ({len(data)} bytes)")
        result[filename] = target
    return result


def inspect_font_names() -> dict[str, tuple[str, str]]:
    """Inspect exact TrueType family/style names via Pillow so libass matches reliably."""
    from PIL import ImageFont

    info: dict[str, tuple[str, str]] = {}
    for filename in FONT_URLS:
        path = FONTS_DIR / filename
        if path.is_file():
            font = ImageFont.truetype(str(path), 48)
            info[filename] = font.getname()
    return info


def ensure_default_music() -> Path | None:
    """
    Generate a clean 65-second dark-ambient background music track via FFmpeg
    if assets/music/ has no audio files yet, so auto-ducking works out of the box.
    """
    ensure_directories()
    existing = [
        p
        for p in MUSIC_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"}
    ]
    if existing:
        return existing[0]

    ffmpeg_path = find_binary("ffmpeg")
    if not ffmpeg_path:
        print("[assets] ffmpeg not found yet; skipping default ambient music generation.")
        return None

    target = MUSIC_DIR / DEFAULT_MUSIC_FILE
    # Subtle minor ambient pad + soft rhythmic pulse (low-passed so voice stays crystal clear)
    expr = (
        "0.18*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.25*t))"
        "+0.12*sin(2*PI*164.81*t)"
        "+0.10*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.5*t))"
        "+0.08*sin(2*PI*261.63*t)"
    )
    cmd = [
        ffmpeg_path,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"aevalsrc='{expr}':s=44100:d=65",
        "-af",
        "lowpass=f=750,aecho=0.8:0.88:60:0.3,afade=t=in:st=0:d=2,afade=t=out:st=62:d=3,volume=0.8",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(target),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        print(f"[assets] Warning: could not generate default ambient track: {proc.stderr[:300]}")
        return None
    print(f"[assets] Generated default ambient music: {target}")
    return target


def ensure_all_assets() -> None:
    ensure_fonts()
    names = inspect_font_names()
    for fname, (family, style) in names.items():
        print(f"[assets] Font {fname}: family={family!r}, style={style!r}")
    ensure_default_music()


if __name__ == "__main__":
    ensure_all_assets()
