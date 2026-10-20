from dataclasses import dataclass
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from threading import RLock

from app.models import Location, POI


class DatasetUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Dataset:
    pois: tuple[POI, ...]
    locations: tuple[Location, ...]
    manifest: dict


def load_snapshot(folder: Path) -> Dataset:
    """Validate the whole snapshot before serving it or publishing its pointer."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    required = {"schema_version", "snapshot_id", "poi_count", "locations_count", "categories",
                "collected_at", "source_data_timestamp", "coverage", "attribution", "license",
                "license_url", "raw_sha256", "raw_elements", "pois_sha256", "locations_sha256"}
    if not required.issubset(manifest):
        raise ValueError("Incomplete manifest")
    if manifest["schema_version"] != 1 or manifest["snapshot_id"] != folder.name:
        raise ValueError("Snapshot identity or schema mismatch")
    for field in ("collected_at", "source_data_timestamp"):
        value = manifest[field]
        if field == "source_data_timestamp" and value is None:
            continue
        if not isinstance(value, str) or datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Snapshot timestamp must include timezone")
    if not all(isinstance(manifest[k], str) and manifest[k] for k in ("attribution", "license", "license_url")):
        raise ValueError("Missing dataset attribution")
    coverage = manifest["coverage"]
    if not isinstance(coverage, dict) or not {"name", "lat", "lon", "radius_m"}.issubset(coverage):
        raise ValueError("Invalid collection coverage")
    if not isinstance(coverage["name"], str) or not coverage["name"]:
        raise ValueError("Invalid coverage name")
    for field, low, high in (("lat", -90, 90), ("lon", -180, 180), ("radius_m", 1, 100_000)):
        value = coverage[field]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Invalid coverage coordinates or radius")
    raw_bytes = (folder / "raw.json").read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != manifest["raw_sha256"]:
        raise ValueError("Source response checksum mismatch")
    raw = json.loads(raw_bytes)
    if not isinstance(raw, dict) or not isinstance(raw.get("elements"), list) or raw.get("remark"):
        raise ValueError("Invalid source response")
    if type(manifest["raw_elements"]) is not int or manifest["raw_elements"] != len(raw["elements"]):
        raise ValueError("Source response count mismatch")
    raw_ids = {f"osm_{e.get('type')}_{e.get('id')}" for e in raw["elements"] if isinstance(e, dict)}
    processed = {}
    for name in ("pois", "locations"):
        content = (folder / f"{name}.json").read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest[f"{name}_sha256"]:
            raise ValueError(f"Processed {name} checksum mismatch")
        processed[name] = json.loads(content)
    poi_values = processed["pois"]
    location_values = processed["locations"]
    if not isinstance(poi_values, list) or not isinstance(location_values, list):
        raise ValueError("POIs and locations must be arrays")
    pois = tuple(POI.model_validate(p) for p in poi_values)
    locations = tuple(Location.model_validate(p) for p in location_values)
    by_id = {p.poi_id: p for p in pois}
    if not pois or len(by_id) != len(pois) or not locations or len({p.id for p in locations}) != len(locations):
        raise ValueError("Empty or duplicate dataset records")
    for poi in pois:
        identity = re.fullmatch(r"osm_(node|way|relation)_([1-9][0-9]*)", poi.poi_id)
        if not identity or poi.poi_id not in raw_ids:
            raise ValueError("POI missing from source response")
        if poi.source_url != f"https://www.openstreetmap.org/{identity[1]}/{identity[2]}":
            raise ValueError("POI identity differs from its source URL")
        if poi.collected_at != manifest["collected_at"]:
            raise ValueError("POI collection timestamp differs from manifest")
    for location in locations:
        poi = by_id.get(location.id)
        if poi is None or (location.name, location.lat, location.lon) != (poi.name, poi.lat, poi.lon):
            raise ValueError("Starting location differs from its source POI")
    if any(type(manifest[key]) is not int or manifest[key] != count
           for key, count in (("poi_count", len(pois)), ("locations_count", len(locations)))):
        raise ValueError("Manifest count mismatch")
    if manifest["categories"] != dict(Counter(p.category for p in pois)):
        raise ValueError("Manifest category counts mismatch")
    return Dataset(pois, locations, manifest)


class DataStore:
    """Reads an immutable snapshot; atomically published updates need no restart."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._snapshot: str | None = None
        self._dataset: Dataset | None = None
        self._files_stamp: tuple | None = None
        self._lock = RLock()

    def get(self) -> Dataset:
        try:
            with self._lock:
                pointer = json.loads((self.root / "current.json").read_text(encoding="utf-8"))
                snapshot = pointer["snapshot"]
                if not re.fullmatch(r"snapshots/[A-Za-z0-9_-]+", snapshot):
                    raise ValueError("Invalid snapshot path")
                folder = (self.root / snapshot).resolve()
                if not folder.is_relative_to(self.root):
                    raise ValueError("Snapshot outside data directory")
                stamps = tuple((s.st_mtime_ns, s.st_size)
                               for name in ("manifest.json", "pois.json", "locations.json", "raw.json")
                               for s in [(folder / name).stat()])
                if (snapshot == self._snapshot and self._dataset is not None
                        and stamps == self._files_stamp):
                    return self._dataset
                dataset = load_snapshot(folder)
                self._dataset, self._snapshot, self._files_stamp = dataset, snapshot, stamps
                return dataset
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DatasetUnavailable("Датасет недоступен. Запустите python scripts/collect_pois.py.") from exc
