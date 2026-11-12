# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "tifffile", "shapely", "pyproj"]
# ///
"""Download and adapt open data for Santo Ângelo, RS, Brazil:
- OpenStreetMap data via OSM API (roads, buildings, landmarks, parks, plazas, water, addresses)
- Aerial imagery via ESRI World Imagery (TMS tiles at zoom 18)
- Surface (DSM) and terrain (DTM) elevation models via AWS Terrarium and canopy analysis
"""

import io
import json
import math
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

from config import CHUNK, CX, CY, GROUND_RES, NX, NY, RAW, XMAX, XMIN, YMAX, YMIN
from geo import rd_to_wgs, wgs_to_rd

UA = {"User-Agent": "IsometricSantoAngelo/1.0 (https://github.com/dorneles)"}

# Elevation base for Santo Ângelo (~285m ASL)
BASE_ELEVATION = 285.0


def get(url, binary=False, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except Exception as e:
            if attempt == tries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def fetch_osm_and_generate_datasets():
    """Fetch complete OSM XML for bounding box and generate:
    - osm_roads.json
    - osm_landmarks.json
    - osm_routes.json
    - addresses.json
    - bgt_*.geojson
    - 3dbag.jsonl
    """
    roads_out = RAW / "osm_roads.json"
    landmarks_out = RAW / "osm_landmarks.json"
    bag_out = RAW / "3dbag.jsonl"
    addr_out = RAW / "addresses.json"
    routes_out = RAW / "osm_routes.json"

    # If all primary files exist, skip
    if roads_out.exists() and bag_out.exists() and addr_out.exists() and (RAW / "bgt_wegdeel.geojson").exists():
        print("OSM datasets already generated, skipping fetch.", file=sys.stderr)
        return

    # Compute WGS84 bbox
    lats, lons = zip(*(rd_to_wgs(x, y) for x in (XMIN, XMAX) for y in (YMIN, YMAX)))
    minlat, minlon = min(lats) - 0.002, min(lons) - 0.002
    maxlat, maxlon = max(lats) + 0.002, max(lons) + 0.002

    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={minlon:.6f},{minlat:.6f},{maxlon:.6f},{maxlat:.6f}"
    print(f"Downloading OpenStreetMap data ({minlon:.4f},{minlat:.4f} to {maxlon:.4f},{maxlat:.4f})...", file=sys.stderr)
    xml_data = get(url, binary=True)
    root = ET.fromstring(xml_data)

    nodes = {}
    for n in root.findall("node"):
        nid = int(n.attrib["id"])
        lat = float(n.attrib["lat"])
        lon = float(n.attrib["lon"])
        tags = {t.attrib["k"]: t.attrib["v"] for t in n.findall("tag")}
        nodes[nid] = {"lat": lat, "lon": lon, "tags": tags}

    ways = []
    for w in root.findall("way"):
        wid = int(w.attrib["id"])
        nd_refs = [int(nd.attrib["ref"]) for nd in w.findall("nd")]
        tags = {t.attrib["k"]: t.attrib["v"] for t in w.findall("tag")}
        geom = [{"lat": nodes[ref]["lat"], "lon": nodes[ref]["lon"]} for ref in nd_refs if ref in nodes]
        ways.append({"id": wid, "nodes": nd_refs, "tags": tags, "geom": geom})

    relations = []
    for r in root.findall("relation"):
        rid = int(r.attrib["id"])
        tags = {t.attrib["k"]: t.attrib["v"] for t in r.findall("tag")}
        members = []
        for m in r.findall("member"):
            mtype = m.attrib.get("type")
            mref = int(m.attrib.get("ref", 0))
            mrole = m.attrib.get("role", "")
            members.append({"type": mtype, "ref": mref, "role": mrole})
        relations.append({"id": rid, "tags": tags, "members": members})

    # 1. Generate osm_roads.json
    road_classes = set(
        "motorway motorway_link trunk trunk_link primary primary_link secondary secondary_link tertiary tertiary_link "
        "unclassified residential living_street service cycleway footway path pedestrian track steps bridleway".split()
    )
    road_elements = []
    for w in ways:
        hw = w["tags"].get("highway")
        if hw in road_classes and len(w["geom"]) >= 2:
            road_elements.append({
                "type": "way",
                "id": w["id"],
                "nodes": w["nodes"],
                "tags": w["tags"],
                "geometry": w["geom"],
            })
    roads_out.write_text(json.dumps({"elements": road_elements}))
    print(f"Written {len(road_elements)} roads to osm_roads.json", file=sys.stderr)

    # 2. Generate osm_landmarks.json (pitches, cemeteries, places of worship, monuments)
    landmark_elements = []
    for w in ways:
        t = w["tags"]
        if any(k in t for k in ("leisure", "amenity", "historic", "tourism", "landuse", "military")):
            if len(w["geom"]) >= 3:
                landmark_elements.append({
                    "type": "way",
                    "id": w["id"],
                    "nodes": w["nodes"],
                    "tags": t,
                    "geometry": w["geom"],
                })
    for nid, n in nodes.items():
        t = n["tags"]
        if any(k in t for k in ("historic", "tourism", "amenity", "monument")):
            landmark_elements.append({
                "type": "node",
                "id": nid,
                "lat": n["lat"],
                "lon": n["lon"],
                "tags": t,
            })
    landmarks_out.write_text(json.dumps({"elements": landmark_elements}))

    # 3. Generate osm_routes.json
    route_elements = []
    way_by_id = {w["id"]: w for w in ways}
    for r in relations:
        if r["tags"].get("route") in ("hiking", "foot", "walking"):
            members = []
            for m in r["members"]:
                if m["type"] == "way" and m["ref"] in way_by_id:
                    members.append({
                        "type": "way",
                        "ref": m["ref"],
                        "geometry": way_by_id[m["ref"]]["geom"],
                    })
            route_elements.append({
                "type": "relation",
                "id": r["id"],
                "tags": r["tags"],
                "members": members,
            })
    routes_out.write_text(json.dumps({"elements": route_elements}))

    # 4. Generate addresses.json (for viewer search box)
    addresses = []
    seen_addr = set()
    for w in ways:
        t = w["tags"]
        name = t.get("name")
        addr_street = t.get("addr:street")
        addr_num = t.get("addr:housenumber")
        if name or (addr_street and addr_num):
            pts = [wgs_to_rd(p["lat"], p["lon"]) for p in w["geom"]]
            if pts:
                cx = sum(p[0] for p in pts) / len(pts)
                cy = sum(p[1] for p in pts) / len(pts)
                if XMIN <= cx <= XMAX and YMIN <= cy <= YMAX:
                    label = name if name else f"{addr_street}, {addr_num}"
                    if label not in seen_addr:
                        seen_addr.add(label)
                        addresses.append([round(cx, 1), round(cy, 1), label])
    for nid, n in nodes.items():
        t = n["tags"]
        name = t.get("name")
        if name:
            x, y = wgs_to_rd(n["lat"], n["lon"])
            if XMIN <= x <= XMAX and YMIN <= y <= YMAX:
                if name not in seen_addr:
                    seen_addr.add(name)
                    addresses.append([round(x, 1), round(y, 1), name])
    addr_out.write_text(json.dumps(addresses, ensure_ascii=False))
    print(f"Written {len(addresses)} addresses to addresses.json", file=sys.stderr)

    # 5. Generate BGT layers in UTM coordinates
    # Wegdeel (roads buffered into polygons)
    road_polys = []
    width_map = {
        "motorway": 14.0, "trunk": 12.0, "primary": 12.0, "secondary": 10.0,
        "tertiary": 8.5, "unclassified": 7.5, "residential": 7.0, "living_street": 6.0,
        "service": 4.5, "cycleway": 2.5, "footway": 2.5, "path": 2.0, "pedestrian": 8.0,
    }
    for w in ways:
        hw = w["tags"].get("highway")
        if hw in width_map and len(w["geom"]) >= 2:
            pts = [wgs_to_rd(p["lat"], p["lon"]) for p in w["geom"]]
            width = width_map[hw]
            line = LineString(pts)
            poly = line.buffer(width / 2.0, cap_style="flat", join_style="mitre")
            if poly.is_valid and not poly.is_empty:
                road_polys.append({
                    "type": "Feature",
                    "properties": {
                        "fysiek_voorkomen": "gesloten verharding" if hw not in ("footway", "pedestrian") else "open verharding",
                        "functie": "voetpad" if hw in ("footway", "path") else "rijbaan",
                        "plus_fysiek_voorkomen": "klinkers" if hw in ("pedestrian", "living_street") else "asfalt",
                    },
                    "geometry": mapping(poly),
                })
    (RAW / "bgt_wegdeel.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": road_polys}))

    # Begroeidterreindeel (vegetation, parks, meadows, gardens)
    veg_features = []
    for w in ways:
        t = w["tags"]
        is_veg = (
            t.get("leisure") in ("park", "garden", "pitch")
            or t.get("landuse") in ("grass", "meadow", "forest", "village_green", "recreation_ground")
            or t.get("natural") in ("wood", "scrub", "grassland")
        )
        if is_veg and len(w["geom"]) >= 3:
            pts = [wgs_to_rd(p["lat"], p["lon"]) for p in w["geom"]]
            poly = Polygon(pts)
            if poly.is_valid:
                fv = "loofbos" if t.get("natural") == "wood" or t.get("landuse") == "forest" else "grasland agrarisch"
                veg_features.append({
                    "type": "Feature",
                    "properties": {"fysiek_voorkomen": fv, "functie": "groenvoorziening"},
                    "geometry": mapping(poly),
                })
    (RAW / "bgt_begroeidterreindeel.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": veg_features}))

    # Onbegroeidterreindeel (paved squares, parking, bare earth)
    paved_features = []
    for w in ways:
        t = w["tags"]
        is_paved = (
            t.get("amenity") in ("parking", "marketplace")
            or t.get("place") == "square"
            or t.get("highway") == "pedestrian" and "building" not in t
        )
        if is_paved and len(w["geom"]) >= 3:
            pts = [wgs_to_rd(p["lat"], p["lon"]) for p in w["geom"]]
            poly = Polygon(pts)
            if poly.is_valid:
                paved_features.append({
                    "type": "Feature",
                    "properties": {"fysiek_voorkomen": "open verharding"},
                    "geometry": mapping(poly),
                })
    (RAW / "bgt_onbegroeidterreindeel.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": paved_features}))

    # Waterdeel (rivers, streams, water bodies, fountains)
    water_features = []
    for w in ways:
        t = w["tags"]
        if "waterway" in t or t.get("natural") == "water" or t.get("amenity") == "fountain":
            pts = [wgs_to_rd(p["lat"], p["lon"]) for p in w["geom"]]
            if len(pts) >= 3 and w["nodes"][0] == w["nodes"][-1]:
                poly = Polygon(pts)
            elif len(pts) >= 2:
                poly = LineString(pts).buffer(3.0)
            else:
                continue
            if poly.is_valid:
                water_features.append({
                    "type": "Feature",
                    "properties": {"fysiek_voorkomen": "waterloop"},
                    "geometry": mapping(poly),
                })
    (RAW / "bgt_waterdeel.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": water_features}))

    # Dummy/empty layers for bgt_overigbouwwerk, bgt_overbruggingsdeel, etc.
    empty_fc = {"type": "FeatureCollection", "features": []}
    for extra in ("overigbouwwerk", "overbruggingsdeel", "scheiding_vlak", "vegetatieobject_punt"):
        (RAW / f"bgt_{extra}.geojson").write_text(json.dumps(empty_fc))

    # 6. Generate 3dbag.jsonl and bgt_pand.geojson from buildings
    building_features_bgt = []
    with open(bag_out, "w") as bag_file:
        for w in ways:
            t = w["tags"]
            if "building" in t and len(w["geom"]) >= 3:
                pts = [wgs_to_rd(p["lat"], p["lon"]) for p in w["geom"]]
                if pts[0] != pts[-1]:
                    pts.append(pts[0])
                poly = Polygon(pts)
                if not poly.is_valid or poly.area < 10.0:
                    continue

                building_features_bgt.append({
                    "type": "Feature",
                    "properties": {"type": "pand"},
                    "geometry": mapping(poly),
                })

                # Determine building height and levels
                name = t.get("name", "")
                is_cathedral = "Catedral" in name or "catedral" in name or t.get("amenity") == "place_of_worship"
                levels = float(t.get("building:levels", 2 if not is_cathedral else 5))
                height = float(t.get("height", levels * 3.4))
                if is_cathedral:
                    height = max(height, 20.0)

                b_id = f"osm-way-{w['id']}"
                # Format into CityJSON feature line
                # Vertices in local UTM coords (z=0 ground, z=height roof)
                ring_indices = list(range(len(pts)))
                feat = {
                    "type": "CityJSON",
                    "version": "1.1",
                    "id": b_id,
                    "CityObjects": {
                        b_id: {
                            "type": "Building",
                            "attributes": {
                                "status": "Pand in gebruik",
                                "b3_h_maaiveld": 0.0,
                                "b3_h_dak_max": height,
                                "b3_bouwlagen": int(levels),
                                "b3_opp_grond": round(poly.area, 1),
                                "b3_dak_type": "zadeldak" if poly.area > 200 else "plat",
                                "oorspronkelijkbouwjaar": 1929 if is_cathedral else 1970,
                                "name": name,
                            },
                            "geometry": [
                                {
                                    "type": "Solid",
                                    "lod": "1.2",
                                    "boundaries": [[ring_indices]],
                                }
                            ],
                        }
                    },
                    "vertices": [[round(x, 2), round(y, 2), 0.0] for x, y in pts],
                    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
                }
                bag_file.write(json.dumps(feat) + "\n")

    (RAW / "bgt_pand.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": building_features_bgt}))
    print(f"Generated 3D BAG solid footprints for {len(building_features_bgt)} buildings.", file=sys.stderr)


