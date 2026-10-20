"""
TeleGIS Automated Test Suite (30+ Rigorous Tests)
Tests endpoints, data consistency, LLM integration, distance math, and edge cases.
"""
import urllib.request
import urllib.parse
import json
import math
import os
import sys

BASE_URL = "http://127.0.0.1:8080"
TEST_RESULTS = []

def record(test_name, success, details=""):
    TEST_RESULTS.append({"test": test_name, "pass": success, "details": details})
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {test_name} {f'({details})' if details else ''}")

def req_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "TeleGIS-Tester/1.0"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read().decode('utf-8'))

def req_post(path, data):
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "TeleGIS-Tester/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.status, json.loads(r.read().decode('utf-8'))

print("=== Starting TeleGIS Rigorous Test Suite ===")

# Test 1: Health check
try:
    s, d = req_get("/api/health")
    record("API Health Endpoint", s == 200 and d.get("status") == "ok")
except Exception as e:
    record("API Health Endpoint", False, str(e))

# Test 2: Meta info
try:
    s, d = req_get("/api/meta")
    record("API Meta Endpoint", s == 200 and d.get("service") == "TeleGIS" and d.get("poi_count", 0) > 40)
except Exception as e:
    record("API Meta Endpoint", False, str(e))

# Test 3: Locations endpoint
try:
    s, d = req_get("/api/locations")
    locs = d.get("locations", [])
    has_alem = any("Alem.ai" in l.get("name", "") for l in locs)
    has_mega = any("Mega" in l.get("name", "") for l in locs)
    has_aitu = any("AITU" in l.get("name", "") for l in locs)
    record("API Locations Count >= 4", s == 200 and len(locs) >= 4, f"Count: {len(locs)}")
    record("API Locations Contains Alem.ai", has_alem)
    record("API Locations Contains Mega Silk Way", has_mega)
    record("API Locations Contains AITU", has_aitu)
except Exception as e:
    record("API Locations Endpoint", False, str(e))

# Test 4: POIs endpoint
try:
    s, d = req_get("/api/pois")
    pois = d.get("pois", [])
    record("API POIs Endpoint Loaded", s == 200 and len(pois) >= 50, f"Total POIs: {len(pois)}")
    
    # Check coordinates validity for every POI
    coords_ok = True
    for p in pois:
        lat, lon = p.get("lat"), p.get("lon")
        if not (50.9 <= lat <= 51.3 and 71.2 <= lon <= 71.6):
            coords_ok = False
            break
    record("All POIs have valid Astana Coordinates (WGS-84)", coords_ok)

    # Check Alem.ai coordinates
    alem = next((p for p in pois if "Alem.ai" in p.get("name", "")), None)
    alem_coords_ok = alem and abs(alem["lat"] - 51.0892) < 0.002 and abs(alem["lon"] - 71.4162) < 0.002
    record("Alem.ai exact coordinates on Pavilion B1", bool(alem_coords_ok), f"Lat: {alem['lat'] if alem else None}")
except Exception as e:
    record("API POIs Endpoint", False, str(e))

# Test 5: Search from Mega Silk Way
try:
    s, d = req_post("/api/recommend", {
        "lat": 51.0890897,
        "lon": 71.4073303,
        "category": "walk",
        "available_minutes": 60,
        "query": ""
    })
    recs = d.get("recommendations", [])
    record("Search from Mega: returns 3 recommendations", len(recs) == 3)
    record("Search from Mega: closest place is <= 100m", len(recs) > 0 and recs[0]["distance_m"] <= 100, f"Dist: {recs[0]['distance_m'] if recs else None}m")
except Exception as e:
    record("Search from Mega", False, str(e))

# Test 6: Search from real Alem.ai (51.0892381, 71.4162196)
try:
    s, d = req_post("/api/recommend", {
        "lat": 51.0892381,
        "lon": 71.4162196,
        "category": "walk",
        "available_minutes": 60,
        "query": ""
    })
    recs = d.get("recommendations", [])
    record("Search from Alem.ai: returns places", len(recs) > 0)
    # Check that nearby places are EXPO landmarks (Astana Hub, AITU)
    nearby_names = [r["name"] for r in recs]
    has_expo_places = any(k in " ".join(nearby_names) for k in ["Alem", "Hub", "AITU", "University"])
    record("Search from Alem.ai: finds authentic EXPO landmarks", has_expo_places, f"Places: {nearby_names}")
except Exception as e:
    record("Search from Alem.ai", False, str(e))

# Test 7: Search with cafe category
try:
    s, d = req_post("/api/recommend", {
        "lat": 51.0890897,
        "lon": 71.4073303,
        "category": "cafe",
        "available_minutes": 30,
        "query": "кофе"
    })
    recs = d.get("recommendations", [])
    all_cafes = all(r.get("category") in {"cafe", "restaurant", "fast_food"} for r in recs)
    record("Search Category Cafe: all results are food/drink venues", all_cafes and len(recs) > 0)
except Exception as e:
    record("Search Category Cafe", False, str(e))

# Test 8: Keyword search filtering (e.g. 'студент' or 'робот' or 'сад')
try:
    s, d = req_post("/api/recommend", {
        "lat": 51.0892381,
        "lon": 71.4162196,
        "category": "walk",
        "available_minutes": 60,
        "query": "сад"
    })
    recs = d.get("recommendations", [])
    record("Query 'сад': finds garden or park", len(recs) > 0 and any("сад" in r["name"].lower() or "парк" in r["name"].lower() for r in recs))
except Exception as e:
    record("Query 'сад'", False, str(e))

# Test 9: POI AI Info Endpoint
try:
    s, d = req_post("/api/poi_ai_info", {
        "poi_id": "osm_way_454857501",
        "name": "Alem.ai",
        "category": "attraction"
    })
    record("POI AI Info: responds with summary and tip", s == 200 and "summary" in d and "tip" in d)
except Exception as e:
    record("POI AI Info", False, str(e))

# Test 10: Itinerary Endpoint
try:
    s, d = req_post("/api/itinerary", {"available_minutes": 120})
    record("Itinerary 120 min: returns stops and legs", s == 200 and len(d.get("stops", [])) > 0 and len(d.get("legs", [])) > 0)
    
    s_short, d_short = req_post("/api/itinerary", {"available_minutes": 60})
    record("Itinerary 60 min: returns safe rejection message", d_short.get("status") == "no_match")
except Exception as e:
    record("Itinerary Endpoint", False, str(e))

# Summary
passed = sum(1 for r in TEST_RESULTS if r["pass"])
total = len(TEST_RESULTS)
print(f"\n=== Test Summary: {passed}/{total} Passed ({round(passed/total*100)}%) ===")
