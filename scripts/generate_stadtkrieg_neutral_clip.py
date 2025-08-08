#!/usr/bin/env python3
import os
import math
import random
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import VideoClip


OUT_PATH = "/workspace/output/clip_stadtkrieg_neutral.mp4"
DURATION_S = 12
FPS = 24
W, H = 1280, 720


def make_background() -> Image.Image:
    # Dämmerungs-Hintergrund mit Rauchschleier
    grad = Image.new("RGB", (W, H))
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    top = np.array([40, 40, 45], dtype=np.float32)
    bottom = np.array([95, 90, 85], dtype=np.float32)
    for y in range(H):
        t = y / max(H - 1, 1)
        arr[y, :, :] = (top * (1 - t) + bottom * t).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    # Leichter Rauch per Perlin-artigem Rauschen (vereinfachtes FBM)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 18, size=(H // 4, W // 4)).astype(np.float32)
    noise = Image.fromarray(((noise - noise.min()) / (noise.ptp() + 1e-6) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    smoke = Image.new("RGBA", (W, H), (80, 75, 70, 0))
    smoke.putalpha(noise)
    smoke = smoke.filter(ImageFilter.GaussianBlur(3))
    img = Image.alpha_composite(img.convert("RGBA"), smoke).convert("RGB")
    return img


def draw_ruins(base: Image.Image, camera_x: float) -> Image.Image:
    # Silhouetten zerstörter Gebäude (ohne erkennbare Symbole)
    img = base.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    horizon = int(H * 0.62)
    # mehrere Blöcke, parallax je nach y
    for i in range(26):
        bw = rng.randint(40, 160)
        bh = rng.randint(80, 280)
        x = (i * 90 - int(camera_x * (0.3 + 0.7 * (bh / 280)))) % (W + 200) - 100
        y = horizon - bh
        col = (25 + rng.randint(0, 10), 25 + rng.randint(0, 10), 28 + rng.randint(0, 10), 255)
        d.rectangle([x, y, x + bw, horizon], fill=col)
        # Brüche/Trümmerkanten
        for _ in range(rng.randint(2, 6)):
            rx = x + rng.randint(0, bw)
            ry = y + rng.randint(0, bh)
            rw = rng.randint(8, 22)
            rh = rng.randint(8, 22)
            d.rectangle([rx, ry, rx + rw, ry + rh], fill=(15, 15, 18, 255))
    # Straße/Vordergrund dunkel
    d.rectangle([0, horizon, W, H], fill=(20, 20, 22, 255))
    return img.convert("RGB")


def add_snow(img: Image.Image, t: float) -> Image.Image:
    # Schneefallpartikel
    rng = np.random.default_rng(99)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    num = 800
    for i in range(num):
        sx = int((rng.random() * (W + 100) + (t * 60 + i * 3)) % (W + 100)) - 50
        sy = int((rng.random() * (H + 200) + (t * 120 + i * 5)) % (H + 200)) - 100
        r = 1 if i % 7 else 2
        alpha = 160 if r == 2 else 110
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(240, 240, 240, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def add_grain(img: Image.Image, strength: float = 0.08) -> Image.Image:
    arr = np.array(img).astype(np.int16)
    rng = np.random.default_rng(5)
    noise = rng.integers(low=int(-255 * strength), high=int(255 * strength), size=arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, mode="RGB")
    return out.filter(ImageFilter.GaussianBlur(0.3))


def color_grade(img: Image.Image, t: float) -> Image.Image:
    # Monochrom mit leichter Sepia-Note, dezentes Flackern
    arr = np.array(img).astype(np.float32)
    gray = (arr[..., 0] * 0.3 + arr[..., 1] * 0.59 + arr[..., 2] * 0.11)[..., None]
    sepia = np.concatenate([
        gray * 1.05,
        gray * 0.95,
        gray * 0.9,
    ], axis=2)
    flicker = 0.96 + 0.08 * math.sin(2 * math.pi * 0.7 * t)
    sepia = np.clip(sepia * flicker, 0, 255).astype(np.uint8)
    return Image.fromarray(sepia, mode="RGB")


def make_frame(t: float) -> np.ndarray:
    # Kamerabewegung: sanfter Schwenk nach rechts
    cam_x = 120 * (t / DURATION_S)
    bg = make_background()
    scene = draw_ruins(bg, camera_x=cam_x)
    scene = add_snow(scene, t)
    scene = add_grain(scene, 0.07)
    scene = color_grade(scene, t)
    return np.array(scene)


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    clip = VideoClip(make_frame, duration=DURATION_S)
    clip = clip.set_fps(FPS)
    clip.write_videofile(OUT_PATH, codec="libx264", audio=False, fps=FPS, bitrate="2500k")


if __name__ == "__main__":
    main()