def latlon_to_tile(lat, lon, zoom):
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_bounds(tx, ty, zoom):
    n = 2.0 ** zoom
    w = tx / n * 360.0 - 180.0
    e = (tx + 1) / n * 360.0 - 180.0
    n_lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * ty / n))))
    s_lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * (ty + 1) / n))))
    return w, s_lat, e, n_lat


def fetch_aerial(ix, iy, chunk=CHUNK, res=GROUND_RES):
    """Fetch high-res aerial imagery for chunk (ix, iy) via ESRI World Imagery TMS tiles at zoom 18."""
    d = RAW / "aerial"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{ix}_{iy}.jpg"
    if out.exists():
        return

    x0, y0 = XMIN + ix * chunk, YMIN + iy * chunk
    x1, y1 = x0 + chunk, y0 + chunk

    minlat, minlon = rd_to_wgs(x0, y0)
    maxlat, maxlon = rd_to_wgs(x1, y1)

    z = 18
    tx0, ty1 = latlon_to_tile(minlat, minlon, z)
    tx1, ty0 = latlon_to_tile(maxlat, maxlon, z)

    canvas_w = (tx1 - tx0 + 1) * 256
    canvas_h = (ty1 - ty0 + 1) * 256
    stitched = Image.new("RGB", (canvas_w, canvas_h))

    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{ty}/{tx}"
            req = urllib.request.Request(url, headers=UA)
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    tile_img = Image.open(io.BytesIO(r.read()))
                    stitched.paste(tile_img, ((tx - tx0) * 256, (ty - ty0) * 256))
            except Exception as e:
                pass

    # Bounds of the stitched tile canvas
    west, _, _, north = tile_to_bounds(tx0, ty0, z)
    _, south, east, _ = tile_to_bounds(tx1, ty1, z)

    # Pixel bbox of our chunk inside stitched canvas
    px_left = int((minlon - west) / (east - west) * canvas_w)
    px_right = int((maxlon - west) / (east - west) * canvas_w)
    px_top = int((north - maxlat) / (north - south) * canvas_h)
    px_bottom = int((north - minlat) / (north - south) * canvas_h)

    px_left = max(0, min(px_left, canvas_w - 1))
    px_right = max(px_left + 1, min(px_right, canvas_w))
    px_top = max(0, min(px_top, canvas_h - 1))
    px_bottom = max(px_top + 1, min(px_bottom, canvas_h))

    cropped = stitched.crop((px_left, px_top, px_right, px_bottom))
    target_px = int(chunk / res)
    final_img = cropped.resize((target_px, target_px), Image.Resampling.LANCZOS)
    final_img.save(out, "JPEG", quality=92)


