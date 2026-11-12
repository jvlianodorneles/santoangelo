"""Shared settings: the area we render, in SIRGAS 2000 / UTM zone 21S (EPSG:31981) meters."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BUILD = ROOT / "data" / "build"

# Santo Ângelo, RS, Brazil - Centro Histórico around Catedral Angelopolitana: 2.0 x 2.0 km.
# Catedral Angelopolitana sits at X=768531, Y=6865955 in UTM 21S (-28.3051, -54.2617).
XMIN, YMIN, XMAX, YMAX = 767500, 6865000, 769500, 6867000
CX, CY = (XMIN + XMAX) / 2, (YMIN + YMAX) / 2

# Downloads and ground textures come in square chunks of this many meters.
CHUNK = 500
NX, NY = int((XMAX - XMIN) / CHUNK), int((YMAX - YMIN) / CHUNK)

# Ground raster resolution in meters per pixel.
GROUND_RES = 0.25

# The compass directions the map is rendered from (render/run.mjs --look); the first is the one the viewer opens on.
VIEWS = (45, 135, 225, 315)


def write_area():
    """The renderer and the viewer read the area from here."""
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "area.json").write_text(
        json.dumps({"xmin": XMIN, "ymin": YMIN, "xmax": XMAX, "ymax": YMAX, "cx": CX, "cy": CY, "chunk": CHUNK, "nx": NX, "ny": NY})
    )

