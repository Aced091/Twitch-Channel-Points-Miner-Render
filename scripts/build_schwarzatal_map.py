#!/usr/bin/env python3
import argparse
import datetime
import math
import os
from typing import Tuple, Optional, Dict, Any

import matplotlib.pyplot as plt
import numpy as np
import contextily as cx
import requests


R_EARTH = 6378137.0  # Web Mercator sphere radius (meters)
INITIAL_RESOLUTION_M_PER_PX = 2 * math.pi * R_EARTH / 256.0


def ensure_dirs(*dirs: str) -> None:
    for d in dirs:
        if d:
            os.makedirs(d, exist_ok=True)


def parse_size(size_str: str) -> Tuple[float, float]:
    try:
        w, h = size_str.lower().split("x")
        return float(w), float(h)
    except Exception as exc:
        raise argparse.ArgumentTypeError("--size erwartet Format wie 14x20 (in Zoll)") from exc


def lonlat_to_webmercator(lon_deg: float, lat_deg: float) -> Tuple[float, float]:
    lon_rad = math.radians(lon_deg)
    lat_rad = math.radians(lat_deg)
    x = R_EARTH * lon_rad
    # clamp latitude for Web Mercator stability
    lat_rad = max(min(lat_rad, math.radians(85.05112878)), math.radians(-85.05112878))
    y = R_EARTH * math.log(math.tan(math.pi / 4.0 + lat_rad / 2.0))
    return x, y


def bbox_wgs84_to_mercator(bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    x_min, y_min = lonlat_to_webmercator(min_lon, min_lat)
    x_max, y_max = lonlat_to_webmercator(max_lon, max_lat)
    return (min(x_min, x_max), min(y_min, y_max), max(x_min, x_max), max(y_min, y_max))


def geocode_bbox(place: str, user_agent: str = "schwarzatal-map/1.0") -> Dict[str, Any]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place, "format": "json", "limit": 1, "polygon_geojson": 0, "addressdetails": 0}
    headers = {"User-Agent": user_agent}
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError(f"Ort konnte nicht gefunden werden: {place}")
    item = data[0]
    bb = item.get("boundingbox")
    if not bb or len(bb) != 4:
        raise RuntimeError("Von Nominatim kam keine Bounding Box zurück")
    # Nominatim order: [south, north, west, east]
    south, north, west, east = map(float, bb)
    bbox_wgs84 = (west, south, east, north)
    return {"display_name": item.get("display_name", place), "bbox_wgs84": bbox_wgs84}


def add_north_arrow(ax, xy=(0.05, 0.08), size=0.05, text="N"):
    ax.annotate(
        text,
        xy=xy,
        xytext=(xy[0], xy[1] + size),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        arrowprops=dict(facecolor="black", width=4, headwidth=12, shrink=0.05),
    )


def add_scale_bar(ax, length_km: Optional[float] = None, location=(0.82, 0.05)):
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    width_m = xlim[1] - xlim[0]
    if length_km is None:
        target_m = width_m / 5
        steps = [1, 2, 5]
        exp = int(np.floor(np.log10(target_m)))
        base = 10 ** exp
        candidates = [s * base for s in steps]
        length_m = min(candidates, key=lambda c: abs(c - target_m))
    else:
        length_m = length_km * 1000

    x_start = xlim[0] + (xlim[1] - xlim[0]) * location[0]
    y_start = ylim[0] + (ylim[1] - ylim[0]) * location[1]

    ax.plot([x_start, x_start + length_m], [y_start, y_start], color="k", linewidth=3, zorder=100)
    ax.plot([x_start, x_start], [y_start - length_m * 0.003, y_start + length_m * 0.003], color="k", linewidth=3, zorder=100)
    ax.plot([x_start + length_m, x_start + length_m], [y_start - length_m * 0.003, y_start + length_m * 0.003], color="k", linewidth=3, zorder=100)
    ax.text(x_start + length_m / 2, y_start + length_m * 0.006, f"{int(length_m/1000)} km", ha="center", va="bottom", fontsize=9)


