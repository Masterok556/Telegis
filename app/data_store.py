from dataclasses import dataclass
import json
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


class DataStore:
    """Reads an immutable snapshot; atomically published updates need no restart."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._snapshot: str | None = None
        self._dataset: Dataset | None = None
        self._lock = RLock()

    def get(self) -> Dataset:
        try:
            with self._lock:
                pointer = json.loads((self.root / "current.json").read_text(encoding="utf-8"))
                snapshot = pointer["snapshot"]
                if not re.fullmatch(r"snapshots/[A-Za-z0-9_-]+", snapshot):
                    raise ValueError("Invalid snapshot path")
                if snapshot == self._snapshot and self._dataset is not None:
                    return self._dataset
                folder = (self.root / snapshot).resolve()
                if not folder.is_relative_to(self.root):
                    raise ValueError("Snapshot outside data directory")
                pois = tuple(POI.model_validate(p) for p in json.loads((folder / "pois.json").read_text(encoding="utf-8")))
                locations = tuple(Location.model_validate(p) for p in json.loads((folder / "locations.json").read_text(encoding="utf-8")))
                manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
                ids = {p.poi_id for p in pois}
                if not pois or len(ids) != len(pois) or not locations or not all(l.id in ids for l in locations):
                    raise ValueError("Empty or inconsistent dataset")
                if manifest["poi_count"] != len(pois):
                    raise ValueError("Manifest count mismatch")
                dataset = Dataset(pois, locations, manifest)
                self._dataset, self._snapshot = dataset, snapshot
                return dataset
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DatasetUnavailable("Датасет недоступен. Запустите python scripts/collect_pois.py.") from exc
