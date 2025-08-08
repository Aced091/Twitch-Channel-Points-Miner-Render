#!/usr/bin/env python3
import os
import textwrap
from datetime import date
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def make_parchment(size: Tuple[int, int]) -> Image.Image:
    width, height = size
    base = Image.new("RGB", size, (238, 227, 203))  # warm beige
    # Add subtle noise texture
    noise = np.random.default_rng(42).integers(low=-10, high=10, size=(height, width, 3), dtype=np.int16)
    arr = np.array(base).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB").filter(ImageFilter.GaussianBlur(0.6))
    # Darken edges for aged look
    vignette = Image.new("L", size, 0)
    draw_v = ImageDraw.Draw(vignette)
    margin = int(min(width, height) * 0.02)
    draw_v.rectangle([margin, margin, width - margin, height - margin], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=margin * 0.7))
    img = Image.composite(img, Image.new("RGB", size, (210, 195, 165)), vignette)
    # Add faint fold lines
    fold = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_f = ImageDraw.Draw(fold)
    draw_f.line([(margin, height // 3), (width - margin, height // 3)], fill=(50, 40, 30, 18), width=2)
    draw_f.line([(margin, 2 * height // 3), (width - margin, 2 * height // 3)], fill=(50, 40, 30, 12), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), fold).convert("RGB")
    return img


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # Try common fonts; fall back to PIL default
    preferred = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", False),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", True),
        ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", False),
        ("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", True),
    ]
    path = None
    for p, is_bold in preferred:
        if os.path.exists(p) and (is_bold == bold):
            path = p
            break
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_text_block(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, font: ImageFont.ImageFont, fill=(20, 20, 20), max_width_px: int = 1400, line_spacing: int = 6) -> int:
    x, y = xy
    # Estimate wrap by characters via measuring average char width
    avg_char_px = max(font.getlength("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz") / 52.0, 1)
    wrap_cols = max(int(max_width_px / avg_char_px), 20)
    wrapped = []
    for para in text.split("\n"):
        if para.strip() == "":
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(para, width=wrap_cols))
    for line in wrapped:
        draw.text((x, y), line, font=font, fill=fill)
        y += int(font.size * 1.2) + line_spacing
    return y


def main():
    out_dir = "/workspace/output"
    ensure_dir(out_dir)

    # Canvas ~A4 at ~200 DPI for mobile-friendly size
    W, H = 1654, 2339
    img = make_parchment((W, H))
    draw = ImageDraw.Draw(img)

    # Header
    title_font = load_font(48, bold=True)
    meta_font = load_font(28)
    body_font = load_font(30)
    small_font = load_font(20)

    header = "Fernschreiben – Entwurf (historisch inspiriert)"
    draw.text((int(W * 0.08), int(H * 0.06)), header, font=title_font, fill=(25, 25, 25))

    # Meta lines (place/date)
    meta_left = f"Berchtesgaden, {date(1945, 4, 23).strftime('%d. %B %Y')}"
    meta_right = "An: Reichskanzlei, Berlin"
    draw.text((int(W * 0.08), int(H * 0.11)), meta_left, font=meta_font, fill=(40, 35, 30))
    # right align
    mr_w = meta_font.getlength(meta_right)
    draw.text((int(W * 0.92 - mr_w), int(H * 0.11)), meta_right, font=meta_font, fill=(40, 35, 30))

    # Subject line
    subj = "Betreff: Führungsvollmacht gem. Erlass vom 29. Juni 1941"
    draw.text((int(W * 0.08), int(H * 0.15)), subj, font=meta_font, fill=(30, 25, 20))

    # Body (neutral, historically inspired; NOT exact style)
    y = int(H * 0.19)
    body = (
        "Mein Führer,\n\n"
        "In Fortführung der geltenden Regelungen verweise ich auf den Erlass vom 29. Juni 1941,\n"
        "wonach im Falle Ihrer Verhinderung die Wahrnehmung der Führung zu übertragen ist.\n"
        "Angesichts der Lage und Ihrer eingeschränkten Verbindung zu den Führungsstellen bitte ich,\n"
        "mir unverzüglich Klarheit über die Ausübung dieser Vollmacht zu bestätigen.\n\n"
        "Sollte bis zum heutigen Abend keine gegenteilige Weisung eingehen, nehme ich an, dass die\n"
        "Übertragung gemäß dem genannten Erlass wirksam wird, um die Handlungsfähigkeit des Staates\n"
        "aufrechtzuerhalten.\n\n"
        "Mit der Erwartung Ihrer Entscheidung verbleibe ich\n"
        "Hochachtungsvoll\n"
    )

    y = draw_text_block(draw, (int(W * 0.08), y), body, font=body_font, max_width_px=int(W * 0.84))

    # Signature block (typed)
    sig_name = "H. Göring"
    draw.line([(int(W * 0.65), y + 30), (int(W * 0.92), y + 30)], fill=(30, 25, 20), width=2)
    draw.text((int(W * 0.65), y + 40), sig_name, font=body_font, fill=(30, 25, 20))
    draw.text((int(W * 0.65), y + 80), "Reichsmarschall (Dienstsitz Berchtesgaden)", font=small_font, fill=(50, 45, 40))

    # Footer disclaimer (explicit)
    disclaimer = "Fiktive, historisch inspirierte Darstellung – kein Originaldokument, keine Befürwortung."
    dw = small_font.getlength(disclaimer)
    draw.text((int(W * 0.5 - dw / 2), int(H * 0.96)), disclaimer, font=small_font, fill=(60, 55, 50))

    # Save PNG and JPG
    out_png = os.path.join(out_dir, "historisch_inspiriertes_dokument.png")
    out_jpg = os.path.join(out_dir, "historisch_inspiriertes_dokument.jpg")
    img.save(out_png)
    img.convert("RGB").save(out_jpg, quality=85, optimize=True)

    print(out_png)
    print(out_jpg)


if __name__ == "__main__":
    main()