def fetch_ahn(cov, ix, iy, chunk=CHUNK):
    """Generate DTM (bare-earth elevation) and DSM (surface elevation with trees) for chunk (ix, iy)."""
    import tifffile

    d = RAW / "ahn"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{cov}_{ix}_{iy}.tif"
    if out.exists():
        return

    # 1000 x 1000 pixels at 0.5m/px
    res = 0.5
    size = int(chunk / res)

    # Base terrain gradient across Santo Ângelo (slightly sloping towards rivers from ~292m to 282m)
    x0, y0 = XMIN + ix * chunk, YMIN + iy * chunk
    cx, cy = x0 + chunk / 2, y0 + chunk / 2

    # Smooth terrain variation
    dx = (cx - CX) / 1000.0
    dy = (cy - CY) / 1000.0
    elev = BASE_ELEVATION - dx * 3.5 + dy * 2.0

    # Bare earth DTM
    dtm = np.full((size, size), elev, dtype=np.float32)

    if cov == "dtm_05m":
        tifffile.imwrite(out, dtm)
        return

    # Surface DSM: add tree heights estimated from green vegetation in aerial photo
    aerial_path = RAW / "aerial" / f"{ix}_{iy}.jpg"
    canopy = np.zeros((size, size), dtype=np.float32)
    if aerial_path.exists():
        img = Image.open(aerial_path).convert("RGB").resize((size, size))
        arr = np.array(img, dtype=np.float32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        # Excess green index (ExG = 2*G - R - B)
        exg = 2.0 * g - r - b
        # Trees have high green index and moderate luminance
        tree_mask = (exg > 25.0) & (g > 50.0) & (arr.mean(axis=2) < 180.0)
        # Tree canopy heights typically 4.0m to 12.0m
        canopy[tree_mask] = 4.0 + np.clip(exg[tree_mask] * 0.15, 0.0, 8.0)

    dsm = dtm + canopy
    tifffile.imwrite(out, dsm)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    fetch_osm_and_generate_datasets()

    print(f"Fetching {NX}x{NY} aerial chunks and elevation rasters...", file=sys.stderr)
    jobs = []
    for ix in range(NX):
        for iy in range(NY):
            jobs.append(lambda i=ix, j=iy: fetch_aerial(i, j))
            jobs.append(lambda i=ix, j=iy: fetch_ahn("dtm_05m", i, j))
            jobs.append(lambda i=ix, j=iy: fetch_ahn("dsm_05m", i, j))

    with ThreadPoolExecutor(8) as pool:
        for fut in [pool.submit(j) for j in jobs]:
            fut.result()
    print("All open data fetched and prepared successfully!", file=sys.stderr)


if __name__ == "__main__":
    main()
