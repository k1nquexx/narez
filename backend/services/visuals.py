from __future__ import annotations

import hashlib
import logging
import math
import random
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from backend.core.hardware import cleanup_vram, detect_hardware, find_binary
from backend.core.paths import (
    BACKGROUNDS_DIR,
    FONTS_DIR,
    PRIMARY_FONT_FILE,
    SECONDARY_FONT_FILE,
)
from backend.services.tts_engine import probe_audio_duration

logger = logging.getLogger(__name__)

NICHE_CARD_PALETTE: dict[str, dict[str, tuple[int, int, int]]] = {
    "reddit": {
        "accent": (255, 69, 0),
        "badge_bg": (255, 69, 0),
        "glow": (255, 110, 40),
    },
    "scary": {
        "accent": (220, 38, 38),
        "badge_bg": (185, 28, 28),
        "glow": (239, 68, 68),
    },
    "psychology": {
        "accent": (124, 58, 237),
        "badge_bg": (109, 40, 217),
        "glow": (167, 139, 250),
    },
    "motivation": {
        "accent": (217, 119, 6),
        "badge_bg": (217, 119, 6),
        "glow": (251, 191, 36),
    },
}

NICHE_BG_GRADIENTS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = {
    "reddit": ((15, 23, 42), (30, 41, 59), (67, 20, 7)),
    "scary": ((9, 9, 15), (38, 10, 18), (18, 12, 34)),
    "psychology": ((15, 12, 36), (46, 16, 101), (17, 24, 39)),
    "motivation": ((17, 24, 39), (49, 27, 12), (24, 24, 27)),
}


