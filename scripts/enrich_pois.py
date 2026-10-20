"""Fetch reviewed primary sources and publish attributable POI facts.

No arbitrary URL arguments, user locations, model extraction or guessed facts.
Every paraphrase requires exact supporting phrases in the live page; if a page
changes or any fetch fails, the previous complete enrichment is retained.
Copyright pages are not redistributed: only tiny supporting fragments and hashes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.data_store import DataStore
from app.facts import OFFICIAL_HOSTS
from app.geo import distance_m

SOURCES = (
    {
        "key": "japanese_garden", "poi_id": "osm_way_1470723968", "name": "Японский сад",
        "lat": 51.0921362, "lon": 71.3994992,
        "url": "https://nu.edu.kz/news-en/place-oriental-philosophy-nu-campus/",
        "published_at": "2019-07-09", "identity_basis": "Reviewed unique Japanese garden at NU campus; OSM name and exact reviewed coordinates.",
        "facts": [
            {"id": "japan_stones", "needles": ["stones used in NU’s garden were brought from Japan"],
             "text": "По статье Nazarbayev University, камни для этого японского сада привезли из Японии."},
            {"id": "fourteen_stones", "needles": ["14 stones at once", "fifteenth"],
             "text": "В описании NU — композиция из 15 камней: с одной точки видны 14. Это идея для внимательного наблюдения."},
        ],
        "warnings": ["Сведения об устройстве сада взяты из статьи NU от 09.07.2019; нынешний вид и доступ на кампус не подтверждены.",
                     "По статье NU, зимой камни укрывают; видимость композиции зависит от сезона. Не сходите с дорожек и не трогайте камни."],
        "warning_needles": ["winter we cover the stones", "do not"],
    },
    {
        "key": "botanical_garden", "poi_id": "osm_way_1196402246", "name": "Ботанический сад",
        "lat": 51.1061652, "lon": 71.4165705,
        "url": "https://www.astanabotsad.kz/ru/o-nas", "published_at": None,
        "identity_basis": "Official website domain is linked by this exact OSM POI; matching name and coordinates.",
        "required_osm_website_host": "www.astanabotsad.kz",
        "facts": [
            {"id": "themed_gardens", "needles": ["8", "тематических садов"],
             "text": "Официальный сайт описывает восемь тематических садов вокруг круглой центральной части."},
            {"id": "water_bridge", "needles": ["искусственный водоём", "пешеходный мост"],
             "text": "На официальном сайте отмечен пешеходный мост через искусственный водоём."},
            {"id": "greenhouse", "needles": ["оранжерейный комплекс"],
             "text": "На территории описан оранжерейный комплекс; его посещение требует отдельной проверки часов и билетов."},
        ],
        "warnings": ["Сайт описывает весь ботанический сад; вход в оранжерею, часы и билеты отдельно не проверялись."],
        "warning_needles": [],
    },
    {
        "key": "nu_park", "poi_id": "osm_way_1467797207", "name": "NU Park",
        "lat": 51.0872699, "lon": 71.3994394,
        "url": "https://fund.nu.edu.kz/en/news/eurasian-bank-supports-the-creation-of-a-new-public-space-nu-park/",
        "published_at": "2026-05-22", "identity_basis": "Reviewed NU Park project at NU campus; exact OSM name and reviewed campus coordinates.",
        "facts": [
            {"id": "development", "needles": ["future NU Park", "50 Siberian spruce trees"],
             "text": "NU Impact Foundation 22.05.2026 описывает будущий NU Park и посадку 50 сибирских елей."},
        ],
        "warnings": ["Официальная публикация от 22.05.2026 описывает NU Park как будущий проект. Подтверждения ввода всех зон нет; точка исключена из прогулочных маршрутов."],
        "warning_needles": [], "exclude_from_routes": True,
    },
    {
        "key": "mangilik_el", "poi_id": "osm_way_549307755", "name": "Триумфальная арка Мангилик Ел",
        "lat": 51.1043034, "lon": 71.4300836,
        "url": "https://visitastana.kz/ru/about-city/what-to-see/triumfalnaya-arka-m-gilik-el9679/",
        "published_at": None,
        "identity_basis": "Reviewed unique Mangilik El Triumphal Arch; matching OSM name, monument type and coordinates.",
        "facts": [
            {"id": "independence_landmark", "needles": ["2011", "20-летия Независимости"],
             "text": "Visit Astana описывает арку как памятник 20-летию независимости Казахстана, построенный в 2011 году."},
            {"id": "national_reliefs", "needles": ["национальными орнаментами", "барельефы"],
             "text": "На странице Visit Astana отмечены национальные орнаменты и барельефы на стенах арки: детали для осмотра снаружи."},
            {"id": "hours_24_7", "needles": ["График работы:", "Круглосуточно"],
             "text": "Visit Astana указывает для арки круглосуточный график. Это сведения источника, а не подтверждение текущего доступа."},
        ],
        "warnings": [
            "Круглосуточная отметка относится к достопримечательности; доступ внутрь и на смотровую площадку отдельно не подтверждён.",
            "Освещение, безопасность ночного подхода и временные ограничения не проверены. Оставайтесь на доступных пешеходных дорожках."
        ],
        "warning_needles": [],
    },
)


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def normalize_text(value: str) -> str:
    return " ".join(value.replace("’", "'").replace("ё", "е").casefold().split())


def extract_record(source: dict, body: bytes, poi, collected_at: str) -> dict:
    parser = PageText()
    parser.feed(body.decode("utf-8"))
    text = normalize_text(" ".join(parser.parts))
    excerpts = []
    for item in source["facts"]:
        for needle in item["needles"]:
            if normalize_text(needle) not in text:
                raise ValueError(f"Supporting phrase missing for {source['key']}:{item['id']}")
            excerpts.append(needle)
    for needle in source["warning_needles"]:
        if normalize_text(needle) not in text:
            raise ValueError(f"Warning evidence missing for {source['key']}")
        excerpts.append(needle)
    # A bounded evidence extract; full copyrighted pages are never saved in Git.
    if sum(len(s.split()) for s in excerpts) > 25:
        raise ValueError("Supporting excerpts exceed 25 words for a source")
    return {
        "identity": {"name": poi.name, "lat": poi.lat, "lon": poi.lon, "source_url": poi.source_url,
                     "match_basis": source["identity_basis"]},
        "source_url": source["url"], "collected_at": collected_at,
        "published_at": source["published_at"], "body_sha256": hashlib.sha256(body).hexdigest(),
        "supporting_excerpts": excerpts,
        "facts": [{"id": f["id"], "text": f["text"]} for f in source["facts"]],
        "warnings": source["warnings"], "exclude_from_routes": source.get("exclude_from_routes", False),
    }


def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS
            or parsed.username or parsed.password or parsed.port not in {None, 443}):
        raise ValueError("URL outside reviewed primary-source allowlist")


class ReviewedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str) -> bytes:
    validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Telegis/1.0 (educational POI evidence collector)"})
    with urllib.request.build_opener(ReviewedRedirects()).open(request, timeout=20) as response:
        validate_url(response.geturl())
        body = response.read(3_000_001)
    if len(body) > 3_000_000:
        raise ValueError("Official page exceeds 3 MB")
    return body


def publish(records: dict, output: Path) -> dict:
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = output / "snapshots" / snapshot_id
    folder.mkdir(parents=True)
    content = (json.dumps(records, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (folder / "records.json").write_bytes(content)
    manifest = {"schema_version": 1, "snapshot_id": snapshot_id, "source_count": len(records),
                "fact_count": sum(len(r["facts"]) for r in records.values()),
                "records_sha256": hashlib.sha256(content).hexdigest(),
                "method": "Allowlisted primary pages, reviewed OSM identities, deterministic phrase checks",
                "license_note": "Factual paraphrases with attribution; short supporting excerpts; page copyrights remain with publishers."}
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary = output / (".current-" + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps({"snapshot": "snapshots/" + snapshot_id}) + "\n", encoding="utf-8")
    os.replace(temporary, output / "current.json")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "enrichment")
    args = parser.parse_args()
    try:
        dataset = DataStore(args.data_dir).get()
        by_id = {p.poi_id: p for p in dataset.pois}
        records = {}
        for source in SOURCES:
            poi = by_id.get(source["poi_id"])
            if (poi is None or poi.name != source["name"]
                    or distance_m(poi.lat, poi.lon, source["lat"], source["lon"]) > 50):
                raise ValueError(f"Reviewed OSM identity no longer matches: {source['key']}")
            host = source.get("required_osm_website_host")
            if host and urlsplit(poi.website or "").hostname != host:
                raise ValueError("Official domain no longer linked by OSM")
            body = fetch(source["url"])
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            records[poi.poi_id] = extract_record(source, body, poi, timestamp)
            print(f"Verified {source['key']}: {len(records[poi.poi_id]['facts'])} facts", flush=True)
        result = publish(records, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Enrichment not published; previous version retained: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
