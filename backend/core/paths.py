from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path, PurePath

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR: Path = BASE_DIR / "backend"
ASSETS_DIR: Path = BASE_DIR / "assets"
BACKGROUNDS_DIR: Path = ASSETS_DIR / "backgrounds"
MUSIC_DIR: Path = ASSETS_DIR / "music"
FONTS_DIR: Path = ASSETS_DIR / "fonts"
OUTPUT_DIR: Path = BASE_DIR / "output"
TEMP_DIR: Path = BASE_DIR / "temp"
DATA_DIR: Path = BASE_DIR / "data"
FRONTEND_DIR: Path = BASE_DIR / "frontend"
FRONTEND_DIST_DIR: Path = FRONTEND_DIR / "dist"
DB_PATH: Path = DATA_DIR / "shorts_factory.db"

# Default bundled Cyrillic+Latin font file and internal family name (verified via Pillow/fontconfig)
PRIMARY_FONT_FILE: str = "Montserrat-ExtraBold.ttf"
SECONDARY_FONT_FILE: str = "Montserrat-SemiBold.ttf"
PRIMARY_FONT_FAMILY: str = "Montserrat"


def ensure_directories() -> None:
    """Create all runtime directories if they do not exist."""
    for directory in (
        ASSETS_DIR,
        BACKGROUNDS_DIR,
        MUSIC_DIR,
        FONTS_DIR,
        OUTPUT_DIR,
        TEMP_DIR,
        DATA_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def escape_ffmpeg_filter_path(path: Path | PurePath, cwd: Path | None = None) -> str:
    """
    Format and escape a filesystem path for FFmpeg filter arguments (e.g. libass subtitles).

    When `cwd` is provided and `path` lies inside `cwd`, returns a relative POSIX path
    so Windows drive letters (`C:`) are completely avoided. Otherwise converts `\\`
    to `/` and escapes FFmpeg filtergraph special characters (`:`, `'`, `,`, `;`, `[`, `]`, `\\`).
    """
    raw: str
    if cwd is not None and isinstance(path, Path):
        try:
            rel = path.resolve().relative_to(cwd.resolve())
            raw = rel.as_posix()
        except ValueError:
            raw = str(path).replace("\\", "/")
    else:
        raw = str(path).replace("\\", "/")

    # Escape backslashes first, then FFmpeg filter option delimiters/special chars
    escaped = raw.replace("\\", "\\\\")
    for ch in (":", "'", ",", ";", "[", "]", " "):
        escaped = escaped.replace(ch, f"\\{ch}")
    return escaped


def safe_asset_path(base_dir: Path, filename: str) -> Path:
    """Resolve a single filename safely inside `base_dir`, preventing path traversal."""
    clean_name = Path(filename).name
    if not clean_name or clean_name in {".", ".."} or clean_name != filename:
        raise ValueError(f"Invalid asset filename: {filename!r}")
    if "/" in filename or "\\" in filename:
        raise ValueError(f"Asset filename must not contain path separators: {filename!r}")
    candidate = (base_dir / clean_name).resolve()
    base_resolved = base_dir.resolve()
    if not candidate.is_relative_to(base_resolved):
        raise ValueError(f"Path escapes target directory: {filename!r}")
    return candidate


def to_relative_posix(path: Path) -> str:
    """Convert a path under BASE_DIR to a portable relative POSIX string for DB storage."""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def from_relative_posix(stored_path: str) -> Path:
    """Resolve a stored relative POSIX (or absolute) path back to a local Path."""
    p = Path(stored_path)
    if p.is_absolute():
        return p
    return (BASE_DIR / p).resolve()


_VIDEO_INDEX_RE = re.compile(r"^video_(\d+)\.(?:mp4|txt)$", re.IGNORECASE)


def next_daily_output_paths(
    base_output_dir: Path | None = None,
    date_str: str | None = None,
) -> tuple[Path, Path]:
    """
    Compute the next available (video_XX.mp4, video_XX.txt) pair in output/YYYY-MM-DD/.
    Caller should hold a lock when running concurrently.
    """
    root = base_output_dir or OUTPUT_DIR
    day = date_str or datetime.now().strftime("%Y-%m-%d")
    day_dir = root / day
    day_dir.mkdir(parents=True, exist_ok=True)

    max_idx = 0
    for item in day_dir.iterdir():
        match = _VIDEO_INDEX_RE.match(item.name)
        if match:
            idx = int(match.group(1))
            if idx > max_idx:
                max_idx = idx

    next_idx = max_idx + 1
    stem = f"video_{next_idx:02d}"
    return day_dir / f"{stem}.mp4", day_dir / f"{stem}.txt"
