"""Offline paths along a collected OSM walking graph, with explicit snap connectors.

This is mapped connectivity, not a guarantee of a safe or accessible entrance.
No network requests or user-coordinate persistence happen here.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import heapq
import json
import math
from pathlib import Path
import re
from threading import RLock

from app.geo import distance_m

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "data" / "walking"
MAX_SNAP_M = 120


@dataclass(frozen=True)
class WalkingLeg:
    distance_m: int
    coordinates: list[list[float]]  # GeoJSON order: longitude, latitude
    connector_m: int


class WalkingNetwork:
    """Directed graph; pedestrian ways normally contribute both edge directions."""

    def __init__(self, nodes: dict[int, tuple[float, float]],
                 edges: list[tuple[int, int, float]], metadata: dict):
        self.nodes = nodes
        self.metadata = dict(metadata)
        self.metadata.update({"basis": "osm_walking_graph", "max_snap_m": MAX_SNAP_M})
        self._adj: dict[int, list[tuple[int, float]]] = {n: [] for n in nodes}
        self._grid: dict[tuple[int, int], list[int]] = {}
        for node_id, (lat, lon) in nodes.items():
            self._grid.setdefault((math.floor(lat * 1000), math.floor(lon * 1000)), []).append(node_id)
        for source, target, length in edges:
            self._adj[source].append((target, length))
        # Cache graph-node trees only, never exact user coordinates or queries.
        self._trees: OrderedDict[int, tuple[dict[int, float], dict[int, int]]] = OrderedDict()
        self._tree_lock = RLock()

    @classmethod
    def load(cls, root_path: Path = DEFAULT_ROOT) -> "WalkingNetwork":
        root_path = Path(root_path)
        pointer = json.loads((root_path / "current.json").read_text(encoding="utf-8"))
        relative = pointer.get("snapshot", "")
        if not isinstance(relative, str) or not re.fullmatch(r"snapshots/[A-Za-z0-9_-]+", relative):
            raise ValueError("Invalid walking snapshot path")
        snapshot = (root_path / relative).resolve()
        if not snapshot.is_relative_to(root_path.resolve()):
            raise ValueError("Walking snapshot escapes data directory")
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("snapshot_id") != snapshot.name or manifest.get("schema_version") != 1:
            raise ValueError("Walking snapshot identity mismatch")
        raw = (snapshot / "raw.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest.get("raw_sha256"):
            raise ValueError("Walking raw checksum mismatch")
        if len(json.loads(raw).get("elements", [])) != manifest.get("raw_elements"):
            raise ValueError("Walking raw element count mismatch")
        body = (snapshot / "graph.json").read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest.get("graph_sha256"):
            raise ValueError("Walking graph checksum mismatch")
        return cls.from_payload(json.loads(body), manifest)

    @classmethod
    def from_payload(cls, payload: dict, metadata: dict | None = None) -> "WalkingNetwork":
        """Validate serialized graph; also useful for small deterministic fixtures."""
        nodes: dict[int, tuple[float, float]] = {}
        for row in payload.get("nodes", []):
            if len(row) != 3 or not isinstance(row[0], int) or isinstance(row[0], bool):
                raise ValueError("Invalid walking node")
            node_id, lat, lon = row
            if node_id in nodes or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (lat, lon)):
                raise ValueError("Invalid/duplicate walking coordinate")
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("Invalid walking coordinate range")
            nodes[node_id] = (float(lat), float(lon))
        edges = []
        for row in payload.get("edges", []):
            if len(row) != 3:
                raise ValueError("Invalid walking edge")
            source, target, length = row
            if source not in nodes or target not in nodes or source == target:
                raise ValueError("Unknown walking node")
            if not isinstance(length, (int, float)) or not math.isfinite(length) or length <= 0:
                raise ValueError("Invalid walking distance")
            # Edges are adjacent source way vertices, never arbitrary distance estimates.
            expected = distance_m(*nodes[source], *nodes[target])
            if abs(expected - length) > 0.1:
                raise ValueError("Walking edge length differs from coordinates")
            edges.append((source, target, float(length)))
        if not nodes or not edges:
            raise ValueError("Empty walking graph")
        meta = metadata or {}
        if meta.get("node_count", len(nodes)) != len(nodes) or meta.get("directed_edge_count", len(edges)) != len(edges):
            raise ValueError("Walking graph counts differ")
        return cls(nodes, edges, meta)

    def _snap(self, point: tuple[float, float]) -> tuple[int, float] | None:
        if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
            return None
        if not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180):
            return None
        nearest_id, nearest_m = None, float("inf")
        lat_cell, lon_cell = math.floor(point[0] * 1000), math.floor(point[1] * 1000)
        # Cell shortlist is conservative; haversine below enforces the actual snap limit.
        lon_cells = math.ceil(MAX_SNAP_M / (111_000 * 0.001 * max(0.01, math.cos(math.radians(point[0]))))) + 1
        candidates = (node_id for lat in range(lat_cell - 2, lat_cell + 3)
                      for lon in range(lon_cell - lon_cells, lon_cell + lon_cells + 1)
                      for node_id in self._grid.get((lat, lon), ()))
        for node_id in candidates:
            coord = self.nodes[node_id]
            d = distance_m(*point, *coord)
            if d < nearest_m:
                nearest_id, nearest_m = node_id, d
        return (nearest_id, nearest_m) if nearest_id is not None and nearest_m <= MAX_SNAP_M else None

    def _tree(self, start: int) -> tuple[dict[int, float], dict[int, int]]:
        with self._tree_lock:
            if start in self._trees:
                self._trees.move_to_end(start)
                return self._trees[start]
        distances, previous = {start: 0.0}, {}
        queue = [(0.0, start)]
        while queue:
            current_distance, node = heapq.heappop(queue)
            if current_distance != distances[node]:
                continue
            for other, length in self._adj[node]:
                alternative = current_distance + length
                if alternative < distances.get(other, float("inf")):
                    distances[other], previous[other] = alternative, node
                    heapq.heappush(queue, (alternative, other))
        with self._tree_lock:
            self._trees[start] = distances, previous
            if len(self._trees) > 16:
                self._trees.popitem(last=False)
        return distances, previous

    def route(self, start: tuple[float, float], end: tuple[float, float]) -> WalkingLeg | None:
        first, last = self._snap(start), self._snap(end)
        if first is None or last is None:
            return None
        if start == end:
            return WalkingLeg(0, [[start[1], start[0]], [end[1], end[0]]], 0)
        first_id, first_connector = first
        last_id, last_connector = last
        distances, previous = self._tree(first_id)
        if last_id not in distances:
            return None
        ids = [last_id]
        while ids[-1] != first_id:
            ids.append(previous[ids[-1]])
        ids.reverse()
        points = [start] + [self.nodes[node_id] for node_id in ids] + [end]
        coordinates: list[list[float]] = []
        for lat, lon in points:
            point = [lon, lat]
            if not coordinates or point != coordinates[-1]:
                coordinates.append(point)
        # A zero-length leg needs two equal positions to remain valid LineString geometry.
        if len(coordinates) == 1:
            coordinates.append(coordinates[0][:])
        connector = first_connector + last_connector
        return WalkingLeg(math.ceil(distances[last_id] + connector), coordinates, math.ceil(connector))
