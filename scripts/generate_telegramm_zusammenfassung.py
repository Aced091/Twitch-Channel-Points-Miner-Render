#!/usr/bin/env python3
import os
import textwrap
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


def ensure_dir(path: str) -> None:
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def make_parchment(size: Tuple[int, int], seed: int = 21) -> Image.Image:
    width, height = size
    base = Image.new("RGB", size, (238, 227, 203))
    rng = np.random.default_rng(seed)
    noise = rng.integers(low=-10, high=10, size=(height, width, 3), dtype=np.int16)
    arr = np.array(base).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB").filter(ImageFilter.GaussianBlur(0.6))
    vignette = Image.new("L", size, 0)
    draw_v = ImageDraw.Draw(vignette)
    margin = int(min(width, height) * 0.025)
    draw_v.rectangle([margin, margin, width - margin, height - margin], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=margin * 0.8))
    img = Image.composite(img, Image.new("RGB", size, (210, 195, 165)), vignette)
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

    # A4 @ 300 DPI
    W, H = 2480, 3508
    img = make_parchment((W, H))
    draw = ImageDraw.Draw(img)

    title_font = load_font(86, bold=True)
    meta_font = load_font(40)
    body_font = load_font(44)
    small_font = load_font(28)

    # Header
    title = "Historische Einordnung: Göring-Telegramm (April 1945)"
    tw = title_font.getlength(title)
    draw.text((int(W * 0.5 - tw / 2), int(H * 0.075)), title, font=title_font, fill=(30, 25, 20))
    draw.line([(int(W * 0.12), int(H * 0.13)), (int(W * 0.88), int(H * 0.13))], fill=(55, 45, 35), width=3)

    # Meta
    meta = "Neutrale, sachliche Zusammenfassung. Kein Originaltext, keine Befürwortung."
    mw = small_font.getlength(meta)
    draw.text((int(W * 0.5 - mw / 2), int(H * 0.145)), meta, font=small_font, fill=(60, 55, 50))

    # Body (neutral facts)
    y = int(H * 0.19)
    body = (
        "Kontext:\n"
        "Ende April 1945 sandte Hermann Göring von Obersalzberg ein Telegramm an Adolf Hitler.\n"
        "Bezugspunkt war ein Führererlass vom 29. Juni 1941, der im Falle der Verhinderung eine\n"
        "Regelung zur Amtswahrnehmung vorsah. Göring stellte die Frage, ob er – mangels Verbindung\n"
        "zur Reichskanzlei – die Führung kommissarisch übernehmen solle, sofern bis zu einer gesetzten\n"
        "Frist keine gegenteilige Weisung eintreffe.\n\n"
        "Rezeption:\n"
        "Die Reaktion im Führerbunker fiel scharf aus; das Vorgehen wurde als illoyal bzw. anmaßend\n"
        "gewertet. Kurz darauf verlor Göring seine Ämter. In der Folge kam es zu weiteren chaotischen\n"
        "Entwicklungen innerhalb der NS-Führung.\n\n"
        "Bewertung:\n"
        "Das Telegramm dokumentiert den Zerfall der Entscheidungsstrukturen in den letzten Kriegstagen.\n"
        "Es hat historischen Quellenwert als Beispiel für Machtfragen und Nachfolgeregelungen in der\n"
        "Endphase des Regimes.\n"
    )
    y = draw_wrapped(draw, (int(W * 0.12), y), body, font=body_font, max_width_px=int(W * 0.76), line_spacing=0.2)

    # Footer
    footer = "Hinweis: Diese Seite bietet eine Zusammenfassung zur historischen Einordnung; kein Originaldokument."
    fw = small_font.getlength(footer)
    draw.text((int(W * 0.5 - fw / 2), int(H * 0.95)), footer, font=small_font, fill=(70, 60, 52))

    # Save
    out_png = os.path.join(out_dir, "telegramm_zusammenfassung_a4.png")
    out_jpg = os.path.join(out_dir, "telegramm_zusammenfassung_a4.jpg")
    img.save(out_png)
    img.convert("RGB").save(out_jpg, quality=88, optimize=True)
    print(out_png)
    print(out_jpg)


if __name__ == "__main__":
    main()