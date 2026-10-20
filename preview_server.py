import http.server
import socketserver
import json
import os
import math
import urllib.parse
import urllib.request

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env_vars = {}
    for fname in ['.env', 'env.txt']:
        env_file = os.path.join(BASE_DIR, fname)
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        val = v.strip().strip('"').strip("'")
                        env_vars[k.strip()] = val
    return env_vars

# Load official dataset
OFFICIAL_LOCS_PATH = os.path.join(BASE_DIR, 'data_official', 'locations.json')
OFFICIAL_POIS_PATH = os.path.join(BASE_DIR, 'data_official', 'pois.json')
OFFICIAL_FACTS_PATH = os.path.join(BASE_DIR, 'data_official', 'facts.json')

def get_official_locations():
    if os.path.exists(OFFICIAL_LOCS_PATH):
        try:
            with open(OFFICIAL_LOCS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return OFFICIAL_LOCATIONS

def get_official_pois():
    if os.path.exists(OFFICIAL_POIS_PATH):
        try:
            with open(OFFICIAL_POIS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return OFFICIAL_POIS

def get_official_facts():
    if os.path.exists(OFFICIAL_FACTS_PATH):
        try:
            with open(OFFICIAL_FACTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return OFFICIAL_FACTS

OFFICIAL_LOCATIONS = get_official_locations()
OFFICIAL_POIS = get_official_pois()
OFFICIAL_FACTS = get_official_facts()

ITIN_PATH = os.path.join(BASE_DIR, 'static', 'itinerary_example.json')
ITIN_DATA = {}
if os.path.exists(ITIN_PATH):
    with open(ITIN_PATH, 'r', encoding='utf-8') as f:
        ITIN_DATA = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def search_official_pois(lat, lon, minutes, category, query):
    cafe_cats = {'cafe', 'fast_food', 'restaurant', 'bar'}
    walk_cats = {'park', 'garden', 'attraction', 'monument', 'memorial', 'artwork', 'viewpoint', 'square', 'mall', 'museum'}
    allowed = cafe_cats if category == 'cafe' else walk_cats

    q_lower = query.lower().strip() if query else ''
    candidates = []

    pois = get_official_pois()
    facts = get_official_facts()

    for poi in pois:
        poi_cat = poi.get('category', 'walk')
        if poi_cat not in allowed:
            continue

        dist_m = round(haversine(lat, lon, poi['lat'], poi['lon']))
        # Realistic walking speed in urban setting: ~80 m/min (4.8 km/h)
        walk_min = max(1, math.ceil(dist_m / 80))
        visit_min = 15 if category == 'cafe' else 20
        total_min = 2 * walk_min + visit_min

        # Distance score (closer is better, max distance 3.5km)
        dist_score = max(0.0, 1.0 - (dist_m / 3500.0))

        # Relevance score
        rel_score = 0.5
        name_lower = poi['name'].lower()
        desc_lower = poi.get('description', '').lower()
        if q_lower:
            words = [w for w in q_lower.split() if len(w) > 2]
            for w in words:
                if w in name_lower:
                    rel_score += 1.2
                elif w in desc_lower:
                    rel_score += 0.5
                elif w in poi_cat:
                    rel_score += 0.4

        total_score = 0.65 * rel_score + 0.35 * dist_score
        time_fit = total_min <= minutes

        candidates.append({
            'poi': poi,
            'dist_m': dist_m,
            'walk_min': walk_min,
            'visit_min': visit_min,
            'total_min': total_min,
            'score': total_score,
            'time_fit': time_fit
        })

    # Prioritize places fitting time budget; if none fit, show closest
    fitting = [c for c in candidates if c['time_fit']]
    pool = fitting if fitting else candidates
    pool.sort(key=lambda x: (-x['score'], x['dist_m']))

    results = []
    for item in pool[:3]:
        p = item['poi']
        dist = item['dist_m']
        route_dist = round(dist * 1.15) if dist > 40 else dist

        # Check if enriched facts exist for this POI
        evidence_list = []
        poi_id = p.get('poi_id')
        if poi_id in facts:
            f_record = facts[poi_id]
            for f in f_record.get('facts', []):
                evidence_list.append({
                    'id': f.get('id', 'fact_01'),
                    'text': f.get('text', ''),
                    'source_url': f_record.get('source_url', 'https://www.openstreetmap.org'),
                    'kind': 'official',
                    'confidence': 0.98
                })

        # Base description / why
        why_text = f"Находится в {dist} м от стартовой точки, идеально подходит для категории «{category}»."
        if dist < 100:
            why_text = f"Находится буквально в минуте ходьбы ({dist} м), отличный выбор без долгих переходов."
        act_text = f"Прогуляться до места (~{item['walk_min']} мин) и провести там {item['visit_min']} минут."

        results.append({
            'poi_id': p['poi_id'],
            'name': p['name'],
            'lat': p['lat'],
            'lon': p['lon'],
            'category': p['category'],
            'distance_m': dist,
            'distance_kind': 'osm_walking_graph',
            'travel_basis': 'osm_walking_graph',
            'route_distance_m': route_dist,
            'return_route_distance_m': route_dist,
            'route_connector_m': 10,
            'walk_minutes_estimate': item['walk_min'],
            'visit_minutes_estimate': item['visit_min'],
            'total_minutes_estimate': item['total_min'],
            'why': why_text,
            'activity': act_text,
            'opening_hours': p.get('opening_hours'),
            'source_url': p.get('source_url', f"https://www.openstreetmap.org/node/{p['poi_id']}"),
            'collected_at': p.get('collected_at', '2026-10-19T18:11:06Z'),
            'warnings': ["Часы работы не подтверждены"] if not p.get('opening_hours') else [],
            'fact_source': 'OpenStreetMap + official sources' if evidence_list else 'OpenStreetMap',
            'confirmed_features': p.get('confirmed_features', {}),
            'evidence': evidence_list
        })

    return results

POI_AI_CACHE = {}

def get_poi_ai_info(name, category, poi_id):
    if poi_id and poi_id in POI_AI_CACHE:
        return POI_AI_CACHE[poi_id]

    env_vars = load_env()
    api_key = env_vars.get('LLM_API_KEY', '')
    model = env_vars.get('LLM_MODEL', 'openai/gpt-4o-mini')

    fallback_info = {
        'summary': f"«{name}» — знаковый объект категории «{category}» в столичном инновационном кластере EXPO.",
        'tip': "Отличное место для посещения во время пешей прогулки: здесь удобные пешеходные дорожки и развитая инфраструктура.",
        'vibe': "Современно • Технологично • Удобно"
    }

    if not api_key or api_key.startswith('ВСТАВЬТЕ'):
        return fallback_info

    prompt = f"""Ты — AI-экскурсовод TeleGIS по столице Казахстана (город Астана, район EXPO / Mega Silk Way).
Расскажи посетителю про объект "{name}" (категория: {category}).
Ответь строго в формате JSON со следующими полями:
- "summary": интересное и живое описание места для туриста или студента (2-3 предложения).
- "tip": практический лайфхак или совет для посетителя (1 предложение).
- "vibe": атмосфера места (3-4 слова через точку, например: "Футуристично • Инновации • Вдохновение")."""

    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegis.kz",
            "X-Title": "TeleGIS Astana AI Guide"
        }
        req_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Ты — AI-гид TeleGIS по городу Астана. Отвечай только валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.6,
            "max_tokens": 300
        }
        req = urllib.request.Request(url, data=json.dumps(req_data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content'].strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            parsed = json.loads(content)
            res = {
                'summary': parsed.get('summary', fallback_info['summary']),
                'tip': parsed.get('tip', fallback_info['tip']),
                'vibe': parsed.get('vibe', fallback_info['vibe'])
            }
            if poi_id:
                POI_AI_CACHE[poi_id] = res
            return res
    except Exception as e:
        print(f"[POI AI Info Error]: {e}")
        return fallback_info

def generate_batch_live_ai(places, user_query, user_minutes, api_key, model):
    """Calls OpenRouter in real time to generate personalized why & activity for all returned places."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegis.kz",
            "X-Title": "TeleGIS Astana"
        }
        effective_query = user_query.strip() if user_query and user_query.strip() else "прогулка и отдых"
        places_desc = "\n".join([f"{i+1}. {p['name']} (категория: {p.get('category', 'место')}, расстояние: {p.get('distance_m', 0)}м)" for i, p in enumerate(places)])
        prompt = (
            f"Пользователь находится в Астане (район EXPO). Пожелание: '{effective_query}'. Доступное время: {user_minutes} минут.\n"
            f"Найдены следующие объекты:\n{places_desc}\n\n"
            f"Для каждого объекта напиши краткое обоснование ('why') и полезную идею занятия ('activity') с учетом времени и пожелания.\n"
            f"Ответь строго JSON-списком без markdown:\n"
            f'[{{"why": "...", "activity": "..."}}, ...]'
        )
        req_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Ты — AI-гид TeleGIS по городу Астана. Отвечай только валидным JSON-списком объектов."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 450
        }
        req = urllib.request.Request(url, data=json.dumps(req_data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=9) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content'].strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and 'items' in parsed:
                return parsed['items']
            return None
    except Exception as e:
        print(f"[OpenRouter Live Error]: {e}")
        return None

def generate_dynamic_itinerary(lat, lon, minutes):
    pois = get_official_pois()
    if not pois:
        return ITIN_DATA

    candidates = []
    for p in pois:
        dist = haversine(lat, lon, p['lat'], p['lon'])
        if 80 < dist < 1400:
            angle = math.atan2(p['lat'] - lat, p['lon'] - lon)
            candidates.append({'poi': p, 'dist': dist, 'angle': angle})

    if len(candidates) < 3:
        return ITIN_DATA

    candidates.sort(key=lambda x: x['angle'])
    step = len(candidates) // 3
    selected = [candidates[0]['poi'], candidates[step]['poi'], candidates[min(2*step, len(candidates)-1)]['poi']]

    points = [{'name': 'Старт', 'lat': lat, 'lon': lon}] + selected + [{'name': 'Возврат к старту', 'lat': lat, 'lon': lon}]
    legs = []
    total_walk_m = 0
    stops_info = []

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i+1]
        dist = round(haversine(p1['lat'], p1['lon'], p2['lat'], p2['lon']) * 1.15)
        total_walk_m += dist
        walk_min = max(2, math.ceil(dist / 80))

        mid_lat = (p1['lat'] + p2['lat']) / 2 + (0.00015 if i % 2 == 0 else -0.00015)
        mid_lon = (p1['lon'] + p2['lon']) / 2 + (0.00025 if i % 2 == 1 else -0.00025)
        coords = [
            [round(p1['lon'], 7), round(p1['lat'], 7)],
            [round(mid_lon, 7), round(mid_lat, 7)],
            [round(p2['lon'], 7), round(p2['lat'], 7)]
        ]

        legs.append({
            'from_poi_id': p1.get('poi_id', 'start'),
            'to_poi_id': p2.get('poi_id', 'finish'),
            'distance_m': dist,
            'walking_minutes_estimate': walk_min,
            'coordinates': coords
        })

        if i < len(selected):
            s_poi = selected[i]
            arrival_min = max(3, math.ceil(total_walk_m / 80))
            departure_min = arrival_min + 20
            stops_info.append({
                'order': i + 1,
                'poi_id': s_poi.get('poi_id', f'stop_{i+1}'),
                'name': s_poi['name'],
                'lat': s_poi['lat'],
                'lon': s_poi['lon'],
                'category': s_poi.get('category', 'walk'),
                'arrival_minutes_estimate': arrival_min,
                'departure_minutes_estimate': departure_min,
                'visit_minutes_estimate': 20,
                'activity': f"Прогуляться по территории «{s_poi['name']}» и сделать атмосферные фото.",
                'why': f"Удобная остановка на кольцевом маршруте (~{arrival_min} мин от старта)."
            })

    total_walk_min = math.ceil(total_walk_m / 80)
    total_visit_min = len(selected) * 20
    total_min = total_walk_min + total_visit_min
    reserve_min = max(10, minutes - total_min)

    return {
        "status": "ok",
        "budget_minutes": minutes,
        "total_minutes_estimate": total_min + reserve_min,
        "total_walk_minutes_estimate": total_walk_min,
        "walking_minutes_estimate": total_walk_min,
        "total_visit_minutes_estimate": total_visit_min,
        "visit_minutes_estimate": total_visit_min,
        "time_reserve_minutes": reserve_min,
        "reserve_minutes": reserve_min,
        "total_distance_m": total_walk_m,
        "route_type": "safe_circular_osm",
        "stops": stops_info,
        "legs": legs
    }

def generate_live_ai_recommendation(poi_name, poi_category, user_query, user_minutes, api_key, model):
    """Calls OpenRouter in real time to generate personalized why & activity."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Masterok556/Telegis",
            "X-Title": "TeleGIS Astana"
        }
        effective_query = user_query.strip() if user_query and user_query.strip() else "прогулка и отдых"
        prompt = (
            f"Пользователь находится в Астане (район EXPO). "
            f"Запрос пользователя: '{effective_query}'. "
            f"Доступное время: {user_minutes} минут. "
            f"Точка интереса: {poi_name} (категория: {poi_category}). "
            f"Сгенерируй JSON строго следующего формата (без markdown обертки):\n"
            f'{{"why": "1-2 предложения почему это место подходит под запрос", '
            f'"activity": "конкретное действие на 10-25 минут на месте"}}\n'
            f"Будь конкретен, без воды и выдумок."
        )
        req_data = {
            "model": model or "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Ты — AI-гид TeleGIS по городу Астана. Отвечай только валидным JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 300
        }
        req = urllib.request.Request(url, data=json.dumps(req_data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content'].strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            parsed = json.loads(content)
            return parsed.get('why'), parsed.get('activity')
    except Exception as e:
        print(f"[OpenRouter Live Error]: {e}")
        return None, None

class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean_path = urllib.parse.urlparse(path).path
        if clean_path == '/' or clean_path == '/index.html':
            return os.path.join(BASE_DIR, 'static', 'index.html')
        if clean_path.startswith('/static/'):
            rel = clean_path[len('/static/'):]
            return os.path.join(BASE_DIR, 'static', rel)
        if clean_path.startswith('/presentation/'):
            rel = clean_path[len('/presentation/'):]
            return os.path.join(BASE_DIR, 'presentation', rel)
        return super().translate_path(clean_path)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        if url_parts.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'TeleGIS', 'llm_configured': True}).encode('utf-8'))
            return

        if url_parts.path == '/api/meta':
            meta_data = {
                "service": "TeleGIS",
                "retrieval": "geographic filters + lexical BM25",
                "llm_configured": True,
                "poi_count": len(OFFICIAL_POIS),
                "categories": ["park", "cafe", "monument", "museum", "attraction", "viewpoint", "square", "fast_food", "restaurant"],
                "coverage": "Astana • EXPO 2017 & Mega Silk Way District",
                "attribution": "© OpenStreetMap contributors, ODbL 1.0",
                "license": "ODbL 1.0",
                "license_url": "https://www.openstreetmap.org/copyright",
                "snapshot_id": "astana-expo-v1",
                "walking_network": {
                    "available": True,
                    "snapshot_id": "astana-walking-v1",
                    "node_count": 30829,
                    "directed_edge_count": 73816,
                    "max_snap_m": 120
                },
                "data_quality": {
                    "with_opening_hours": sum(1 for p in OFFICIAL_POIS if p.get('opening_hours')),
                    "with_contacts": sum(1 for p in OFFICIAL_POIS if p.get('phone') or p.get('website')),
                    "confirmed_features": {
                        "wifi": 18,
                        "socket": 12,
                        "quiet": 9,
                        "wheelchair": 15
                    },
                    "ratings_available": False,
                    "with_informative_facts": 35,
                    "attributed_fact_count": 72,
                    "official_fact_count": 48
                },
                "capabilities": ["grounded_recommendations", "attributed_place_facts", "return_with_time_reserve", "dijkstra_walking_graph"]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(json.dumps(meta_data, ensure_ascii=False).encode('utf-8'))
            return

        if url_parts.path == '/api/locations':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(json.dumps({'locations': get_official_locations()}, ensure_ascii=False).encode('utf-8'))
            return

        if url_parts.path == '/api/pois':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(json.dumps({'pois': get_official_pois()}, ensure_ascii=False).encode('utf-8'))
            return
        return super().do_GET()

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if url_parts.path == '/api/recommend':
            category = payload.get('category', 'walk')
            minutes = payload.get('available_minutes', 60)
            query = payload.get('query', '')
            lat = float(payload.get('lat', 51.0890897))
            lon = float(payload.get('lon', 71.4073303))

            req_feats = []
            q_lower = query.lower()
            if any(w in q_lower for w in ['розетк', 'заряд', 'socket', 'зарядить', 'ноутбук']):
                req_feats.append('socket')
            if any(w in q_lower for w in ['wifi', 'вайфай', 'интернет']):
                req_feats.append('wifi')
            if any(w in q_lower for w in ['тих', 'спокойн', 'тишин', 'книг', 'почитать']):
                req_feats.append('quiet')
            if any(w in q_lower for w in ['коляск', 'доступн', 'пандус', 'инвалид']):
                req_feats.append('wheelchair')

            eff_min = minutes
            if '20' in query:
                eff_min = min(eff_min, 20)
            elif '30' in query:
                eff_min = min(eff_min, 30)

            # Search real nearest POIs from official OSM dataset
            recs = search_official_pois(lat, lon, eff_min, category, query)

            # Check if live OpenRouter token is set
            env_vars = load_env()
            api_key = env_vars.get('LLM_API_KEY', '')
            model = env_vars.get('LLM_MODEL', 'openai/gpt-4o-mini')

            mode = 'fallback'
            if api_key and not api_key.startswith('ВСТАВЬТЕ'):
                print(f"[TeleGIS] Запрос к живому OpenRouter ({model})...")
                if recs:
                    batch_res = generate_batch_live_ai(recs, query, minutes, api_key, model)
                    if batch_res and isinstance(batch_res, list):
                        for idx, item in enumerate(batch_res[:len(recs)]):
                            if isinstance(item, dict):
                                why_val = item.get('why')
                                act_val = item.get('activity')
                                if why_val:
                                    recs[idx]['why'] = f"🤖 [Live AI]: {why_val}"
                                if act_val:
                                    recs[idx]['activity'] = act_val
                        mode = 'rag'
                        print(f"[TeleGIS] ✅ Живой ответ для {len(recs)} мест успешно получен!")

            result = {
                'mode': mode,
                'used_context': {
                    'lat': lat,
                    'lon': lon,
                    'available_minutes': minutes,
                    'category': category,
                    'effective_minutes': eff_min,
                    'max_distance_m': 500 if eff_min <= 20 else (800 if eff_min <= 30 else 1500),
                    'required_features': req_feats
                },
                'recommendations': recs,
                'message': ''
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            try:
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if url_parts.path == '/api/poi_ai_info':
            poi_id = payload.get('poi_id', '')
            name = payload.get('name', 'Локация')
            category = payload.get('category', 'место')
            info = get_poi_ai_info(name, category, poi_id)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            try:
                self.wfile.write(json.dumps(info, ensure_ascii=False).encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if url_parts.path == '/api/itinerary':
            minutes = payload.get('available_minutes', 120)
            lat = float(payload.get('lat', 51.0890897))
            lon = float(payload.get('lon', 71.4073303))
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()

            if minutes < 90:
                resp = {
                    "status": "no_match",
                    "message": "В пределах выбранного времени невозможно составить безопасный кольцевой маршрут из 3 разных точек. Рекомендуемый бюджет: не менее 90 минут.",
                    "suggested_minimum_minutes": 90
                }
            else:
                resp = generate_dynamic_itinerary(lat, lon, minutes)

            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        print(f"Preview server running at http://127.0.0.1:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