def _load_font(filename: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONTS_DIR / filename
    if path.is_file():
        return ImageFont.truetype(str(path), size)
    fallback = FONTS_DIR / PRIMARY_FONT_FILE
    if fallback.is_file():
        return ImageFont.truetype(str(fallback), size)
    return ImageFont.load_default()


def _wrap_text_to_width(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.strip().split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.getlength(candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def generate_hook_card(
    *,
    title: str,
    subreddit_or_tag: str,
    author: str,
    niche: str,
    output_png: Path,
) -> Path:
    """
    Render a crisp 920px-wide Reddit/Story hook card PNG with transparent shadow canvas
    using bundled Cyrillic+Latin Montserrat fonts and pure Pillow vector icons.
    """
    palette = NICHE_CARD_PALETTE.get(niche, NICHE_CARD_PALETTE["reddit"])
    accent = palette["accent"]

    card_w = 900
    pad_x = 44
    pad_y = 36
    shadow_pad = 32
    text_max_w = card_w - pad_x * 2

    # Choose optimal title font size so 1-4 lines fit comfortably
    title_text = title.strip()
    title_font_size = 44
    title_font = _load_font(PRIMARY_FONT_FILE, title_font_size)
    wrapped = _wrap_text_to_width(title_text, title_font, text_max_w)
    while len(wrapped) > 4 and title_font_size > 28:
        title_font_size -= 3
        title_font = _load_font(PRIMARY_FONT_FILE, title_font_size)
        wrapped = _wrap_text_to_width(title_text, title_font, text_max_w)
    if len(wrapped) > 4:
        wrapped = wrapped[:4]
        wrapped[-1] = wrapped[-1][: max(1, len(wrapped[-1]) - 3)].rstrip() + "..."

    meta_font = _load_font(SECONDARY_FONT_FILE, 26)
    sub_font = _load_font(PRIMARY_FONT_FILE, 28)
    stat_font = _load_font(SECONDARY_FONT_FILE, 24)

    line_height = int(title_font_size * 1.28)
    header_h = 68
    body_h = len(wrapped) * line_height + 24
    footer_h = 54
    card_h = pad_y * 2 + header_h + body_h + footer_h

    canvas_w = card_w + shadow_pad * 2
    canvas_h = card_h + shadow_pad * 2

    # Soft shadow layer
    shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.rounded_rectangle(
        (shadow_pad, shadow_pad + 10, shadow_pad + card_w, shadow_pad + card_h + 10),
        radius=34,
        fill=(0, 0, 0, 155),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=18))

    # Card surface
    card_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_layer)

    x0 = shadow_pad
    y0 = shadow_pad
    x1 = x0 + card_w
    y1 = y0 + card_h

    # Dark sleek high-contrast card (works seamlessly on bright or dark backgrounds)
    draw.rounded_rectangle(
        (x0, y0, x1, y1),
        radius=32,
        fill=(252, 252, 253, 248),
        outline=(226, 232, 240, 255),
        width=3,
    )

    # Top accent pill bar inside card
    draw.rounded_rectangle(
        (x0 + pad_x, y0 + 20, x0 + pad_x + 74, y0 + 27),
        radius=4,
        fill=(*accent, 255),
    )

    # Circular avatar badge
    av_x = x0 + pad_x
    av_y = y0 + pad_y + 10
    av_r = 28
    draw.ellipse(
        (av_x, av_y, av_x + av_r * 2, av_y + av_r * 2),
        fill=(*palette["badge_bg"], 255),
    )
    badge_glyph = "r/" if niche == "reddit" else ("!" if niche == "scary" else ("P" if niche == "psychology" else "M"))
    glyph_font = _load_font(PRIMARY_FONT_FILE, 26)
    bbox = draw.textbbox((0, 0), badge_glyph, font=glyph_font)
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]
    draw.text(
        (av_x + av_r - gw / 2 - bbox[0], av_y + av_r - gh / 2 - bbox[1]),
        badge_glyph,
        font=glyph_font,
        fill=(255, 255, 255, 255),
    )

    # Subreddit / Tag + Author
    header_tx = av_x + av_r * 2 + 18
    draw.text(
        (header_tx, av_y - 2),
        subreddit_or_tag.strip() or "r/AskReddit",
        font=sub_font,
        fill=(15, 23, 42, 255),
    )
    draw.text(
        (header_tx, av_y + 31),
        f"{author.strip() or 'u/storyteller'}  •  2h",
        font=meta_font,
        fill=(100, 116, 139, 255),
    )

    # Verified-style accent pill on top-right
    pill_w, pill_h = 112, 34
    pill_x0 = x1 - pad_x - pill_w
    pill_y0 = av_y + 10
    draw.rounded_rectangle(
        (pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h),
        radius=17,
        fill=(*accent, 28),
        outline=(*accent, 180),
        width=2,
    )
    top_lbl = "TOP"
    tb = draw.textbbox((0, 0), top_lbl, font=stat_font)
    draw.text(
        (pill_x0 + (pill_w - (tb[2] - tb[0])) / 2 - tb[0], pill_y0 + (pill_h - (tb[3] - tb[1])) / 2 - tb[1]),
        top_lbl,
        font=stat_font,
        fill=(*accent, 255),
    )

    # Title lines
    cur_y = y0 + pad_y + header_h + 12
    for line in wrapped:
        draw.text(
            (x0 + pad_x, cur_y),
            line,
            font=title_font,
            fill=(15, 23, 42, 255),
        )
        cur_y += line_height

    # Divider line above footer
    div_y = y1 - pad_y - footer_h + 4
    draw.line(
        (x0 + pad_x, div_y, x1 - pad_x, div_y),
        fill=(226, 232, 240, 255),
        width=2,
    )

    # Footer vector icons: Upvote arrow, Comment bubble, Share arrow (NO emojis!)
    fy = div_y + 18
    fx = x0 + pad_x

    # 1. Upvote arrow + count
    arrow_pts = [
        (fx + 14, fy + 2),
        (fx + 27, fy + 15),
        (fx + 20, fy + 15),
        (fx + 20, fy + 26),
        (fx + 8, fy + 26),
        (fx + 8, fy + 15),
        (fx + 1, fy + 15),
    ]
    draw.polygon(arrow_pts, fill=(*accent, 255))
    draw.text((fx + 38, fy + 1), "9.4k", font=stat_font, fill=(71, 85, 105, 255))

    # 2. Comment speech bubble + count
    cx = fx + 150
    draw.rounded_rectangle((cx, fy + 3, cx + 28, fy + 22), radius=6, outline=(100, 116, 139, 255), width=3)
    draw.polygon([(cx + 6, fy + 22), (cx + 4, fy + 28), (cx + 13, fy + 22)], fill=(100, 116, 139, 255))
    draw.text((cx + 38, fy + 1), "648", font=stat_font, fill=(71, 85, 105, 255))

    # 3. Share arrow icon + label
    sx = fx + 288
    draw.arc((sx, fy + 6, sx + 22, fy + 28), start=180, end=295, fill=(100, 116, 139, 255), width=3)
    draw.polygon([(sx + 18, fy + 2), (sx + 27, fy + 10), (sx + 18, fy + 16)], fill=(100, 116, 139, 255))
    draw.text((sx + 36, fy + 1), "Share", font=stat_font, fill=(71, 85, 105, 255))

    composed = Image.alpha_composite(shadow_layer, card_layer)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    composed.save(str(output_png), format="PNG")
    return output_png


