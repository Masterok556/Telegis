/* Behavioral checks for request contracts and async isolation, without a browser.
 * Run: node tests/frontend_contract.cjs
 * Browser layout and map interactions still require the real browser smoke check.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
  constructor() {
    this.children = []; this.dataset = {}; this.value = ''; this.textContent = '';
    this.style = {}; this.events = {}; this.disabled = false;
    const classes = new Set();
    this.classList = {
      add: (...values) => values.forEach(v => classes.add(v)),
      remove: (...values) => values.forEach(v => classes.delete(v)),
      contains: value => classes.has(value),
      toggle: (value, force) => {
        const add = force === undefined ? !classes.has(value) : force;
        if (add) classes.add(value); else classes.delete(value);
      }
    };
  }
  appendChild(child) { this.children.push(child); return child; }
  append(...children) { children.forEach(child => this.appendChild(child)); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, callback) { this.events[type] = callback; }
  setAttribute(key, value) { this[key] = value; }
  getAttribute(key) { return this[key]; }
  removeAttribute(key) { delete this[key]; }
  querySelector() { return null; }
  focus() { this.focused = true; document.activeElement = this; }
  scrollTo(options) { this.lastScroll = options; }
  getBoundingClientRect() { return { width: 440, height: 405 }; }
  set innerHTML(value) { this._html = value; this.children = []; }
  get innerHTML() { return this._html || ''; }
}

const elements = new Map();
const get = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
const category = { value: 'walk' };
let minutes = { value: '60' };
const tagChip = new Element();
tagChip.setAttribute('data-fill', 'Хочу тихое место');
const document = {
  getElementById: get,
  querySelectorAll: selector => selector === '.tag-chip' ? [tagChip] : [],
  querySelector: selector => {
    if (selector === 'input[name="category"]:checked') return category;
    if (selector === 'input[name="availableMinutes"]:checked') return minutes;
    if (selector.startsWith('input[name="availableMinutes"][value=')) return null;
    return null;
  },
  createElement: () => new Element(),
  addEventListener: () => {},
  documentElement: {},
};
const origin = { dataset: { lat: '51.0890897', lon: '71.4073303' } };
get('locationSelect').selectedOptions = [origin];
const requests = [];
const pending = [];
let fetchMode = 'immediate';
let customBody = null;
let httpStatus = 503;
const context = {
  document, window: { location: { search: '' } }, navigator: {},
  console, AbortController, URL, URLSearchParams, structuredClone, setTimeout, clearTimeout,
  fetch: (url, options = {}) => {
    requests.push({ url, options, body: options.body ? JSON.parse(options.body) : null });
    if (fetchMode === 'network-error') return Promise.reject(new TypeError('Failed to fetch'));
    if (fetchMode === 'http-error') return Promise.resolve({
      ok: false, status: httpStatus, json: async () => ({ detail: 'Датасет недоступен. Запустите сборщик.' })
    });
    if (fetchMode === 'custom') return Promise.resolve({ ok: true, json: async () => customBody });
    if (fetchMode === 'geometry') return Promise.resolve({ ok: true, json: async () => ({
      type: 'FeatureCollection', features: [{ type: 'Feature', geometry: {
        type: 'MultiLineString', coordinates: [[[71.4, 51.09], [71.41, 51.10]]]
      }, properties: {} }]
    }) });
    if (fetchMode === 'pending') return new Promise(resolve => pending.push(resolve));
    return Promise.resolve({ ok: true, json: async () => ({ mode: 'fallback', recommendations: [] }) });
  },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/ui-copy.js'), 'utf8'), context);
const source = fs.readFileSync(path.join(__dirname, '../static/app.js'), 'utf8');
vm.runInContext(source.replace("  document.addEventListener('DOMContentLoaded', init);", `
  globalThis.harness = {
    handleFormSubmit, executeSearch, invalidateSearch, openPoiDrawer, closePoiDrawer,
    selectMinutes, handleItinerarySuccess, openTelemetryModal, mockResponse,
    bindEvents, setCatalog: poi => poiCatalog.set(poi.poi_id, poi),
    categoryName, setLanguage, modelStatus, initMap, setUIState, mapViewPadding,
    loadWeather, renderWeather, handleGeoLocation, buildWalkingRouteToPoi, clearRoutePolyline,
    trapModalFocus, closeTelemetryModal, renderUsedContext,
    setWeather: value => { weatherSnapshot = value; lastClimateContext = null; renderWeather(); },
    setLive: () => { isMockMode = false; },
    setMap: value => { leafletMap = value; },
    getPointController: () => pointRouteController,
    getTranslations: () => window.TELEGIS_UI_COPY,
    setMode: value => { appMode = value; },
    setMock: value => { isMockMode = true; mockData = value; },
    setMeta: value => { cachedSystemMeta = value; },
    getController: () => activeAbortController,
    results: [], errors: []
  };
  handleSearchSuccess = data => harness.results.push(data);
  loadSystemMeta = async () => {};
  handleSearchError = text => harness.errors.push(text);
`), context);
const h = context.harness;
const tick = () => new Promise(resolve => setImmediate(resolve));
const response = value => ({ ok: true, json: async () => value });
const common = { query: 'Хочу погулять', lat: 51.0890897, lon: 71.4073303, available_minutes: 60 };

(async () => {
  assert.equal(h.modelStatus(), 'Проверяем состояние API…');
  assert.equal(h.categoryName('park'), 'Парк');
  assert.equal(h.categoryName('<script>'), 'Место');
  h.setLanguage('kz');
  assert.equal(h.categoryName('park'), 'Саябақ');
  h.setLanguage('en');
  assert.equal(h.categoryName('artwork'), 'Public art');
  h.setLanguage('ru');
  h.handleFormSubmit({ preventDefault() {} });
  await tick();
  assert.deepEqual(Object.keys(requests[0].body).sort(), ['available_minutes', 'category', 'climate_shield', 'lat', 'locale', 'lon', 'query']);
  assert.equal(requests[0].body.climate_shield, false);
  assert.equal(requests[0].body.locale, 'ru');
  h.setMode('itinerary'); category.value = 'cafe';
  h.handleFormSubmit({ preventDefault() {} });
  await tick();
  assert.deepEqual(Object.keys(requests[1].body).sort(), ['available_minutes', 'climate_shield', 'include_coffee', 'lat', 'locale', 'lon', 'query']);
  assert.equal(requests[1].body.include_coffee, true);

  h.setMode('places'); fetchMode = 'pending';
  const first = h.executeSearch({ ...common, category: 'walk' });
  const firstController = h.getController();
  const second = h.executeSearch({ ...common, category: 'cafe' });
  const secondController = h.getController();
  assert.equal(firstController.signal.aborted, true);
  pending.shift()(response({ request: 'obsolete' }));
  await first;
  assert.equal(h.getController(), secondController, 'old finally must not clear new controller');
  assert.equal(get('submitBtn').disabled, true);
  pending.shift()(response({ request: 'latest' }));
  await second;
  assert.equal(h.results.at(-1).request, 'latest');
  assert.equal(h.results.some(item => item.request === 'obsolete'), false);

  const cancel = h.executeSearch({ ...common, category: 'walk' });
  h.invalidateSearch();
  pending.shift()(response({ request: 'cancelled' }));
  await cancel;
  assert.equal(h.results.some(item => item.request === 'cancelled'), false);
  assert.equal(h.getController(), null);
  fetchMode = 'network-error';
  await h.executeSearch({ ...common, category: 'walk' });
  assert.equal(h.errors.at(-1), 'Не удалось связаться с сервером. Проверьте, что Telegis запущен, и повторите запрос.');
  assert.equal(h.getController(), null);
  assert.equal(get('submitBtn').disabled, false);
  h.setLanguage('en'); fetchMode = 'http-error';
  for (const status of [503, 404, 422]) {
    httpStatus = status;
    await h.executeSearch({ ...common, category: 'walk', locale: 'en' });
    assert.match(h.errors.at(-1), new RegExp(`HTTP ${status}`));
    assert.doesNotMatch(h.errors.at(-1), /[А-Яа-яЁё]/, 'HTTP diagnostics must not leak untranslated backend copy');
  }
  h.setLanguage('ru');
  fetchMode = 'pending';

  h.bindEvents();
  get('climateShieldCheck').checked = true;
  const unchangedOrigin = get('locationSelect').selectedOptions[0];
  fetchMode = 'custom'; customBody = { status: 'unavailable', current: null };
  get('climateShieldCheck').events.change();
  await tick();
  assert.equal(get('locationSelect').selectedOptions[0], unchangedOrigin, 'shield must not change user start');
  get('climateShieldCheck').checked = false;
  fetchMode = 'pending';
  const chipped = h.executeSearch({ ...common, category: 'walk' });
  tagChip.events.click();
  assert.equal(get('queryInput').value, 'Хочу тихое место');
  pending.shift()(response({ request: 'before-chip' }));
  await chipped;
  assert.equal(h.results.some(item => item.request === 'before-chip'), false);
  assert.equal(h.getController(), null);

  h.setCatalog({ poi_id: 'two', confirmed_features: { wifi: true }, tags: { 'addr:street': 'Test Street' } });
  h.openPoiDrawer({ poi_id: 'one', name: 'One', confirmed_features: {}, description: 'First' });
  h.openPoiDrawer({ poi_id: 'two', name: 'Two', description: 'Second' });
  pending.shift()(response({ summary: 'OUTDATED' }));
  await tick();
  assert.equal(get('drawerAiSummary').textContent, 'Second');
  pending.shift()(response({ summary: 'CURRENT' }));
  await tick();
  assert.equal(get('drawerAiSummary').textContent, 'CURRENT');
  assert.ok(get('drawerFeaturesGrid').children.some(item => item.textContent === '📶 Wi-Fi: указано в OSM'));
  assert.ok(get('drawerAddress').textContent.includes('Test Street'));
  assert.ok(get('drawerFeaturesGrid').children.some(item => item.textContent === '🕒 Часы не подтверждены'));
  assert.ok(get('drawerFeaturesGrid').children.some(item => item.textContent.includes('Розетки: нет подтверждённых данных')));
  assert.equal(get('drawerHeroImg').getAttribute('src'), undefined, 'unknown photographs remain placeholders');
  assert.equal(get('poiDrawer').getAttribute('inert'), undefined);
  h.closePoiDrawer();
  assert.equal(get('poiDrawer').getAttribute('inert'), '');

  h.selectMinutes(83);
  assert.equal(get('timeSelector').children.at(-1).children[0].value, 83);
  assert.equal(get('timeSelector').children.at(-1).children[0].checked, true);
  get('queryInput').value = 'Хочу маршрут на 60 минут';
  h.handleItinerarySuccess({ status: 'no_match', message: 'Need more time', suggested_minimum_minutes: 83,
    used_context: { ...common, effective_minutes: 60 }, stops: [] });
  get('emptyAdviceContainer').children[0].events.click();
  assert.equal(get('queryInput').value, 'Хочу маршрут на 60 минут');
  assert.equal(get('queryInput').focused, true);
  assert.ok(get('emptyAdviceContainer').children.at(-1).textContent.includes('измените его вручную'));

  h.setMeta({ poi_count: 49, data_quality: { attributed_fact_count: 72, official_fact_count: 6,
    confirmed_features: { wifi: 5, socket: 0, quiet: 0, wheelchair: 0 } } });
  h.openTelemetryModal();
  assert.match(get('telemetryModalBody').innerHTML, /Розетки: 0/);
  assert.doesNotMatch(get('telemetryModalBody').innerHTML, /Розетки: 12|gpt-4o-mini|100%/);

  context.window.matchMedia = () => ({ matches: true });
  context.window.innerWidth = 367;
  context.window.innerHeight = 676;
  assert.equal(h.mapViewPadding().paddingBottomRight[1], 425);
  get('gisSidebar').classList.add('collapsed');
  assert.equal(h.mapViewPadding().paddingBottomRight[1], 84);
  get('gisSidebar').classList.remove('collapsed');
  get('sidebarContent').offsetTop = 650;
  get('sheetHandle').offsetHeight = 20;
  h.setUIState('empty');
  assert.equal(get('gisSidebar').lastScroll.top, 630);
  assert.equal(get('gisSidebar').classList.contains('collapsed'), false);
  context.window.matchMedia = () => ({ matches: false });
  context.window.innerWidth = 1200;
  assert.equal(h.mapViewPadding().paddingTopLeft[0], 472);

  let tileError, tileOptions, attribution = '', removed = 0, graphs = 0;
  const layer = () => ({
    addTo() { return this; }, bindPopup() { return this; },
    setLatLng() {}, setRadius() {}, clearLayers() {},
    getLatLng() { return { lat: 51.09, lng: 71.4 }; }
  });
  const map = {
    attributionControl: { setPrefix() {}, addAttribution(text) { attribution = text; } },
    on() {}, removeLayer() { removed++; }, createPane() { return { style: {} }; }
  };
  context.L = {
    map: () => map, layerGroup: layer, divIcon: value => value, marker: layer, circle: layer,
    canvas: () => ({}), geoJSON: () => { graphs++; return layer(); },
    tileLayer: (_, options) => {
      tileOptions = options;
      return { on(_, callback) { tileError = callback; }, addTo() {} };
    }
  };
  context.window.L = context.L;
  fetchMode = 'geometry';
  h.initMap();
  assert.equal(tileOptions.referrerPolicy, 'strict-origin-when-cross-origin');
  assert.match(attribution, /openstreetmap.org\/copyright/);
  const beforeGeometry = requests.length;
  const failedTile = { style: {} };
  tileError({ tile: failedTile });
  tileError({ tile: failedTile });
  await new Promise(resolve => setTimeout(resolve, 5));
  assert.equal(failedTile.style.visibility, 'hidden');
  assert.equal(requests.length - beforeGeometry, 1, 'load local map once; do not retry failing raster');
  assert.equal(requests.at(-1).url, '/api/walking-map.geojson');
  assert.equal(graphs, 1);
  assert.ok(removed >= 1);
  assert.match(get('mapBackgroundStatus').textContent, /Локальная схема дорожек OSM/);

  const treeText = el => [el.textContent || '', ...el.children.map(treeText)].join(' ');
  for (const lang of ['ru', 'kz', 'en']) {
    h.setLanguage(lang);
    for (const [key, values] of Object.entries(h.getTranslations())) {
      assert.equal(typeof values[lang], 'string', `translation ${key}/${lang} exists`);
      assert.ok(values[lang].length, `translation ${key}/${lang} is nonempty`);
    }
  }
  assert.equal(document.documentElement.lang, 'en');
  h.setWeather({ status: 'live', current: { temperature_c: 0, wind_m_s: 0, gust_m_s: 3 },
    valid_at: '2026-10-20T17:30:00Z', fetched_at: '2026-10-20T17:31:00Z',
    source: 'Open-Meteo', source_url: 'https://open-meteo.com/' });
  assert.equal(get('climateWeatherBadge').dataset.weatherStatus, 'live');
  assert.match(treeText(get('climateWeatherBadge')), /0 °C/);
  assert.match(treeText(get('climateWeatherBadge')), /wind 0 m\/s/);
  assert.match(treeText(get('climateWeatherBadge')), /Forecast time/);
  assert.match(treeText(get('climateWeatherBadge')), /Fetched by server/);
  assert.match(treeText(get('climateWeatherBadge')), /Open-Meteo/);
  h.setWeather({ status: 'stale', current: { temperature_c: 4 } });
  assert.match(treeText(get('climateWeatherBadge')), /Stale weather data/);
  h.setWeather({ status: 'unavailable', current: null });
  assert.doesNotMatch(treeText(get('climateWeatherBadge')), /°C|m\/s/);
  h.setWeather({ status: 'demo', current: { temperature_c: -10 } });
  assert.match(treeText(get('climateWeatherBadge')), /not current weather/);
  fetchMode = 'custom'; customBody = { status: 'live', current: { temperature_c: 6 } };
  await h.loadWeather();
  assert.equal(requests.at(-1).url, '/api/weather?locale=en');
  assert.match(treeText(get('climateWeatherBadge')), /6 °C/);
  fetchMode = 'network-error';
  await h.loadWeather();
  assert.equal(get('climateWeatherBadge').dataset.weatherStatus, 'unavailable');

  h.setLanguage('ru');
  let geoCalls = 0;
  context.navigator.geolocation = { getCurrentPosition(ok, fail) { geoCalls++; fail({ code: 1 }); } };
  assert.equal(geoCalls, 0);
  h.handleGeoLocation();
  assert.equal(geoCalls, 1);
  assert.match(get('geoStatus').textContent, /не разрешён/);
  assert.equal(get('geoBtn').disabled, false);

  const drawCalls = [];
  context.L.polyline = coordinates => {
    drawCalls.push(coordinates);
    return { addTo() { return this; }, getBounds() { return {}; } };
  };
  h.setMap({ ...map, fitBounds() {} });
  const poi = { poi_id: 'osm_node_123', name: 'Route destination', lat: 51.10, lon: 71.42 };
  customBody = { status: 'ready', coordinates: [[71.4073303, 51.0890897], [71.41, 51.095], [71.42, 51.10]],
    distance_m: 1700, walk_minutes_estimate: 25, warnings: ['One way only'] };
  fetchMode = 'custom';
  await h.buildWalkingRouteToPoi(poi);
  assert.equal(requests.at(-1).url, '/api/route');
  assert.deepEqual(Object.keys(requests.at(-1).body).sort(), ['climate_shield', 'lat', 'locale', 'lon', 'poi_id']);
  assert.equal(drawCalls.length, 1);
  assert.equal(drawCalls[0].length, 3, 'draw actual network intermediate vertex, not straight start/end line');
  assert.equal(drawCalls[0][1][0], 51.095);
  assert.match(treeText(get('routeBannerStats')), /25 мин/);
  assert.match(treeText(get('routeBannerStats')), /One way only/);
  customBody = { status: 'no_match', message: 'No verified path', coordinates: [] };
  await h.buildWalkingRouteToPoi(poi);
  assert.equal(drawCalls.length, 1, 'missing route must not invent geometry');
  assert.equal(get('routeBannerStats').textContent, 'No verified path');
  fetchMode = 'pending';
  const oldRoute = h.buildWalkingRouteToPoi(poi);
  const oldController = h.getPointController();
  h.invalidateSearch();
  assert.equal(oldController.signal.aborted, true);
  pending.shift()(response({ status: 'ready', coordinates: [[71, 51], [72, 52]], distance_m: 1, walk_minutes_estimate: 1 }));
  await oldRoute;
  assert.equal(drawCalls.length, 1, 'cancelled point route must not reappear');

  const modalButton = get('modalCloseBtn');
  get('telemetryModal').querySelectorAll = () => [modalButton];
  h.openTelemetryModal();
  assert.equal(document.activeElement, modalButton);
  let prevented = false;
  h.trapModalFocus({ key: 'Tab', preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  h.closeTelemetryModal();
  assert.equal(get('gisSidebar').getAttribute('inert'), undefined);

  let startupGeoCalls = 0;
  const bootContext = {
    ...context,
    window: { location: { search: '' } },
    navigator: { geolocation: { getCurrentPosition() { startupGeoCalls++; } } }
  };
  vm.createContext(bootContext);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/ui-copy.js'), 'utf8'), bootContext);
  vm.runInContext(source.replace("  document.addEventListener('DOMContentLoaded', init);", `
    initMap = () => {};
    bindEvents = () => {};
    renderTimeSelector = () => {};
    loadLocations = async () => {};
    loadSystemMeta = async () => {};
    loadAndRenderAllPoisOnMap = async () => {};
    loadWeather = async () => {};
    globalThis.boot = init;
  `), bootContext);
  await bootContext.boot();
  assert.equal(startupGeoCalls, 0, 'page initialization must never request GPS');

  const fixtures = JSON.parse(fs.readFileSync(path.join(__dirname, '../static/mock.json'), 'utf8'));
  h.setMock(fixtures);
  for (const scenario of fixtures.scenarios) {
    const result = await h.mockResponse(scenario.request, scenario.mode);
    if (result.status === 'ready') {
      assert.ok(result.total_minutes_estimate <= scenario.request.available_minutes);
      assert.ok(result.legs.length >= 3);
    }
    if (scenario.mode === 'places') assert.ok(Array.isArray(result.recommendations));
  }
  const unmatched = await h.mockResponse({ ...common, lat: 10, include_coffee: true }, 'itinerary');
  assert.equal(unmatched.status, 'no_match');
  assert.equal(unmatched.stops.length, 0);
  console.log('PASS: strict locale/climate payloads; stale search/drawer/route isolation; sourced geometry only; live/stale/unavailable/demo weather and timestamps; explicit GPS; truthful photos/amenities; focus; RU/KZ/EN copy; original mock and budget regressions.');
})().catch(error => { console.error(error); process.exitCode = 1; });
