#!/usr/bin/env python3
import os
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def make_parchment(size: Tuple[int, int], seed: int = 11) -> Image.Image:
    width, height = size
    base = Image.new("RGB", size, (238, 227, 203))
    rng = np.random.default_rng(seed)
    noise = rng.integers(low=-12, high=12, size=(height, width, 3), dtype=np.int16)
    arr = np.array(base).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB").filter(ImageFilter.GaussianBlur(0.6))
    vignette = Image.new("L", size, 0)
    draw_v = ImageDraw.Draw(vignette)
    margin = int(min(width, height) * 0.025)
    draw_v.rectangle([margin, margin, width - margin, height - margin], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=margin * 0.8))
    img = Image.composite(img, Image.new("RGB", size, (210, 195, 165)), vignette)
    # leichte Flecken
    spots = Image.new("RGBA", size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(spots)
    for y in range(margin, height - margin, int(height * 0.12)):
        ds.ellipse([(margin, y), (margin + 14, y + 10)], fill=(80, 60, 40, 12))
    img = Image.alpha_composite(img.convert("RGBA"), spots).convert("RGB")
    return img


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    preferred = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", False),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", True),
    ]
    path = None
    for p, is_bold in preferred:
        if os.path.exists(p) and (is_bold == bold):
            path = p
            break
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_guides(img: Image.Image) -> Image.Image:
    W, H = img.size
    g = img.convert("RGBA")
    d = ImageDraw.Draw(g)
    # Ränder
    left, right = int(W * 0.12), int(W * 0.88)
    top, bottom = int(H * 0.12), int(H * 0.9)
    d.rectangle([left, top, right, bottom], outline=(60, 50, 40, 64), width=3)
    # Feine Linien für Text
    y = top + int((H * 0.04))
    while y < bottom - int(H * 0.05):
        d.line([(left + 12, y), (right - 12, y)], fill=(60, 50, 40, 36), width=1)
        y += 56  # Zeilenabstand
    # Kopfzeile (faint placeholders)
    font_big = load_font(72, bold=True)
    font_small = load_font(36)
    title = "Titel"
    tw = font_big.getlength(title)
    d.text((int(W * 0.5 - tw / 2), int(H * 0.08)), title, font=font_big, fill=(50, 45, 40, 90))
    d.text((left + 8, top - 40), "Ort:", font=font_small, fill=(50, 45, 40, 90))
    d.text((right - 220, top - 40), "Datum:", font=font_small, fill=(50, 45, 40, 90))
    return g.convert("RGB")


def main():
    out_dir = "/workspace/output"
    ensure_dir(out_dir)
    # A4 @ 300 DPI
    W, H = 2480, 3508
    base = make_parchment((W, H))
    # Blank
    blank_png = os.path.join(out_dir, "altes_dokument_a4_blank.png")
    blank_jpg = os.path.join(out_dir, "altes_dokument_a4_blank.jpg")
    base.save(blank_png)
    base.convert("RGB").save(blank_jpg, quality=88, optimize=True)
    # Template mit Linien/Platzhaltern
    templ = draw_guides(base.copy())
    templ_png = os.path.join(out_dir, "altes_dokument_a4_template.png")
    templ_jpg = os.path.join(out_dir, "altes_dokument_a4_template.jpg")
    templ.save(templ_png)
    templ.convert("RGB").save(templ_jpg, quality=88, optimize=True)
    print(blank_jpg)
    print(templ_jpg)


if __name__ == "__main__":
    main()