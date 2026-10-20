"""Small, attributable POI facts; no network access during recommendations.

OSM tags remain community-reported information, not a live inspection. Official
page extracts are optional and keyed to reviewed OSM identities, never just names.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from app.models import POI

DEFAULT_ENRICHMENT_DIR = Path(__file__).resolve().parents[1] / "data" / "enrichment"
OFFICIAL_HOSTS = {"nu.edu.kz", "fund.nu.edu.kz", "www.astanabotsad.kz", "astanabotsad.kz",
                  "visitastana.kz", "www.visitastana.kz"}
# Reviewed safety hold: OSM's park category conflicts with a dated primary-source
# future-project description. Removing enrichment must not turn that into an open
# park again. Remove this hold only after a new explicit opening/access review.
PROJECT_HOLDS = {
    "osm_way_1467797207": "NU Impact Foundation 22.05.2026 описывает NU Park как будущий проект. Доступность не подтверждена, поэтому точка исключена из маршрутов. Источник: https://fund.nu.edu.kz/en/news/eurasian-bank-supports-the-creation-of-a-new-public-space-nu-park/",
}
CUISINES = {
    "coffee_shop": "кофе", "breakfast": "завтраки", "cake": "десерты",
    "russian": "русская кухня", "european": "европейская кухня", "italian": "итальянская кухня",
    "pasta": "паста", "donut": "пончики", "crepe": "блины", "burger": "бургеры",
    "barbecue": "блюда на гриле", "chicken": "блюда из курицы", "fish": "рыба",
    "local": "местная кухня", "diner": "закуски",
}


def _timestamp(value: object) -> bool:
    try:
        return isinstance(value, str) and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


@lru_cache(maxsize=8)
def _read_records(folder: Path, records_stamp: tuple[int, int], manifest_stamp: tuple[int, int]) -> dict:
    """Stat arguments invalidate the bounded cache when a snapshot is edited."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    body = (folder / "records.json").read_bytes()
    if len(body) > 250_000 or hashlib.sha256(body).hexdigest() != manifest["records_sha256"]:
        return {}
    records = json.loads(body)
    if manifest.get("schema_version") != 1 or not isinstance(records, dict):
        return {}
    return records