def list_gameplay_backgrounds() -> list[Path]:
    """Return available local video files in assets/backgrounds/."""
    exts = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    if not BACKGROUNDS_DIR.exists():
        return []
    return sorted(p for p in BACKGROUNDS_DIR.iterdir() if p.is_file() and p.suffix.lower() in exts)


def _run_ffmpeg(cmd: list[str], timeout: int = 300) -> None:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg command failed ({proc.returncode}): {proc.stderr[-1000:]}")


def prepare_gameplay_background(
    *,
    duration: float,
    output_video: Path,
    niche: str = "reddit",
    seed: int | None = None,
) -> Path:
    """
    Prepare a 1080x1920 60fps vertical background video of at least `duration` seconds.
    If assets/backgrounds/ contains videos, crops a random segment; otherwise generates
    a smooth animated procedural gradient backdrop via FFmpeg.
    """
    ffmpeg_path = find_binary("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg binary not found")

    target_dur = max(1.0, duration)
    output_video.parent.mkdir(parents=True, exist_ok=True)
    clips = list_gameplay_backgrounds()

    if clips:
        rng = random.Random(seed)
        chosen = rng.choice(clips)
        clip_dur = probe_audio_duration(chosen)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=60,setsar=1,format=yuv420p"

        cmd = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error"]
        if clip_dur > target_dur + 1.0:
            start_offset = rng.uniform(0.0, max(0.0, clip_dur - target_dur - 0.5))
            cmd.extend(["-ss", f"{start_offset:.2f}", "-i", str(chosen)])
        else:
            cmd.extend(["-stream_loop", "-1", "-i", str(chosen)])

        cmd.extend(
            [
                "-t",
                f"{target_dur:.3f}",
                "-an",
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "17",
                str(output_video),
            ]
        )
        _run_ffmpeg(cmd, timeout=360)
        return output_video

    # Procedural animated dark gradient fallback when assets/backgrounds is empty
    c0, c1, c2 = NICHE_BG_GRADIENTS.get(niche, NICHE_BG_GRADIENTS["reddit"])
    hex0 = f"#{c0[0]:02x}{c0[1]:02x}{c0[2]:02x}"
    hex1 = f"#{c1[0]:02x}{c1[1]:02x}{c1[2]:02x}"
    hex2 = f"#{c2[0]:02x}{c2[1]:02x}{c2[2]:02x}"
    grad_seed = seed if seed is not None else random.randint(1, 99999)

    grad_src = (
        f"gradients=s=540x960:r=30:n=3:c0={hex0}:c1={hex1}:c2={hex2}:"
        f"speed=0.018:type=radial:seed={grad_seed}:d={target_dur:.3f}"
    )
    vf = "scale=1080:1920:flags=bilinear,fps=60,vignette=PI/4,setsar=1,format=yuv420p"

    cmd = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        grad_src,
        "-vf",
        vf,
        "-t",
        f"{target_dur:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "20",
        str(output_video),
    ]
    try:
        _run_ffmpeg(cmd, timeout=240)
    except RuntimeError as exc:
        logger.warning("FFmpeg gradients filter fallback (%s); using color+hue", exc)
        fallback_src = f"color=c={hex1}:s=540x960:r=30:d={target_dur:.3f}"
        fallback_vf = "hue=h='t*12',scale=1080:1920:flags=bilinear,fps=60,vignette=PI/4,setsar=1,format=yuv420p"
        _run_ffmpeg(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                fallback_src,
                "-vf",
                fallback_vf,
                "-t",
                f"{target_dur:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "20",
                str(output_video),
            ],
            timeout=240,
        )
    return output_video


