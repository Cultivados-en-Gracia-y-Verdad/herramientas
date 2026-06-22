#!/usr/bin/env python3
"""Generate macOS-style squircle app icons for CGV Writer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "app-icon-source.png"
OUT_DIR = ROOT / "src-tauri" / "icons"
MASTER_SIZE = 1024
# Fill the squircle — logo as large as possible; the mask provides dock-sized rounding.
CONTENT_SCALE = 0.96
# macOS Big Sur squircle is close to superellipse n≈5.
SQUIRCLE_N = 5.0


def trim_logo(image: Image.Image, padding: int = 8) -> Image.Image:
    """Crop to colored logo pixels, dropping baked-in shadows or outer margins."""
    rgba = image.convert("RGBA")
    mask = Image.new("L", rgba.size, 0)
    px = rgba.load()
    mpx = mask.load()
    for y in range(rgba.size[1]):
        for x in range(rgba.size[0]):
            r, g, b, a = px[x, y]
            if a > 200 and (r < 250 or g < 250 or b < 250):
                mpx[x, y] = 255
    bbox = mask.getbbox()
    if not bbox:
        return rgba
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(rgba.size[0], bbox[2] + padding)
    bottom = min(rgba.size[1], bbox[3] + padding)
    return rgba.crop((left, top, right, bottom))


def squircle_mask(size: int, exponent: float = SQUIRCLE_N) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    pixels = mask.load()
    radius = size / 2.0
    center = radius
    for y in range(size):
        ny = abs((y - center + 0.5) / radius)
        ny_pow = ny**exponent
        for x in range(size):
            nx = abs((x - center + 0.5) / radius)
            if nx**exponent + ny_pow <= 1.0:
                pixels[x, y] = 255
    return mask


def fit_square(image: Image.Image, size: int, scale: float = CONTENT_SCALE) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    target = size * scale
    fit_scale = min(target / width, target / height)
    new_w = max(1, int(round(width * fit_scale)))
    new_h = max(1, int(round(height * fit_scale)))
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    offset = ((size - new_w) // 2, (size - new_h) // 2)
    canvas.paste(resized, offset, resized)
    return canvas


def apply_squircle(image: Image.Image) -> Image.Image:
    size = image.size[0]
    mask = squircle_mask(size)
    result = image.copy()
    alpha = result.getchannel("A")
    result.putalpha(Image.composite(alpha, Image.new("L", (size, size), 0), mask))
    return result


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def build_icns(master: Image.Image, out_path: Path) -> None:
    iconset = out_path.with_suffix(".iconset")
    if iconset.exists():
        for child in iconset.iterdir():
            child.unlink()
    else:
        iconset.mkdir(parents=True)

    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }

    for name, px in sizes.items():
        save_png(master.resize((px, px), Image.Resampling.LANCZOS), iconset / name)

    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out_path)], check=True)

    for child in iconset.iterdir():
        child.unlink()
    iconset.rmdir()


def build_ico(master: Image.Image, out_path: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [master.resize((px, px), Image.Resampling.LANCZOS) for px in sizes]
    images[0].save(
        out_path,
        format="ICO",
        sizes=[(img.size[0], img.size[1]) for img in images],
        append_images=images[1:],
    )


def main() -> int:
    if not SOURCE.exists():
        print(f"Source icon not found: {SOURCE}", file=sys.stderr)
        return 1

    source = trim_logo(Image.open(SOURCE))
    square = fit_square(source, MASTER_SIZE)
    icon = apply_squircle(square)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    save_png(icon, OUT_DIR / "icon.png")
    save_png(icon.resize((32, 32), Image.Resampling.LANCZOS), OUT_DIR / "32x32.png")
    save_png(icon.resize((128, 128), Image.Resampling.LANCZOS), OUT_DIR / "128x128.png")
    save_png(icon.resize((256, 256), Image.Resampling.LANCZOS), OUT_DIR / "128x128@2x.png")
    build_icns(icon, OUT_DIR / "icon.icns")
    build_ico(icon, OUT_DIR / "icon.ico")

    print(f"Icons written to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
