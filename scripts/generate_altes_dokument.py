#!/usr/bin/env python3
import os
import textwrap
from typing import Tuple
from datetime import date

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def make_parchment(size: Tuple[int, int]) -> Image.Image:
    width, height = size
    base = Image.new("RGB", size, (238, 227, 203))
    # dezentes Rauschen für Struktur
    noise = np.random.default_rng(7).integers(low=-12, high=12, size=(height, width, 3), dtype=np.int16)
    arr = np.array(base).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB").filter(ImageFilter.GaussianBlur(0.7))
    # Ränder abdunkeln
    vignette = Image.new("L", size, 0)
    draw_v = ImageDraw.Draw(vignette)
    margin = int(min(width, height) * 0.025)
    draw_v.rectangle([margin, margin, width - margin, height - margin], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=margin * 0.8))
    img = Image.composite(img, Image.new("RGB", size, (210, 195, 165)), vignette)
    # leichte Faltlinien
    fold = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_f = ImageDraw.Draw(fold)
    draw_f.line([(margin, height // 3), (width - margin, height // 3)], fill=(50, 40, 30, 16), width=2)
    draw_f.line([(margin, 2 * height // 3), (width - margin, 2 * height // 3)], fill=(50, 40, 30, 12), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), fold).convert("RGB")
    return img


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
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


def draw_wrapped(draw: ImageDraw.ImageDraw, pos: Tuple[int, int], text: str, font: ImageFont.ImageFont, color=(25, 20, 15), max_width_px: int = 2000, line_spacing: float = 0.25) -> int:
    x, y = pos
    avg = max(font.getlength("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz") / 52.0, 1)
    cols = max(int(max_width_px / avg), 20)
    for para in text.split("\n"):
        if not para.strip():
            y += int(font.size * (1.0 + line_spacing))
            continue
        for line in textwrap.wrap(para, width=cols):
            draw.text((x, y), line, font=font, fill=color)
            y += int(font.size * (1.0 + line_spacing))
    return y


def main():
    out_dir = "/workspace/output"
    ensure_dir(out_dir)

    # A4 @ 300 DPI: 2480 x 3508 px
    W, H = 2480, 3508
    img = make_parchment((W, H))
    draw = ImageDraw.Draw(img)

    # Typografie
    title_font = load_font(96, bold=True)
    subtitle_font = load_font(40)
    body_font = load_font(44)
    small_font = load_font(28)

    # Titel
    title = "Wie früher geschrieben wurde"
    tw = title_font.getlength(title)
    draw.text((int(W * 0.5 - tw / 2), int(H * 0.08)), title, font=title_font, fill=(30, 25, 20))

    # Zierlinie
    draw.line([(int(W * 0.15), int(H * 0.14)), (int(W * 0.85), int(H * 0.14))], fill=(55, 45, 35), width=3)

    # Untertitel/Datumszeile (neutral)
    sub = f"Im Jahre {date.today().year}, in stiller Erinnerung an alte Schreibkunst"
    sw = subtitle_font.getlength(sub)
    draw.text((int(W * 0.5 - sw / 2), int(H * 0.16)), sub, font=subtitle_font, fill=(40, 35, 30))

    # Fließtext – neutraler, altmodischer Tonfall
    y = int(H * 0.22)
    body = (
        "Hochgeehrte Damen und Herren,\n\n"
        "mit demütiger Feder sei hier ein Schreiben gesetzt, wie es ehedem gebräuchlich war.\n"
        "In wohlgesetzten Worten, behutsam und mit Bedacht, werden Zeilen geordnet und Gedanken gefügt.\n"
        "So möge der Leser erkennen, wie sich Zucht und Zierde des Schreibens in früheren Tagen gestalteten,\n"
        "da Tinte und Pergament die treuen Gefährten der Mitteilungen waren.\n\n"
        "Es geziemt sich, in anständiger Form, Gruß und Anliegen zu verbinden und die Hand in Respekt zu reichen.\n"
        "Darum sei dieses Blatt ein schlichtes Zeugnis dessen, wie früher geschrieben wurde: in ruhigen Sätzen,\n"
        "klarer Absicht und besonnener Sprache.\n\n"
        "So verbleibe ich, mit verbindlichem Gruße, in ausgezeichneter Hochachtung.\n"
    )
    y = draw_wrapped(draw, (int(W * 0.12), y), body, font=body_font, max_width_px=int(W * 0.76), line_spacing=0.2)

    # Signaturblock (typografisch)
    sig_line_y = y + 60
    draw.line([(int(W * 0.6), sig_line_y), (int(W * 0.88), sig_line_y)], fill=(45, 35, 28), width=2)
    draw.text((int(W * 0.6), sig_line_y + 18), "In aufrichtiger Verbundenheit", font=small_font, fill=(45, 35, 28))
    draw.text((int(W * 0.6), sig_line_y + 52), "— Dein ergebener Schreiber —", font=small_font, fill=(55, 45, 38))

    # Fußzeile (neutraler Hinweis)
    footer = "Gestaltet als stilisiertes, neutrales Dokument im historischen Gewand"
    fw = small_font.getlength(footer)
    draw.text((int(W * 0.5 - fw / 2), int(H * 0.95)), footer, font=small_font, fill=(70, 60, 52))

    # Speichern
    out_png = os.path.join(out_dir, "altes_dokument_a4.png")
    out_jpg = os.path.join(out_dir, "altes_dokument_a4.jpg")
    img.save(out_png)
    img.convert("RGB").save(out_jpg, quality=88, optimize=True)
    print(out_png)
    print(out_jpg)


if __name__ == "__main__":
    main()