def _generate_procedural_art_frame(prompt: str, niche: str, index: int, out_png: Path) -> Path:
    """
    Create an atmospheric 1080x1920 vertical scene image via Pillow when CUDA/diffusers
    is unavailable (e.g. CPU-only Linux testing). Deterministic & distinct per prompt.
    """
    w, h = 1080, 1920
    digest = hashlib.sha256(f"{niche}:{index}:{prompt}".encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))

    c_top, c_mid, c_bot = NICHE_BG_GRADIENTS.get(niche, NICHE_BG_GRADIENTS["reddit"])
    # Slight per-slide variation so consecutive slides look visibly distinct
    shift = [(rng.randint(-15, 35), rng.randint(-15, 35), rng.randint(-15, 45)) for _ in range(3)]
    c0 = tuple(max(5, min(230, c_top[i] + shift[0][i])) for i in range(3))
    c1 = tuple(max(8, min(235, c_mid[i] + shift[1][i])) for i in range(3))
    c2 = tuple(max(5, min(220, c_bot[i] + shift[2][i])) for i in range(3))

    # Build smooth 1D vertical gradient strip and resize to full canvas (super fast!)
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / (h - 1)
        if t < 0.5:
            u = t * 2.0
            col = tuple(int(c0[i] * (1 - u) + c1[i] * u) for i in range(3))
        else:
            u = (t - 0.5) * 2.0
            col = tuple(int(c1[i] * (1 - u) + c2[i] * u) for i in range(3))
        px[0, y] = col
    base = strip.resize((w, h), Image.Resampling.BILINEAR).convert("RGBA")

    # Atmospheric soft glowing orbs & silhouettes
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    accent = NICHE_CARD_PALETTE.get(niche, NICHE_CARD_PALETTE["reddit"])["glow"]

    for _ in range(4):
        cx = rng.randint(140, w - 140)
        cy = rng.randint(250, h - 350)
        rx = rng.randint(180, 420)
        ry = rng.randint(180, 460)
        alpha = rng.randint(35, 95)
        gdraw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(*accent, alpha))

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=90))
    composed = Image.alpha_composite(base, glow_layer)

    # Geometric depth rings / stars / mist horizon
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(65):
        sx = rng.randint(20, w - 20)
        sy = rng.randint(40, h - 40)
        sr = rng.randint(2, 6)
        odraw.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 255, 255, rng.randint(30, 120)))

    # Silhouette horizon mountains / city blocks at bottom third
    pts = [(0, h)]
    steps = 12
    base_hy = rng.randint(1220, 1460)
    for s in range(steps + 1):
        px_x = int(s * (w / steps))
        px_y = base_hy + int(math.sin(s * 0.9 + index) * 95) + rng.randint(-55, 55)
        pts.append((px_x, px_y))
    pts.append((w, h))
    odraw.polygon(pts, fill=(8, 10, 16, 215))

    composed = Image.alpha_composite(composed, overlay).convert("RGB")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    composed.save(str(out_png), format="PNG")
    return out_png


