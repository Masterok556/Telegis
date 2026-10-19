"""Collect a fixed EXPO/Mega OSM pedestrian graph; publish only complete snapshots.

python scripts/collect_walk_network.py
python scripts/collect_walk_network.py --reprocess-current
The query contains the fixed project coverage, never a user's position.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.geo import distance_m
from app.walking import WalkingNetwork
from scripts.collect_pois import CENTER, RADIUS_M, ENDPOINTS, fetch_overpass, write_json

EXCLUDED_HIGHWAYS = {"motorway", "motorway_link", "trunk", "trunk_link", "construction", "proposed", "raceway", "bus_guideway"}
WALK_HIGHWAYS = {"footway", "path", "pedestrian", "steps", "living_street", "residential", "service", "unclassified", "tertiary", "tertiary_link", "secondary", "secondary_link", "primary", "primary_link", "track", "road"}
PROHIBITED = {"no", "private", "customers", "customers_only", "permit", "delivery", "military", "agricultural", "forestry"}
PUBLIC_FOOT = {"yes", "designated", "permissive", "official"}


def build_query() -> str:
    return f'''[out:json][timeout:40];
way["highway"]["highway"!~"^(motorway|motorway_link|trunk|trunk_link|construction|proposed|raceway|bus_guideway)$"](around:{RADIUS_M},{CENTER[0]},{CENTER[1]});
(._;>;);
out body;'''


def accessible(tags: dict, *, node: bool = False) -> bool:
    """Conservative fixed policy; uncertain time-dependent access is excluded."""
    if tags.get("foot") in PROHIBITED | {"use_sidepath", "destination"} or tags.get("access") in {"no", "private"}:
        return False
    if tags.get("access") in PROHIBITED and tags.get("foot") not in PUBLIC_FOOT:
        return False
    if any(k in tags for k in ("foot:conditional", "access:conditional")):
        return False
    if node:
        if tags.get("locked") == "yes":
            return False
        if tags.get("barrier") in {"wall", "fence", "hedge", "retaining_wall"}:
            return False
        if tags.get("barrier") in {"gate", "lift_gate", "swing_gate", "turnstile"} and tags.get("foot") not in PUBLIC_FOOT and tags.get("access") not in PUBLIC_FOOT:
            return False
        return True
    highway = tags.get("highway")
    if highway in EXCLUDED_HIGHWAYS:
        return False
    if tags.get("construction") not in {None, "no"}:
        return False
    if tags.get("oneway:foot") not in {None, "yes", "1", "true", "-1", "reverse", "no", "0", "false"}:
        return False
    if highway not in WALK_HIGHWAYS and not (highway in {"cycleway", "bridleway"} and tags.get("foot") in PUBLIC_FOOT):
        return False
    if tags.get("indoor") == "yes" or tags.get("tunnel") == "yes":
        return False  # Interior/tunnel passage cannot be assumed available from this extract.
    if tags.get("sidewalk") in {"no", "none"} and highway in {"primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link"} and tags.get("foot") not in PUBLIC_FOOT:
        return False
    return True


def normalize(raw: dict) -> tuple[dict, dict]:
    if not isinstance(raw, dict) or not isinstance(raw.get("elements"), list) or raw.get("remark"):
        raise ValueError("Incomplete Overpass walking response")
    nodes, skipped = {}, Counter()
    for element in raw["elements"]:
        if element.get("type") != "node":
            continue
        if not accessible(element.get("tags", {}), node=True):
            skipped["restricted_node"] += 1
            continue
        try:
            point = float(element["lat"]), float(element["lon"])
            if distance_m(*CENTER, *point) > RADIUS_M:
                continue
            nodes[element["id"]] = point
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid OSM walking node") from None
    edges: dict[tuple[int, int], float] = {}
    ways = 0
    uncertain_sidewalk_ways = 0
    for element in raw["elements"]:
        if element.get("type") != "way":
            continue
        tags = element.get("tags", {})
        if not accessible(tags):
            skipped["restricted_or_nonwalkable_way"] += 1
            continue
        ids = element.get("nodes", [])
        added = False
        direction = tags.get("oneway:foot", "no")
        for source, target in zip(ids, ids[1:]):
            if source not in nodes or target not in nodes or source == target:
                continue
            length = round(distance_m(*nodes[source], *nodes[target]), 3)
            if length <= 0:
                continue
            if direction not in {"-1", "reverse"}:
                edges[source, target] = length
            if direction not in {"yes", "1", "true"}:
                edges[target, source] = length
            added = True
        if added:
            ways += 1
            if tags.get("highway") not in {"footway", "path", "pedestrian", "steps"} and not tags.get("sidewalk"):
                uncertain_sidewalk_ways += 1
    used = {node for edge in edges for node in edge}
    graph = {"schema_version": 1,
             "nodes": [[n, *nodes[n]] for n in sorted(used)],
             "edges": [[a, b, edges[a, b]] for a, b in sorted(edges)]}
    WalkingNetwork.from_payload(graph)
    stats = {"node_count": len(used), "directed_edge_count": len(edges), "way_count": ways,
             "ways_without_sidewalk_tag": uncertain_sidewalk_ways, "skipped": dict(skipped)}
    return graph, stats


def publish(raw: dict, output: Path, endpoint: str, query: str, collected_at: str) -> dict:
    graph, stats = normalize(raw)
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    snapshot = output / "snapshots" / snapshot_id
    snapshot.mkdir(parents=True)
    write_json(snapshot / "raw.json", raw)
    write_json(snapshot / "graph.json", graph)
    manifest = {
        "schema_version": 1, "snapshot_id": snapshot_id,
        "collected_at": collected_at, "source_data_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
        "source": "OpenStreetMap", "basis": "osm_walking_graph", "endpoint": endpoint,
        "request_method": "GET", "query": query,
        "license": "ODbL 1.0", "attribution": "© OpenStreetMap contributors",
        "license_url": "https://www.openstreetmap.org/copyright",
        "coverage": {"lat": CENTER[0], "lon": CENTER[1], "radius_m": RADIUS_M},
        "raw_sha256": hashlib.sha256((snapshot / "raw.json").read_bytes()).hexdigest(),
        "graph_sha256": hashlib.sha256((snapshot / "graph.json").read_bytes()).hexdigest(),
        "raw_elements": len(raw["elements"]), **stats,
        "limitations": [
            "Путь построен по связности OSM, без проверки на местности и без данных о временных перекрытиях.",
            "Подход к графу и к точке — отрезки до 120 м каждый; входы, заборы и проход через здания на них не проверены.",
            "У обычных улиц тротуары и переходы могут быть не описаны. Безопасность и доступность маршрута не подтверждены.",
            "Ступени разрешены; маршрут не предназначен для проверки доступности на коляске.",
        ],
    }
    WalkingNetwork.from_payload(graph, manifest)
    write_json(snapshot / "manifest.json", manifest)
    pointer = output / f".current-{uuid.uuid4().hex}.tmp"
    write_json(pointer, {"snapshot": f"snapshots/{snapshot_id}"})
    os.replace(pointer, output / "current.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "walking")
    parser.add_argument("--endpoint", action="append")
    parser.add_argument("--reprocess-current", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = args.output / ".collect.lock"
    try:
        handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print("Сбор пешеходного графа уже запущен.", file=sys.stderr)
        return 1
    os.close(handle)
    try:
        if args.reprocess_current:
            pointer = json.loads((args.output / "current.json").read_text(encoding="utf-8"))
            if not re.fullmatch(r"snapshots/[A-Za-z0-9_-]+", pointer["snapshot"]):
                raise ValueError("Invalid walking snapshot path")
            previous = args.output / pointer["snapshot"]
            metadata = json.loads((previous / "manifest.json").read_text(encoding="utf-8"))
            raw_body = (previous / "raw.json").read_bytes()
            if hashlib.sha256(raw_body).hexdigest() != metadata["raw_sha256"]:
                raise ValueError("Walking raw checksum mismatch")
            result = publish(json.loads(raw_body), args.output, metadata["endpoint"], metadata["query"], metadata["collected_at"])
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        query = build_query()
        for endpoint in args.endpoint or ENDPOINTS:
            if urllib.parse.urlsplit(endpoint).scheme != "https":
                print("Нужен HTTPS endpoint", file=sys.stderr)
                continue
            print(f"Сбор графа: {endpoint}; фиксированный радиус {RADIUS_M} м", flush=True)
            try:
                raw = fetch_overpass(endpoint, query, timeout=55)
                result = publish(raw, args.output, endpoint, query, datetime.now(timezone.utc).isoformat(timespec="seconds"))
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            except (OSError, ValueError) as exc:
                print(f"Сбор не выполнен: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        print("Предыдущий граф сохранён; новая версия не опубликована.", file=sys.stderr)
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
