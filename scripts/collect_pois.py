"""Collect a bounded OSM extract; publish a complete snapshot atomically.

Run from any directory: python scripts/collect_pois.py
Fetches with Python's standard library and validates with the backend's models.
No API key or user coordinates are involved.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.geo import distance_m
from app.data_store import load_snapshot

# This is the fixed collection extent, not a claimed POI or user location.
CENTER = (51.089, 71.419)
RADIUS_M = 3500
ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
CATEGORY_LABELS = {
    "cafe": "Кафе", "park": "Парк", "garden": "Сад",
    "playground": "Детская площадка", "museum": "Музей",
    "gallery": "Галерея", "attraction": "Достопримечательность",
    "viewpoint": "Смотровая площадка", "artwork": "Арт-объект",
    "monument": "Памятник", "memorial": "Мемориал", "mall": "Торговый центр",
}
PUBLIC_TAGS = {
    "name", "name:ru", "name:kk", "name:en", "amenity", "leisure", "tourism",
    "historic", "shop", "opening_hours", "website", "contact:website",
    "phone", "contact:phone", "addr:street", "addr:housenumber",
    "cuisine", "internet_access", "socket", "wheelchair", "outdoor_seating",
    "access", "fee", "description", "description:ru", "level", "indoor",
}


def build_query() -> str:
    extent = f"(around:{RADIUS_M},{CENTER[0]},{CENTER[1]})"
    return f'''[out:json][timeout:30];
(
 nwr["amenity"="cafe"]{extent};
 nwr["leisure"~"^(park|garden|playground)$"]{extent};
 nwr["tourism"~"^(museum|gallery|attraction|viewpoint|artwork)$"]{extent};
 nwr["historic"~"^(monument|memorial)$"]{extent};
 nwr["shop"="mall"]{extent};
);
out center tags;'''


def category_for(tags: dict) -> str | None:
    if tags.get("amenity") == "cafe":
        return "cafe"
    for key in ("leisure", "tourism", "historic", "shop"):
        value = tags.get(key)
        if value in CATEGORY_LABELS:
            return value
    return None


def coordinates(element: dict) -> tuple[float, float] | None:
    point = element if "lat" in element else element.get("center", {})
    try:
        lat, lon = float(point["lat"]), float(point["lon"])
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (KeyError, ValueError, TypeError):
        pass
    return None


def safe_http_url(value: str | None) -> str | None:
    if not value:
        return None
    p = urllib.parse.urlsplit(value)
    return value if p.scheme in {"https", "http"} and p.netloc else None


def normalize(raw: dict, collected_at: str) -> tuple[list[dict], list[dict], dict]:
    if raw.get("remark"):
        raise ValueError("Overpass вернул remark: ответ может быть неполным")
    if not isinstance(raw.get("elements"), list):
        raise ValueError("В ответе Overpass нет массива elements")
    pois, anchors, skipped = [], [], Counter()
    seen_ids: set[str] = set()
    # Prefer the richer of two nearby mappings of the same object (e.g. node + building).
    for element in sorted(raw["elements"], key=lambda e: (-len(e.get("tags", {})), str(e.get("type")), e.get("id", 0))):
        tags = element.get("tags", {})
        category = category_for(tags)
        name = tags.get("name:ru") or tags.get("name") or tags.get("name:en") or tags.get("name:kk")
        coord = coordinates(element)
        if not category or not name or not coord:
            skipped["missing_name_category_or_coordinates"] += 1
            continue
        if tags.get("access") in {"private", "no", "customers_only"}:
            skipped["restricted_access"] += 1
            continue
        if distance_m(*CENTER, *coord) > RADIUS_M:
            skipped["center_outside_collection_extent"] += 1
            continue
        osm_type, osm_id = element.get("type"), element.get("id")
        if osm_type not in {"node", "way", "relation"} or not isinstance(osm_id, int):
            skipped["invalid_osm_id"] += 1
            continue
        poi_id = f"osm_{osm_type}_{osm_id}"
        if poi_id in seen_ids:
            skipped["duplicate_id"] += 1
            continue
        seen_ids.add(poi_id)
        # Conservative spatial dedup: same category, name and <=20m; retain different levels.
        canonical_name = re.sub(r"[^\w]", "", str(name).casefold())
        duplicate = next((p for p in pois
            if p["category"] == category
            and (re.sub(r"[^\w]", "", p["name"].casefold()) == canonical_name or category == "mall")
            and p["tags"].get("level") == tags.get("level")
            and distance_m(p["lat"], p["lon"], *coord) < 20), None)
        if duplicate:
            skipped["duplicate_name_nearby"] += 1
            continue
        source_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
        description = f"{CATEGORY_LABELS[category]}. Название в OpenStreetMap: {name}."
        if tags.get("cuisine"):
            description += f" Кухня по данным OSM: {tags['cuisine']}."
        poi = {
            "poi_id": poi_id, "name": str(name), "lat": coord[0], "lon": coord[1],
            "category": category, "description": description,
            "tags": {k: str(v) for k, v in tags.items() if k in PUBLIC_TAGS},
            "opening_hours": tags.get("opening_hours") or None,
            "phone": tags.get("contact:phone") or tags.get("phone") or None,
            "website": safe_http_url(tags.get("contact:website") or tags.get("website")),
            "rating": None, "source": "OpenStreetMap", "source_url": source_url,
            "collected_at": collected_at,
            "coordinate_kind": "point" if osm_type == "node" else "bounding_box_center",
            "confirmed_features": {
                "wifi": True if tags.get("internet_access") == "wlan" else (False if tags.get("internet_access") == "no" else None),
                "socket": True if tags.get("socket") == "yes" else (False if tags.get("socket") == "no" else None),
                "wheelchair": True if tags.get("wheelchair") == "yes" else (False if tags.get("wheelchair") == "no" else None),
                # OSM has no dependable quietness evidence in this bounded collection.
                "quiet": None,
            },
        }
        pois.append(poi)
        all_names = " ".join(str(tags.get(k, "")) for k in ("name", "name:en", "name:ru", "name:kk"))
        normalized_name = re.sub(r"[^\w]", "", all_names.casefold())
        is_mega = category == "mall" and ("megasilkway" in normalized_name or "мегасилк" in normalized_name)
        is_nur = category in {"museum", "attraction"} and any(t in normalized_name for t in ("нуралем", "нұрәлем", "nuralem"))
        if is_mega or is_nur:
            anchors.append({"id": poi_id, "name": str(name), "lat": coord[0], "lon": coord[1],
                            "source_url": source_url, "coordinate_kind": poi["coordinate_kind"]})
    if not pois:
        raise ValueError("После проверки не осталось подходящих именованных POI")
    if len(anchors) < 2:
        # Supplement with an actual nearby park/landmark instead of inventing EXPO coordinates.
        chosen = sorted(pois, key=lambda p: (p["category"] not in {"park", "garden", "attraction", "museum"}, distance_m(*CENTER, p["lat"], p["lon"])))
        for p in chosen:
            if any(distance_m(p["lat"], p["lon"], a["lat"], a["lon"]) < 100 for a in anchors):
                continue
            anchors.append({k: p[k] for k in ("name", "lat", "lon", "source_url", "coordinate_kind")} | {"id": p["poi_id"]})
            if len(anchors) >= 2:
                break
    # Prefer the mall then the museum; duplicate anchor labels are unnecessary.
    anchors.sort(key=lambda a: ("mega" not in a["name"].lower(), a["name"]))
    return sorted(pois, key=lambda p: p["poi_id"]), anchors[:3], dict(skipped)


def fetch_overpass(endpoint: str, query: str, timeout: float = 45) -> dict:
    # Bounded query fits comfortably in a URL. GET also works behind proxies that reject POST.
    url = endpoint + "?" + urllib.parse.urlencode({"data": query})
    request = urllib.request.Request(url, headers={
        "User-Agent": "Telegis/1.0 (bounded POI collection; no tracking)",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(12_000_001)
    if len(body) > 12_000_000:
        raise ValueError("Ответ превысил 12 MB")
    raw = json.loads(body)
    if not isinstance(raw, dict) or not isinstance(raw.get("elements"), list) or raw.get("remark"):
        raise ValueError("Overpass вернул неполный или некорректный ответ")
    return raw


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(raw: dict, output: Path, endpoint: str, query: str, collected_at: str) -> dict:
    pois, locations, skipped = normalize(raw, collected_at)
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    snapshot = output / "snapshots" / snapshot_id
    snapshot.mkdir(parents=True)
    write_json(snapshot / "raw.json", raw)
    write_json(snapshot / "pois.json", pois)
    write_json(snapshot / "locations.json", locations)
    raw_hash = hashlib.sha256((snapshot / "raw.json").read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1, "snapshot_id": snapshot_id, "collected_at": collected_at,
        "source": "OpenStreetMap", "endpoint": endpoint, "request_method": "GET",
        "source_data_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
        "license": "ODbL 1.0", "attribution": "© OpenStreetMap contributors",
        "license_url": "https://www.openstreetmap.org/copyright",
        "coverage": {"name": "EXPO / Mega Silk Way, Астана", "lat": CENTER[0], "lon": CENTER[1], "radius_m": RADIUS_M},
        "query": query, "raw_sha256": raw_hash, "raw_elements": len(raw["elements"]),
        "poi_count": len(pois), "categories": dict(Counter(p["category"] for p in pois)),
        "skipped": skipped, "locations_count": len(locations),
    }
    write_json(snapshot / "manifest.json", manifest)
    # A complete JSON export can still contain invalid types or inconsistent metadata.
    # Validate exactly as the API does before replacing the last working version.
    load_snapshot(snapshot)
    # Only this pointer is switched. A crash before it leaves the old dataset intact.
    pointer_tmp = output / f".current-{uuid.uuid4().hex}.tmp"
    write_json(pointer_tmp, {"snapshot": f"snapshots/{snapshot_id}"})
    os.replace(pointer_tmp, output / "current.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    parser.add_argument("--endpoint", action="append", help="Explicit HTTPS Overpass endpoint; may repeat")
    parser.add_argument("--reprocess-current", action="store_true", help="Rebuild from saved raw response, preserving original collection timestamp; no network")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = args.output / ".collect.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print("Сбор уже запущен (data/.collect.lock).", file=sys.stderr)
        return 1
    os.close(handle)
    try:
        query = build_query()
        if args.reprocess_current:
            pointer = json.loads((args.output / "current.json").read_text(encoding="utf-8"))
            if not re.fullmatch(r"snapshots/[A-Za-z0-9_-]+", pointer["snapshot"]):
                raise ValueError("Некорректный путь снимка")
            previous = args.output / pointer["snapshot"]
            manifest = json.loads((previous / "manifest.json").read_text(encoding="utf-8"))
            raw = json.loads((previous / "raw.json").read_text(encoding="utf-8"))
            result = publish(raw, args.output, manifest["endpoint"], manifest["query"], manifest["collected_at"])
            print("Офлайн-пересборка: время исходного сбора сохранено.", flush=True)
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
            return 0
        for i, endpoint in enumerate(args.endpoint or ENDPOINTS):
            if urllib.parse.urlsplit(endpoint).scheme != "https":
                print("Нужен HTTPS endpoint", file=sys.stderr)
                continue
            print(f"Запрос {i+1}: {endpoint}; район EXPO, радиус {RADIUS_M} м", flush=True)
            try:
                raw = fetch_overpass(endpoint, query)
                timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
                result = publish(raw, args.output, endpoint, query, timestamp)
                print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
                return 0
            except (OSError, ValueError, urllib.error.URLError) as exc:
                # No user data or keys are part of this collector.
                print(f"Сбор не выполнен: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                if i == 0:
                    time.sleep(1)
        print("Новая версия не опубликована. Предыдущий датасет сохранён.", file=sys.stderr)
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