def _generate_sdxl_images(
    image_prompts: list[str],
    sdxl_model: str,
    work_dir: Path,
) -> list[Path]:
    """Generate 576x1024 vertical images using diffusers SDXL-Turbo on CUDA GPU."""
    import torch  # type: ignore
    from diffusers import AutoPipelineForText2Image  # type: ignore

    logger.info("Loading SDXL model %s on CUDA float16...", sdxl_model)
    pipe = None
    generated: list[Path] = []
    try:
        try:
            pipe = AutoPipelineForText2Image.from_pretrained(
                sdxl_model,
                torch_dtype=torch.float16,
                variant="fp16",
            )
        except Exception:
            pipe = AutoPipelineForText2Image.from_pretrained(
                sdxl_model,
                torch_dtype=torch.float16,
            )

        pipe = pipe.to("cuda")
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing()
        if hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()

        is_turbo = "turbo" in sdxl_model.lower()
        steps = 4 if is_turbo else 20
        guidance = 0.0 if is_turbo else 5.5

        for idx, prompt in enumerate(image_prompts):
            full_prompt = f"{prompt}, vertical 9:16 composition, atmospheric lighting, high detail, no text"
            image = pipe(
                prompt=full_prompt,
                width=576,
                height=1024,
                num_inference_steps=steps,
                guidance_scale=guidance,
            ).images[0]
            out_png = work_dir / f"slide_{idx:02d}.png"
            image.save(str(out_png), format="PNG")
            generated.append(out_png)
    finally:
        if pipe is not None:
            del pipe
        cleanup_vram()
    return generated


def generate_ai_slideshow(
    *,
    image_prompts: list[str],
    duration: float,
    output_video: Path,
    work_dir: Path,
    sdxl_model: str = "stabilityai/sdxl-turbo",
    niche: str = "reddit",
) -> tuple[Path, str]:
    """
    Generate 4-6 vertical images (via CUDA SDXL-Turbo when available, or procedural Pillow art fallback)
    and assemble them into a smooth 1080x1920 60fps Ken Burns zoom/pan MP4.
    Returns (output_video, mode_used).
    """
    ffmpeg_path = find_binary("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg binary not found")

    prompts = [p.strip() for p in image_prompts if p.strip()][:6]
    if not prompts:
        prompts = [f"cinematic vertical scene {i}" for i in range(5)]

    work_dir.mkdir(parents=True, exist_ok=True)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    hw = detect_hardware()
    slide_paths: list[Path] = []
    mode_used = "procedural_art_cpu"

    if hw.cuda_available and hw.diffusers_available:
        try:
            slide_paths = _generate_sdxl_images(prompts, sdxl_model, work_dir)
            mode_used = "sdxl_cuda"
        except Exception as exc:
            logger.warning("SDXL-Turbo GPU generation failed (%s); using procedural art fallback", exc)
            cleanup_vram()
            slide_paths = []

    if not slide_paths:
        for idx, prompt in enumerate(prompts):
            slide_paths.append(
                _generate_procedural_art_frame(prompt, niche, idx, work_dir / f"slide_{idx:02d}.png")
            )

    # Assemble Ken Burns zoom/pan segments via FFmpeg
    num_slides = len(slide_paths)
    slide_dur = max(2.0, duration / num_slides)
    frames_per_slide = max(60, int(math.ceil(slide_dur * 60)))

    cmd: list[str] = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error"]
    for img_path in slide_paths:
        cmd.extend(["-i", str(img_path)])

    filter_parts: list[str] = []
    concat_inputs: list[str] = []

    for idx in range(num_slides):
        # Alternate smooth zoom-in, slow zoom-out, gentle pan-right/zoom-in
        mode = idx % 3
        if mode == 0:
            # Zoom in smoothly toward center
            z_expr = "min(zoom+0.0007,1.18)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif mode == 1:
            # Zoom out smoothly from 1.16 -> 1.0
            z_expr = "if(lte(on,1),1.16,max(1.00,zoom-0.0006))"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:
            # Subtle pan + zoom clamped safely inside bounds
            z_expr = "min(zoom+0.0005,1.14)"
            x_expr = "min(iw-iw/zoom,max(0,iw/2-(iw/zoom/2)+(on-1)*0.15))"
            y_expr = "ih/2-(ih/zoom/2)"

        filter_parts.append(
            f"[{idx}:v]scale=1296:2304:force_original_aspect_ratio=increase,crop=1296:2304,"
            f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames_per_slide}:s=1080x1920:fps=60,"
            f"setsar=1,format=yuv420p[v{idx}]"
        )
        concat_inputs.append(f"[v{idx}]")

    filter_parts.append(f"{''.join(concat_inputs)}concat=n={num_slides}:v=1:a=0[vout]")

    cmd.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[vout]",
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "17",
            str(output_video),
        ]
    )
    _run_ffmpeg(cmd, timeout=600)
    return output_video, mode_used