def plot_map(
    place: str,
    fig_size: Tuple[float, float],
    dpi: int,
    buffer_m: float,
    out_base: str,
    labels_language: str,
):
    print(f"Erzeuge Karte für: {place}")
    geocoded = geocode_bbox(place)
    bbox_wgs84 = geocoded["bbox_wgs84"]
    display_name = geocoded["display_name"]

    # In Web Mercator umrechnen und ggf. puffern (in Metern)
    minx, miny, maxx, maxy = bbox_wgs84_to_mercator(bbox_wgs84)
    if buffer_m and buffer_m > 0:
        minx -= buffer_m
        miny -= buffer_m
        maxx += buffer_m
        maxy += buffer_m

    print("Zeichne …")
    fig, ax = plt.subplots(1, 1, figsize=fig_size, dpi=dpi, constrained_layout=True)

    # Ausdehnung setzen (Web Mercator)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)

    # Dynamischen Zoom abschätzen (horizontal)
    fig_width_px = fig_size[0] * dpi
    bbox_width_m = maxx - minx
    target_res_m_per_px = bbox_width_m / max(fig_width_px, 1)
    zoom = int(round(math.log2(INITIAL_RESOLUTION_M_PER_PX / max(target_res_m_per_px, 1e-6))))
    zoom = max(0, min(19, zoom))

    # Basiskarte: aktuelle Esri World Imagery
    cx.add_basemap(ax, crs="EPSG:3857", source=cx.providers.Esri.WorldImagery, zoom=zoom)

    # Hillshade-Overlay für Höhenwirkung
    try:
        cx.add_basemap(ax, crs="EPSG:3857", source=cx.providers.Esri.WorldHillshade, alpha=0.35, zoom=zoom)
    except Exception as e:
        print(f"Warnung: Hillshade-Overlay nicht verfügbar: {e}")

    # Topo/Transport-Overlay für Infrastruktur und ggf. Konturen
    try:
        cx.add_basemap(ax, crs="EPSG:3857", source=cx.providers.Esri.WorldTransportation, alpha=0.6, zoom=zoom)
    except Exception as e:
        print(f"Warnung: Transportation-Overlay nicht verfügbar: {e}")
    try:
        cx.add_basemap(ax, crs="EPSG:3857", source=cx.providers.Esri.WorldTopoMap, alpha=0.25, zoom=zoom)
    except Exception as e:
        print(f"Warnung: Topo-Overlay nicht verfügbar: {e}")

    # Label-Overlay für hochwertige Beschriftungen
    try:
        cx.add_basemap(ax, crs="EPSG:3857", source=cx.providers.CartoDB.PositronOnlyLabels, alpha=0.9, zoom=zoom)
    except Exception as e:
        print(f"Warnung: Label-Overlay nicht verfügbar: {e}")

    # Schmuckelemente
    add_north_arrow(ax)
    add_scale_bar(ax)

    # Rahmen und Achsen aus
    ax.set_axis_off()

    # Titel/Metadaten
    today = datetime.date.today().isoformat()
    fig.suptitle(
        f"Schwarzatal – Satellit, Infrastruktur & Höhenmodell\nRegion: {display_name}\nDaten: Esri World Imagery, World Hillshade, World Transportation/Topo, OSM Labels – Stand {today}",
        fontsize=11,
    )

    ensure_dirs(os.path.dirname(out_base))

    out_png = f"{out_base}.png"
    out_pdf = f"{out_base}.pdf"

    print(f"Speichere {out_png} …")
    fig.savefig(out_png, dpi=dpi, bbox_inches="tight")

    print(f"Speichere {out_pdf} …")
    fig.savefig(out_pdf, dpi=dpi, bbox_inches="tight")

    print("Fertig.")


def main():
    parser = argparse.ArgumentParser(description="Erzeuge hochwertige Karte des Schwarzatals")
    parser.add_argument("--place", default="Stadt Schwarzatal, Thüringen, Deutschland", help="Ort/Region für die Karte (Geocoding über Nominatim)")
    parser.add_argument("--size", default="14x20", type=parse_size, help="Seitengröße in Zoll, z.B. 14x20")
    parser.add_argument("--dpi", default=300, type=int, help="Auflösung in DPI")
    parser.add_argument("--buffer-m", default=0.0, type=float, help="Zusätzlicher Puffer um die Region in Metern (Web Mercator)")
    parser.add_argument("--out", default="/workspace/output/schwarzatal_map", help="Basispfad ohne Endung für Export")
    parser.add_argument("--labels-language", default="de", help="Label-Sprache (informativ; Kachel-Labels sind mehrsprachig)")

    args = parser.parse_args()

    width_in, height_in = args.size
    plot_map(
        place=args.place,
        fig_size=(width_in, height_in),
        dpi=args.dpi,
        buffer_m=args.buffer_m,
        out_base=args.out,
        labels_language=args.labels_language,
    )


if __name__ == "__main__":
    main()