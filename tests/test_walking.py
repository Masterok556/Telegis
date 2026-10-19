from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest

from app.geo import distance_m
from app.walking import WalkingNetwork
from scripts.collect_walk_network import accessible, normalize, publish


def graph_fixture():
    # The mapped connection makes an L-shaped detour; a diagonal would be invented.
    nodes = {1: (51.089, 71.419), 2: (51.090, 71.419), 3: (51.090, 71.420)}
    edges = [(a, b, distance_m(*nodes[a], *nodes[b])) for a, b in ((1, 2), (2, 1), (2, 3), (3, 2))]
    return WalkingNetwork(nodes, edges, {})


def raw_fixture(tags=None, *, node_tags=None):
    return {"osm3s": {"timestamp_osm_base": "2026-10-19T00:00:00Z"}, "elements": [
        {"type": "node", "id": 1, "lat": 51.089, "lon": 71.419},
        {"type": "node", "id": 2, "lat": 51.090, "lon": 71.419, "tags": node_tags or {}},
        {"type": "node", "id": 3, "lat": 51.090, "lon": 71.420},
        {"type": "way", "id": 10, "nodes": [1, 2, 3], "tags": tags or {"highway": "footway"}},
    ]}


def test_path_follows_real_edges_not_diagonal():
    graph = graph_fixture()
    result = graph.route(graph.nodes[1], graph.nodes[3])
    assert result is not None
    assert result.distance_m > distance_m(*graph.nodes[1], *graph.nodes[3]) + 30
    assert result.coordinates == [[71.419, 51.089], [71.419, 51.090], [71.420, 51.090]]
    assert result.connector_m == 0
    assert graph.metadata["basis"] == "osm_walking_graph"


def test_connector_is_included_and_bounded():
    graph = graph_fixture()
    start = (51.0888, 71.419)
    result = graph.route(start, graph.nodes[3])
    base = graph.route(graph.nodes[1], graph.nodes[3])
    assert result is not None and base is not None
    assert 22 <= result.connector_m <= 23
    assert 22 <= result.distance_m - base.distance_m <= 23
    assert result.coordinates[0] == [start[1], start[0]]
    assert graph.route((51.08, 71.419), graph.nodes[3]) is None


def test_disconnected_components_never_get_straight_line_fallback():
    graph = graph_fixture()
    graph = WalkingNetwork(graph.nodes | {4: (51.089, 71.423)},
                           [(a, b, length) for a, pairs in graph._adj.items() for b, length in pairs], {})
    assert graph.route(graph.nodes[1], graph.nodes[4]) is None


@pytest.mark.parametrize("tags", [
    {"highway": "footway", "foot": "no"},
    {"highway": "footway", "access": "private", "foot": "yes"},
    {"highway": "footway", "access": "no"},
    {"highway": "motorway", "foot": "yes"},
    {"highway": "trunk"},
    {"highway": "construction"},
    {"highway": "proposed"},
    {"highway": "cycleway"},
    {"highway": "primary", "sidewalk": "no"},
    {"highway": "footway", "access:conditional": "no @ (night)"},
    {"highway": "footway", "indoor": "yes"},
    {"highway": "residential", "foot": "use_sidepath"},
    {"highway": "footway", "oneway:foot": "reversible"},
    {"highway": "footway", "construction": "yes"},
])
def test_excludes_unsupported_or_restricted_ways(tags):
    assert not accessible(tags)


def test_ordinary_oneway_does_not_restrict_pedestrians_but_oneway_foot_does():
    both, _ = normalize(raw_fixture({"highway": "residential", "oneway": "yes"}))
    directed, _ = normalize(raw_fixture({"highway": "footway", "oneway:foot": "yes"}))
    assert len(both["edges"]) == 4
    graph = WalkingNetwork.from_payload(directed)
    assert graph.route(graph.nodes[1], graph.nodes[3]) is not None
    assert graph.route(graph.nodes[3], graph.nodes[1]) is None


@pytest.mark.parametrize("tags", [{"barrier": "gate"}, {"barrier": "fence"}, {"locked": "yes"}, {"foot": "no"}])
def test_unknown_or_forbidden_gates_break_connectivity(tags):
    with pytest.raises(ValueError, match="Empty walking graph"):
        normalize(raw_fixture(node_tags=tags))


def test_public_gate_is_preserved():
    payload, stats = normalize(raw_fixture(node_tags={"barrier": "gate", "foot": "yes"}))
    assert stats["directed_edge_count"] == 4
    assert len(payload["nodes"]) == 3


def test_publish_failure_keeps_old_pointer_and_loader_checks_hash(tmp_path):
    raw = raw_fixture()
    metadata = publish(raw, tmp_path, "https://example.test/overpass", "fixed query", datetime.now(timezone.utc).isoformat())
    first_pointer = (tmp_path / "current.json").read_bytes()
    with pytest.raises(ValueError):
        publish({"remark": "timeout", "elements": []}, tmp_path, "https://example.test/overpass", "fixed query", "ignored")
    assert (tmp_path / "current.json").read_bytes() == first_pointer
    graph = WalkingNetwork.load(tmp_path)
    assert graph.metadata["source_data_timestamp"] == raw["osm3s"]["timestamp_osm_base"]
    snapshot = tmp_path / "snapshots" / metadata["snapshot_id"]
    assert hashlib.sha256((snapshot / "raw.json").read_bytes()).hexdigest() == metadata["raw_sha256"]
    (snapshot / "graph.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        WalkingNetwork.load(tmp_path)


def test_loader_rejects_path_traversal(tmp_path):
    (tmp_path / "current.json").write_text(json.dumps({"snapshot": "../elsewhere"}))
    with pytest.raises(ValueError, match="path"):
        WalkingNetwork.load(tmp_path)


def test_same_position_does_not_invent_double_connector():
    graph = graph_fixture()
    start = (51.0888, 71.419)
    leg = graph.route(start, start)
    assert leg is not None and leg.distance_m == 0 and leg.connector_m == 0


def test_shipped_graph_is_reproducible_from_raw():
    from app.walking import DEFAULT_ROOT
    graph = WalkingNetwork.load()
    pointer = json.loads((DEFAULT_ROOT / "current.json").read_text(encoding="utf-8"))
    snapshot = DEFAULT_ROOT / pointer["snapshot"]
    raw = json.loads((snapshot / "raw.json").read_text(encoding="utf-8"))
    expected, stats = normalize(raw)
    assert expected == json.loads((snapshot / "graph.json").read_text(encoding="utf-8"))
    assert stats["node_count"] == graph.metadata["node_count"]


def test_invalid_length_rejected():
    with pytest.raises(ValueError, match="length"):
        WalkingNetwork.from_payload({"nodes": [[1, 51.089, 71.419], [2, 51.090, 71.419]], "edges": [[1, 2, 1]]})


@pytest.mark.parametrize("bad", [(float("nan"), 71.419), (100, 71.419), (51.089, 200)])
def test_invalid_coordinate_cannot_route(bad):
    graph = graph_fixture()
    assert graph.route(bad, graph.nodes[1]) is None


def test_tree_cache_stores_node_ids_only():
    graph = graph_fixture()
    graph.route((51.0888, 71.419), graph.nodes[3])
    assert list(graph._trees) == [1]
    assert all(isinstance(node_id, int) for node_id in graph._trees[1][0])