def _official_record(poi: POI, enrichment_dir: Path | None = None) -> dict:
    root = Path(enrichment_dir) if enrichment_dir is not None else DEFAULT_ENRICHMENT_DIR
    try:
        pointer = json.loads((root / "current.json").read_text(encoding="utf-8"))
        snapshot = pointer["snapshot"]
        if not isinstance(snapshot, str) or not re.fullmatch(r"snapshots/[A-Za-z0-9_-]+", snapshot):
            return {}
        folder = root / snapshot
        records_stat, manifest_stat = (folder / "records.json").stat(), (folder / "manifest.json").stat()
        records = _read_records(folder, (records_stat.st_mtime_ns, records_stat.st_size),
                                (manifest_stat.st_mtime_ns, manifest_stat.st_size))
        record = records.get(poi.poi_id, {})
        identity = record.get("identity", {})
        # Reviewed identity must still agree with the currently served OSM POI.
        if (identity.get("source_url") != poi.source_url or identity.get("name") != poi.name
                or abs(identity.get("lat", -999) - poi.lat) > 0.002
                or abs(identity.get("lon", -999) - poi.lon) > 0.002):
            return {}
        parsed = urlsplit(record.get("source_url", ""))
        if (parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS
                or parsed.username or parsed.password or parsed.port not in {None, 443}
                or not _timestamp(record.get("collected_at"))):
            return {}
        if not isinstance(record.get("facts"), list) or not isinstance(record.get("warnings"), list):
            return {}
        for item in record["facts"]:
            if (not isinstance(item, dict) or not re.fullmatch(r"[a-z][a-z0-9_]{0,55}", item.get("id", ""))
                    or not isinstance(item.get("text"), str) or not 1 <= len(item["text"]) <= 500):
                return {}
        if not all(isinstance(w, str) and len(w) <= 600 for w in record["warnings"]):
            return {}
        return record
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def facts_for(poi: POI, enrichment_dir: Path | None = None) -> list[dict]:
    """Return grounded short facts with a source per fact, strongest details first."""
    facts: list[dict] = []
    official = _official_record(poi, enrichment_dir)
    for fact in official.get("facts", []):
        facts.append({"id": "official_" + fact["id"], "text": fact["text"],
                      "source_url": official["source_url"], "collected_at": official["collected_at"],
                      "kind": "official", "confidence": "source_reported",
                      "published_at": official.get("published_at")})

    def add(key: str, text: str) -> None:
        facts.append({"id": "osm_" + key, "text": text, "source_url": poi.source_url,
                      "collected_at": poi.collected_at, "kind": "osm_tag", "confidence": "source_reported"})

    tags = poi.tags
    cuisines = list(dict.fromkeys(CUISINES[v] for v in tags.get("cuisine", "").split(";") if v in CUISINES))
    if cuisines:
        add("cuisine", "В OSM отмечены: " + ", ".join(cuisines[:5]) + ".")
    if tags.get("artwork_type") in {"sculpture", "statue", "installation", "mural"}:
        label = {"sculpture": "скульптура", "statue": "статуя", "installation": "инсталляция", "mural": "настенная роспись"}[tags["artwork_type"]]
        add("artwork_type", f"В OSM объект описан как {label}.")
    if tags.get("memorial") == "bust":
        add("memorial", "В OSM отмечен памятный бюст.")
    if tags.get("architect"):
        add("architect", f"Архитектор по данным OSM: {tags['architect'][:150]}.")
    if re.fullmatch(r"\d{1,3}(?:\.\d+)?", tags.get("height", "")):
        add("height", f"Указанная в OSM высота объекта — {tags['height']} м.")
    if re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", tags.get("start_date", "")):
        add("start_date", f"Указанная в OSM дата создания или открытия объекта — {tags['start_date']}.")
    if tags.get("garden:type") == "public":
        add("public_garden", "В OSM сад обозначен как общественный; текущий доступ нужно уточнить.")
    for key, label in (("artist_name", "Автор по данным OSM"), ("species", "Вид растений по данным OSM")):
        if tags.get(key):
            add(key, f"{label}: {tags[key][:150]}.")
    if tags.get("takeaway") == "yes":
        add("takeaway", "В OSM отмечена возможность заказа с собой; наличие уточните при заказе.")
    if tags.get("outdoor_seating") in {"yes", "no"}:
        add("outdoor_seating", "В OSM указаны места на улице; сезонную доступность нужно уточнить." if tags["outdoor_seating"] == "yes" else "В OSM указано отсутствие мест на улице.")
    if tags.get("indoor_seating") == "yes":
        add("indoor_seating", "В OSM отмечены места внутри помещения.")
    if tags.get("internet_access") == "wlan":
        add("wifi", "В OSM указан Wi-Fi; работоспособность и условия подключения нужно уточнить.")
    elif tags.get("internet_access") == "yes":
        add("internet", "В OSM указан доступ к интернету; способ подключения не уточнён.")
    if tags.get("internet_access:fee") == "no" and tags.get("internet_access") in {"yes", "wlan"}:
        add("internet_fee", "В OSM интернет помечен как бесплатный; актуальные условия нужно уточнить.")
    if tags.get("smoking") == "no":
        add("smoking", "В OSM отмечен запрет курения.")
    if tags.get("toilets") == "yes":
        add("toilets", "В OSM отмечен туалет; условия доступа не подтверждены.")
    if tags.get("addr:street"):
        address = tags["addr:street"] + (", " + tags["addr:housenumber"] if tags.get("addr:housenumber") else "")
        add("address", "Адрес в OSM: " + address[:200] + ".")
    return facts[:20]


def warnings_for(poi: POI, enrichment_dir: Path | None = None) -> list[str]:
    warnings = list(_official_record(poi, enrichment_dir).get("warnings", []))
    if poi.poi_id in PROJECT_HOLDS and not warnings:
        warnings.append(PROJECT_HOLDS[poi.poi_id])
    return warnings


def excluded_from_routes(poi: POI, enrichment_dir: Path | None = None) -> bool:
    """A published construction caveat prevents routing into an unverified project."""
    return poi.poi_id in PROJECT_HOLDS or _official_record(poi, enrichment_dir).get("exclude_from_routes") is True
