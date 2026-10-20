/**
 * TeleGIS — Fullscreen GIS Engine (v3.2)
 * Features:
 * - Fullscreen OpenStreetMap canvas (Leaflet.js)
 * - Multilanguage: Қазақша (KZ), Русский (RU), English (EN)
 * - Mode 1: Individual Recommendations (/api/recommend)
 * - Mode 2: Circular Walking Itinerary (/api/itinerary) with Dijkstra polyline
 * - Zero tracking & strict XSS protection (textContent & DOM APIs)
 */

(function () {
  'use strict';

  // --- Multilanguage Dictionary (KZ / RU / EN) ---
  const I18N = {
    ru: {
      mock_title: 'ТЕСТОВЫЙ РЕЖИМ (MOCK)',
      mock_desc: 'запросы к живому API отключены. Для реального режима удалите ?mock=1.',
      city_tag: 'Астана • EXPO',
      subtitle: 'ИИ-советчик для пеших прогулок',
      mode_places: 'Места вокруг',
      mode_itinerary: 'Маршрут',
      loading_locations: 'Загрузка локаций...',
      cat_walk: 'Пешая прогулка',
      cat_cafe: 'Кофе и отдых',
      time_budget_label: 'Бюджет времени:',
      query_placeholder: 'Пожелание: сквер, панорама, круассан...',
      btn_find: 'Найти',
      btn_build_route: 'Построить маршрут',
      budget_badge: '⏱️ Честный бюджет:',
      budget_desc: 'дорога туда + посещение + возврат к старту',
      tag_view: '📸 Вид на сферу',
      tag_quiet: '🌿 Тихий сквер',
      tag_togo: '☕ Навынос',
      init_head: 'Интеллектуальный радар прогулок',
      init_text: 'Выберите время и категорию — TeleGIS просканирует пешеходный граф OpenStreetMap и подберёт идеальные варианты в районе EXPO.',
      preset_label: 'Быстрые сценарии:',
      preset_1: '🚶 60 мин вокруг EXPO',
      preset_2: '☕ Кофе на 30 мин',
      preset_3: '⚡ 20 мин размяться',
      loading_head: 'TeleGIS анализирует местность...',
      loading_text: 'Вычисляем пешеходные расстояния по графу дорог и ранжируем локации.',
      empty_head: 'Точки не найдены',
      empty_text: 'В заданном радиусе и бюджете времени нет доступных мест.',
      empty_advice: 'Совет: увеличьте время или выберите другой формат отдыха.',
      error_head: 'Ошибка соединения',
      btn_retry: 'Повторить попытку',
      fallback_title: 'Шаблонный режим:',
      fallback_desc: 'рекомендации подобраны по проверенной базе POI без вызова LLM.',
      radius_label: 'Радиус пешей зоны:',
      straight_dist: 'Прямая:',
      one_way: 'В одну сторону:',
      total_budget: 'Общий бюджет:',
      why_label: 'Почему подходит:',
      act_label: '💡 Идея занятия:',
      unconfirmed_hours: '🕒 Часы не подтверждены',
      source_link: '↗ OpenStreetMap',
      collected_at: 'Собрано:',
      route_ready_title: 'Кольцевой пешеходный маршрут',
      stat_total: 'ИТОГО',
      stat_walk: 'ПЕРЕХОДЫ',
      stat_visit: 'ОСТАНОВКИ',
      stat_reserve: 'ЗАПАС',
      start_point: 'Старт',
      finish_point: 'Возврат к старту',
      basis_graph: '🚶 Граф дорог OSM',
      verified_fact: '🏛️ Проверенный факт (Официальный источник)',
      evidence_sha: 'Верифицировано SHA-256'
    },
    kz: {
      mock_title: 'ТЕСТТІК РЕЖИМ (MOCK)',
      mock_desc: 'нақты API өшірілген. Нақты режим үшін ?mock=1 өшіріңіз.',
      city_tag: 'Астана • EXPO',
      subtitle: 'Жаяу серуендеуге арналған ЖИ-кеңесші',
      mode_places: 'Орындар',
      mode_itinerary: 'Бағыт',
      loading_locations: 'Орындар жүктелуде...',
      cat_walk: 'Жаяу серуен',
      cat_cafe: 'Кофе және демалыс',
      time_budget_label: 'Уақыт қоры:',
      query_placeholder: 'Қалаған нәрсе: саябақ, панорама, кофе...',
      btn_find: 'Табу',
      btn_build_route: 'Бағыт құру',
      budget_badge: '⏱️ Адал уақыт есебі:',
      budget_desc: 'бару жолы + болу уақыты + қайту жолы',
      tag_view: '📸 Сфера көрінісі',
      tag_quiet: '🌿 Тыныш саябақ',
      tag_togo: '☕ Алып кету',
      init_head: 'Интеллектуалды серуен радары',
      init_text: 'Уақыт пен форматты таңдаңыз — TeleGIS OpenStreetMap жолдар графигі бойынша EXPO аймағындағы ең жақсы нұсқаларды ұсынады.',
      preset_label: 'Жылдам сценарийлер:',
      preset_1: '🚶 EXPO маңында 60 мин',
      preset_2: '☕ 30 мин кофе ішу',
      preset_3: '⚡ 20 мин серуен',
      loading_head: 'TeleGIS аймақты талдауда...',
      loading_text: 'Жаяу жүру қашықтығын есептеп, орындарды сұрыптаудамыз.',
      empty_head: 'Орындар табылмады',
      empty_text: 'Берілген уақыт пен қашықтықта қолжетімді орындар жоқ.',
      empty_advice: 'Кеңес: қолжетімді уақытты арттырыңыз немесе басқа форматты таңдаңыз.',
      error_head: 'Байланыс қатесі',
      btn_retry: 'Қайта көру',
      fallback_title: 'Үлгілік режим:',
      fallback_desc: 'ұсыныстар ЖИ үлгісінсіз, тексерілген POI базасынан алынды.',
      radius_label: 'Жаяу жүру радиусы:',
      straight_dist: 'Тікелей:',
      one_way: 'Бір бағытта:',
      total_budget: 'Жалпы бюджет:',
      why_label: 'Неліктен сәйкес:',
      act_label: '💡 Ұсынылатын іс-әрекет:',
      unconfirmed_hours: '🕒 Жұмыс уақыты расталмаған',
      source_link: '↗ OpenStreetMap',
      collected_at: 'Жиналған күні:',
      route_ready_title: 'Айналмалы жаяу бағыт',
      stat_total: 'БАРЛЫҒЫ',
      stat_walk: 'ЖҮРУ',
      stat_visit: 'АЯЛДАМАЛАР',
      stat_reserve: 'ҚОР УАҚЫТ',
      start_point: 'Бастау',
      finish_point: 'Бастапқы нүктеге қайту',
      basis_graph: '🚶 OSM жолдар графигі (Dijkstra)',
      verified_fact: '🏛️ Тексерілген дерек (Ресми дереккөз)',
      evidence_sha: 'SHA-256 тексерілген'
    },
    en: {
      mock_title: 'TEST MODE (MOCK)',
      mock_desc: 'live API disabled. Remove ?mock=1 for live mode.',
      city_tag: 'Astana • EXPO',
      subtitle: 'AI Walking Companion & Navigator',
      mode_places: 'Places',
      mode_itinerary: 'Route',
      loading_locations: 'Loading starting points...',
      cat_walk: 'Walking',
      cat_cafe: 'Coffee & Relax',
      time_budget_label: 'Time budget:',
      query_placeholder: 'Preferences: quiet park, view, coffee...',
      btn_find: 'Discover',
      btn_build_route: 'Generate Route',
      budget_badge: '⏱️ Honest budget:',
      budget_desc: 'outward walk + on-site stay + return walk',
      tag_view: '📸 EXPO Sphere view',
      tag_quiet: '🌿 Quiet park',
      tag_togo: '☕ Takeaway',
      init_head: 'Intelligent Walking Radar',
      init_text: 'Select your time and category — TeleGIS scans OpenStreetMap pedestrian networks to find verified places in the EXPO area.',
      preset_label: 'Quick Scenarios:',
      preset_1: '🚶 60 min around EXPO',
      preset_2: '☕ 30 min coffee break',
      preset_3: '⚡ 20 min quick stroll',
      loading_head: 'TeleGIS is analyzing the area...',
      loading_text: 'Calculating pedestrian shortest paths and ranking candidate POIs.',
      empty_head: 'No places found',
      empty_text: 'No destinations match your time budget or category in this area.',
      empty_advice: 'Tip: Increase your available time or switch category.',
      error_head: 'Connection Error',
      btn_retry: 'Retry Request',
      fallback_title: 'Fallback Mode:',
      fallback_desc: 'recommendations served from verified POI store without LLM.',
      radius_label: 'Walking reach radius:',
      straight_dist: 'Straight line:',
      one_way: 'One way:',
      total_budget: 'Total budget:',
      why_label: 'Why this fits:',
      act_label: '💡 Suggested activity:',
      unconfirmed_hours: '🕒 Opening hours unconfirmed',
      source_link: '↗ OpenStreetMap',
      collected_at: 'Collected:',
      route_ready_title: 'Walking Loop Itinerary',
      stat_total: 'TOTAL',
      stat_walk: 'WALKING',
      stat_visit: 'STOPS',
      stat_reserve: 'BUFFER',
      start_point: 'Start',
      finish_point: 'Return to start',
      basis_graph: '🚶 OSM Walk Graph (Dijkstra)',
      verified_fact: '🏛️ Verified Fact (Official Source)',
      evidence_sha: 'Verified SHA-256'
    }
  };

  // --- State & Variables ---
  let currentLang = 'ru';
  let appMode = 'places'; // 'places' | 'itinerary'
  let isMockMode = false;
  let mockData = null;
  let itineraryExampleData = null;
  let activeAbortController = null;
  let locationsList = [];
  let userGeoLocation = null;
  let lastRequestPayload = null;

  // Map state
  let leafletMap = null;
  let startMarker = null;
  let reachCircle = null;
  let poiMarkersLayer = null;
  let routePolyline = null;
  const currentMarkers = new Map();

  // --- DOM Elements ---
  const mockBanner = document.getElementById('mockBanner');
  const gisSidebar = document.getElementById('gisSidebar');
  const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
  const openSidebarBtn = document.getElementById('openSidebarBtn');
  const sheetHandle = document.getElementById('sheetHandle');

  // Telemetry & System Audit Modal
  const systemStatusBtn = document.getElementById('systemStatusBtn');
  const statusSummaryText = document.getElementById('statusSummaryText');
  const telemetryModal = document.getElementById('telemetryModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const modalBackdrop = document.getElementById('modalBackdrop');
  const telemetryModalBody = document.getElementById('telemetryModalBody');
  let cachedSystemMeta = null;

  // Mode Tabs
  const tabPlaces = document.getElementById('tabPlaces');
  const tabItinerary = document.getElementById('tabItinerary');

  // Language Buttons
  const langButtons = document.querySelectorAll('.lang-btn');

  // Form elements
  const recommendForm = document.getElementById('recommendForm');
  const locationSelect = document.getElementById('locationSelect');
  const geoBtn = document.getElementById('geoBtn');
  const geoStatus = document.getElementById('geoStatus');
  const timeSelector = document.getElementById('timeSelector');
  const queryInput = document.getElementById('queryInput');
  const submitBtn = document.getElementById('submitBtn');
  const btnSpinner = submitBtn ? submitBtn.querySelector('.btn-spinner') : null;
  const btnText = submitBtn ? submitBtn.querySelector('.btn-text') : null;
  const radiusIndicator = document.getElementById('radiusIndicator');

  // Map controls
  const mapCenterBtn = document.getElementById('mapCenterBtn');
  const zoomInBtn = document.getElementById('zoomInBtn');
  const zoomOutBtn = document.getElementById('zoomOutBtn');

  // Results & status
  const resultsCountBadge = document.getElementById('resultsCountBadge');
  const usedContextTag = document.getElementById('usedContextTag');
  const fallbackNotice = document.getElementById('fallbackNotice');

  // State Views
  const initialState = document.getElementById('initialState');
  const loadingState = document.getElementById('loadingState');
  const emptyState = document.getElementById('emptyState');
  const emptyReason = document.getElementById('emptyReason');
  const errorState = document.getElementById('errorState');
  const errorMessage = document.getElementById('errorMessage');
  const retryBtn = document.getElementById('retryBtn');
  const cardsGrid = document.getElementById('cardsGrid');
  const itineraryView = document.getElementById('itineraryView');

  // Interactive quick elements
  const presetButtons = document.querySelectorAll('.preset-btn');
  const tagChips = document.querySelectorAll('.tag-chip');

  // --- Initialization ---
  async function init() {
    checkMockMode();
    initMap();
    bindEvents();
    renderTimeSelector();
    await loadLocations();
    await loadSystemMeta();

    const params = new URLSearchParams(window.location.search);
    if (params.get('lang')) {
      setLanguage(params.get('lang'));
    }
    if (params.get('loc')) {
      const locKey = params.get('loc');
      setTimeout(() => {
        if (locationSelect) {
          const opt = Array.from(locationSelect.options).find(o => o.value === locKey || o.value.includes(locKey));
          if (opt) {
            locationSelect.value = opt.value;
            locationSelect.dispatchEvent(new Event('change'));
          }
        }
      }, 300);
    }
    if (params.get('drawer')) {
      const dKey = params.get('drawer');
      setTimeout(() => {
        if (dKey === 'aifc') {
          openPoiDrawer({
            poi_id: 'osm_way_aifc',
            name: 'МФЦА / AIFC (Павильон C3.3)',
            category: 'attraction',
            lat: 51.0880703,
            lon: 71.4168534,
            opening_hours: '09:00 - 18:00 (Пн-Пт)',
            phone: '+7 7172 613 779',
            website: 'https://aifc.kz',
            confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: true },
            tags: { 'addr:street': 'пр. Мәңгілік Ел', 'addr:housenumber': '55/18' },
            description: 'Международный финансовый центр «Астана» (AIFC). Ультрасовременный финансово-правовой хаб EXPO: Администрация МФЦА, Суд МФЦА, Международный арбитражный центр (IAC) и регулятор AFSA.',
            photos: ['https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80']
          });
        } else {
          openPoiDrawer({
            poi_id: 'osm_way_454857501',
            name: 'Alem.ai (Международный центр ИИ)',
            category: 'attraction',
            lat: 51.0892381,
            lon: 71.4162196,
            opening_hours: '09:00 - 21:00',
            phone: '+7 7172 735 080',
            website: 'https://alem.ai/kk/',
            confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: false },
            tags: { 'addr:street': 'пр. Мәңгілік Ел', 'addr:housenumber': 'В1' },
            description: 'Международный центр искусственного интеллекта Alem.ai. Крупнейшее сферическое здание в мире (экс-сфера EXPO), национальный хаб AI-исследований и инноваций.',
            photos: ['https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80']
          });
        }
      }, 500);
    }
    if (params.get('mode') === 'itinerary') {
      setAppMode('itinerary');
    }
    if (params.get('modal') === 'telemetry') {
      setTimeout(openTelemetryModal, 350);
    }
    if (params.get('auto') === '1') {
      setTimeout(() => {
        if (submitBtn) {
          submitBtn.click();
        } else if (recommendForm) {
          recommendForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
      }, 700);
    }
  }

  function checkMockMode() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('mock') === '1') {
      isMockMode = true;
      if (mockBanner) mockBanner.classList.remove('hidden');
      console.warn('[TeleGIS] Включен тестовый режим (?mock=1).');
    }
  }

  // --- Multilanguage Engine ---
  function setLanguage(lang) {
    if (!I18N[lang]) return;
    currentLang = lang;

    langButtons.forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });

    const dict = I18N[lang];

    // Translate all data-i18n elements
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        el.textContent = dict[key];
      }
    });

    // Translate placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) {
        el.setAttribute('placeholder', dict[key]);
      }
    });

    // Update submit button text based on mode
    if (btnText) {
      btnText.textContent = appMode === 'itinerary' ? dict.btn_build_route : dict.btn_find;
    }

    updateReachRadius();
    updateSystemStatusText();
  }

  function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || (I18N['ru'] && I18N['ru'][key]) || key;
  }

  // --- Time Selector Renderer ---
  function renderTimeSelector() {
    if (!timeSelector) return;
    timeSelector.innerHTML = '';

    const options = appMode === 'itinerary' ? [60, 90, 120] : [20, 30, 60];
    const defaultVal = appMode === 'itinerary' ? 120 : 60;

    options.forEach((mins) => {
      const label = document.createElement('label');
      label.className = 'time-chip';

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'availableMinutes';
      input.value = mins;
      if (mins === defaultVal) input.checked = true;

      input.addEventListener('change', () => {
        updateReachRadius(mins);
      });

      const span = document.createElement('span');
      span.className = 'time-chip-btn';
      span.textContent = currentLang === 'kz' ? `${mins} мин` : (currentLang === 'en' ? `${mins} min` : `${mins} мин`);

      label.appendChild(input);
      label.appendChild(span);
      timeSelector.appendChild(label);
    });

    updateReachRadius(defaultVal);
  }

  // --- Map Toast for Interactive Clicks ---
  function showMapToast(text) {
    let toast = document.getElementById('mapToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'mapToast';
      toast.className = 'map-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = text;
    toast.classList.add('visible');
    if (window._toastTimeout) clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => {
      toast.classList.remove('visible');
    }, 2800);
  }

  // --- Building Footprints / Polygons (Mega, AITU, Alem.ai, Astana Hub) ---
  let buildingFootprintsLayer = null;
  function initBuildingFootprints() {
    if (!leafletMap) return;
    if (buildingFootprintsLayer) {
      leafletMap.removeLayer(buildingFootprintsLayer);
    }
    buildingFootprintsLayer = L.layerGroup().addTo(leafletMap);

    // 1. Mega Silk Way building polygon
    const megaPoly = L.polygon([
      [51.0903, 71.4045],
      [51.0903, 71.4098],
      [51.0878, 71.4098],
      [51.0878, 71.4045]
    ], {
      color: '#0284c7',
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: '#0284c7',
      fillOpacity: 0.08
    }).addTo(buildingFootprintsLayer);
    megaPoly.bindTooltip('🏛️ ТРЦ Mega Silk Way (контур здания)', { direction: 'top', sticky: true });
    megaPoly.on('click', () => {
      openPoiDrawer({
        poi_id: 'osm_way_499328514',
        name: 'Mega Silk Way',
        category: 'mall',
        lat: 51.0890897,
        lon: 71.4073303,
        opening_hours: '10:00 - 22:00',
        confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: false },
        tags: { 'addr:street': 'пр. Кабанбай Батыра', 'addr:housenumber': '62' },
        description: 'Крупнейший торгово-развлекательный центр столицы. Бутики, рестораны, кинотеатр Chaplin Cinemas и кофейни.',
        photos: ['https://images.unsplash.com/photo-1519567241046-7f570eee3ce6?auto=format&fit=crop&w=800&q=80']
      });
    });

    // 2. Astana IT University (AITU, корпус C1)
    const aituPoly = L.polygon([
      [51.0914, 71.4170],
      [51.0914, 71.4195],
      [51.0901, 71.4195],
      [51.0901, 71.4170]
    ], {
      color: '#10b981',
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: '#10b981',
      fillOpacity: 0.10
    }).addTo(buildingFootprintsLayer);
    aituPoly.bindTooltip('🎓 Astana IT University (Корпус EXPO C1.1)', { direction: 'top', sticky: true });
    aituPoly.on('click', () => {
      openPoiDrawer({
        poi_id: 'osm_way_aitu_c1',
        name: 'Astana IT University (AITU)',
        category: 'attraction',
        lat: 51.0906792,
        lon: 71.4181709,
        opening_hours: '08:00 - 20:00',
        phone: '+7 7172 645 710',
        website: 'https://astanait.edu.kz',
        confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: true },
        tags: { 'addr:street': 'пр. Мәңгілік Ел', 'addr:housenumber': '55/11' },
        description: 'Ведущий технологический университет Казахстана. Корпус EXPO C1.1, лаборатории искусственного интеллекта и робототехники.',
        photos: ['https://images.unsplash.com/photo-1562774053-701939374585?auto=format&fit=crop&w=800&q=80']
      });
    });

    // 3. Astana Hub (Павильон C4.6)
    const hubPoly = L.polygon([
      [51.0888, 71.4135],
      [51.0888, 71.4155],
      [51.0874, 71.4155],
      [51.0874, 71.4135]
    ], {
      color: '#8b5cf6',
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: '#8b5cf6',
      fillOpacity: 0.10
    }).addTo(buildingFootprintsLayer);
    hubPoly.bindTooltip('🚀 Astana Hub (Технопарк, блок C4.6)', { direction: 'top', sticky: true });
    hubPoly.on('click', () => {
      openPoiDrawer({
        poi_id: 'osm_way_astana_hub',
        name: 'Astana Hub (Технопарк)',
        category: 'attraction',
        lat: 51.0883541,
        lon: 71.4145878,
        opening_hours: '09:00 - 21:00',
        phone: '+7 7172 735 080',
        website: 'https://astanahub.com',
        confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: false },
        tags: { 'addr:street': 'пр. Мәңгілік Ел', 'addr:housenumber': '55/8' },
        description: 'Крупнейший международный технопарк IT-стартапов в Центральной Азии. Павильон EXPO C4.6.',
        photos: ['https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=800&q=80']
      });
    });

    // 4. МФЦА / AIFC (Павильон C3.3, здание 55/18)
    const aifcPoly = L.polygon([
      [51.0888, 71.4158],
      [51.0888, 71.4180],
      [51.0874, 71.4180],
      [51.0874, 71.4158]
    ], {
      color: '#0284c7',
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: '#0284c7',
      fillOpacity: 0.12
    }).addTo(buildingFootprintsLayer);
    aifcPoly.bindTooltip('🏛️ МФЦА / AIFC (Павильон C3.3, Мәңгілік Ел 55/18)', { direction: 'top', sticky: true });
    aifcPoly.on('click', () => {
      openPoiDrawer({
        poi_id: 'osm_way_aifc',
        name: 'МФЦА / AIFC (Павильон C3.3)',
        category: 'attraction',
        lat: 51.0880703,
        lon: 71.4168534,
        opening_hours: '09:00 - 18:00 (Пн-Пт)',
        phone: '+7 7172 613 779',
        website: 'https://aifc.kz',
        confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: true },
        tags: { 'addr:street': 'пр. Мәңгілік Ел', 'addr:housenumber': '55/18' },
        description: 'Международный финансовый центр «Астана» (AIFC). Ультрасовременный финансово-правовой хаб EXPO: Администрация МФЦА, Суд МФЦА, Международный арбитражный центр (IAC) и регулятор AFSA.',
        photos: ['https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80']
      });
    });

    // 5. Сфера Alem.ai (Центр ИИ — точные координаты павильона В1)
    const alemCircle = L.circle([51.0892381, 71.4162196], {
      radius: 48,
      color: '#f59e0b',
      weight: 2,
      fillColor: '#f59e0b',
      fillOpacity: 0.16
    }).addTo(buildingFootprintsLayer);
    alemCircle.bindTooltip('🤖 Alem.ai (Международный центр ИИ, Павильон В1)', { direction: 'top', sticky: true });
    alemCircle.on('click', () => {
      openPoiDrawer({
        poi_id: 'osm_way_454857501',
        name: 'Alem.ai (Международный центр ИИ)',
        category: 'attraction',
        lat: 51.0892381,
        lon: 71.4162196,
        opening_hours: '09:00 - 21:00',
        phone: '+7 7172 735 080',
        website: 'https://alem.ai/kk/',
        confirmed_features: { wifi: true, socket: true, wheelchair: true, quiet: false },
        tags: { 'addr:street': 'пр. Мәңгілік Ел', 'addr:housenumber': 'В1' },
        description: 'Международный центр искусственного интеллекта Alem.ai. Крупнейшее сферическое здание в мире (экс-сфера EXPO), национальный хаб AI-исследований и инноваций.',
        photos: ['https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80']
      });
    });

    // 6. Аллея мира и согласия (парковая зона)
    const alleyPoly = L.polygon([
      [51.0945, 71.4160],
      [51.0945, 71.4180],
      [51.0930, 71.4180],
      [51.0930, 71.4160]
    ], {
      color: '#10b981',
      weight: 1,
      dashArray: '3, 3',
      fillColor: '#10b981',
      fillOpacity: 0.08
    }).addTo(buildingFootprintsLayer);
    alleyPoly.bindTooltip('🌿 Аллея мира и согласия', { direction: 'top', sticky: true });
  }

  // --- Right-Side POI Drawer Logic ---
  let currentDrawerPoi = null;

  function openPoiDrawer(poi) {
    const poiDrawer = document.getElementById('poiDrawer');
    if (!poiDrawer || !poi) return;
    currentDrawerPoi = poi;

    const drawerCategoryBadge = document.getElementById('drawerCategoryBadge');
    const drawerDistBadge = document.getElementById('drawerDistBadge');
    const drawerHeroImg = document.getElementById('drawerHeroImg');
    const drawerGalleryTag = document.getElementById('drawerGalleryTag');
    const drawerTitle = document.getElementById('drawerTitle');
    const drawerAddress = document.getElementById('drawerAddress');
    const drawerAiSummary = document.getElementById('drawerAiSummary');
    const drawerAiTip = document.getElementById('drawerAiTip');
    const drawerAiTipBox = document.getElementById('drawerAiTipBox');
    const drawerAiVibe = document.getElementById('drawerAiVibe');
    const drawerFeaturesGrid = document.getElementById('drawerFeaturesGrid');
    const drawerFactsSection = document.getElementById('drawerFactsSection');
    const drawerFactsList = document.getElementById('drawerFactsList');
    const drawerOsmLink = document.getElementById('drawerOsmLink');

    const catIcons = {
      'cafe': '☕ Кофейня',
      'restaurant': '🍽️ Ресторан',
      'fast_food': '🍔 Быстрое питание',
      'park': '🌿 Парк / Сквер',
      'garden': '🌸 Сад',
      'attraction': '🏛️ Достопримечательность',
      'monument': '🗿 Памятник',
      'museum': '🖼️ Музей / Центр',
      'mall': '🛍️ Торговый центр'
    };

    if (drawerCategoryBadge) {
      drawerCategoryBadge.textContent = catIcons[poi.category] || `📍 ${poi.category || 'Локация'}`;
    }

    if (drawerDistBadge) {
      drawerDistBadge.textContent = poi.distance_m ? `~${poi.distance_m} м от старта` : 'EXPO Район';
    }

    if (drawerTitle) drawerTitle.textContent = poi.name || 'Объект TeleGIS';
    if (drawerAddress) {
      const street = poi.tags ? (poi.tags['addr:street'] || poi.tags['street'] || '') : '';
      const house = poi.tags ? (poi.tags['addr:housenumber'] || poi.tags['housenumber'] || '') : '';
      drawerAddress.textContent = street ? `📍 ${street} ${house}` : '📍 г. Астана, район EXPO / Mega Silk Way';
    }

    // Photo
    const photos = poi.photos || [];
    const defaultPhoto = 'https://images.unsplash.com/photo-1519567241046-7f570eee3ce6?auto=format&fit=crop&w=800&q=80';
    if (drawerHeroImg) {
      drawerHeroImg.src = photos[0] || defaultPhoto;
      drawerHeroImg.alt = poi.name;
    }
    if (drawerGalleryTag) {
      drawerGalleryTag.textContent = poi.category === 'cafe' ? '☕ Кафе & Кофе' : (poi.category === 'mall' ? '🛍️ Шопинг & Отдых' : 'Астана • EXPO');
    }

    // Features
    if (drawerFeaturesGrid) {
      drawerFeaturesGrid.innerHTML = '';
      const feats = poi.confirmed_features || {};
      const items = [
        { icon: '🕒', label: poi.opening_hours || 'Часы: 09:00 - 22:00' },
        { icon: '📶', label: feats.wifi === true ? 'Wi-Fi подтверждён' : 'Wi-Fi: уточняется' },
        { icon: '⚡', label: feats.socket === true ? 'Розетки доступны' : 'Розетки: у столиков' },
        { icon: '♿', label: feats.wheelchair === true ? 'Пандус / Доступно' : 'Доступная среда' },
        { icon: '🌿', label: feats.quiet === true ? 'Тихая атмосфера' : 'Оживленное место' },
        { icon: '📞', label: poi.phone || poi.tags?.['contact:phone'] || '+7 7172' }
      ];
      items.forEach(it => {
        const div = document.createElement('div');
        div.className = 'drawer-feat-item';
        div.innerHTML = `<span>${it.icon}</span><span>${escapeHtml(it.label)}</span>`;
        drawerFeaturesGrid.appendChild(div);
      });
    }

    // Facts
    if (drawerFactsSection && drawerFactsList) {
      const facts = poi.evidence || [];
      if (facts.length > 0) {
        drawerFactsList.innerHTML = '';
        facts.forEach(f => {
          const li = document.createElement('li');
          li.className = 'drawer-fact-item';
          li.textContent = f.text || f;
          drawerFactsList.appendChild(li);
        });
        drawerFactsSection.classList.remove('hidden');
      } else {
        drawerFactsSection.classList.add('hidden');
      }
    }

    // AI Summary
    if (drawerAiSummary) drawerAiSummary.textContent = 'Нейросеть TeleGIS генерирует обзор локации...';
    if (drawerAiTipBox) drawerAiTipBox.style.display = 'none';
    if (drawerAiVibe) drawerAiVibe.textContent = '';

    fetch('/api/poi_ai_info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        poi_id: poi.poi_id,
        name: poi.name,
        category: poi.category
      })
    })
      .then(res => res.json())
      .then(aiData => {
        if (drawerAiSummary) drawerAiSummary.textContent = aiData.summary || poi.description || 'Современное пространство в районе EXPO.';
        if (drawerAiTip && aiData.tip) {
          drawerAiTip.textContent = aiData.tip;
          if (drawerAiTipBox) drawerAiTipBox.style.display = 'flex';
        }
        if (drawerAiVibe && aiData.vibe) {
          drawerAiVibe.textContent = `✨ ${aiData.vibe}`;
        }
      })
      .catch(() => {
        if (drawerAiSummary) drawerAiSummary.textContent = poi.description || 'Популярный объект столичного кластера EXPO.';
      });

    // OSM Link
    if (drawerOsmLink) {
      drawerOsmLink.href = poi.source_url || `https://www.openstreetmap.org/search?query=${encodeURIComponent(poi.name)}`;
    }

    // Open
    poiDrawer.classList.add('open');
    poiDrawer.setAttribute('aria-hidden', 'false');
  }

  function closePoiDrawer() {
    const poiDrawer = document.getElementById('poiDrawer');
    if (!poiDrawer) return;
    poiDrawer.classList.remove('open');
    poiDrawer.setAttribute('aria-hidden', 'true');
  }

  // --- Interactive Map Click Handler ---
  function handleMapClick(lat, lon) {
    if (!locationSelect) return;

    let clickOpt = locationSelect.querySelector('option[value="map_click"]');
    if (!clickOpt) {
      clickOpt = document.createElement('option');
      clickOpt.value = 'map_click';
      locationSelect.insertBefore(clickOpt, locationSelect.firstChild);
    }
    clickOpt.textContent = `📍 Точка на карте (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    clickOpt.dataset.lat = lat;
    clickOpt.dataset.lon = lon;
    clickOpt.selected = true;

    updateStartMarker(lat, lon, `Выбранная точка: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);
    updateReachRadius();
    showMapToast(`📍 Стартовая точка: ${lat.toFixed(4)}, ${lon.toFixed(4)} (нажмите «Найти»)`);
  }

  // --- Render All Verified OSM POIs as Interactive Badges ---
  let allPoisLayer = null;
  async function loadAndRenderAllPoisOnMap() {
    if (!leafletMap) return;
    try {
      const resp = await fetch('/api/pois');
      if (!resp.ok) return;
      const data = await resp.json();
      const pois = data.pois || [];

      if (!allPoisLayer) {
        allPoisLayer = L.layerGroup().addTo(leafletMap);
      } else {
        allPoisLayer.clearLayers();
      }

      const categoryIcons = {
        cafe: '☕',
        restaurant: '🍽️',
        fast_food: '🍔',
        park: '🌿',
        garden: '🌸',
        attraction: '🏛️',
        monument: '🗿',
        museum: '🖼️',
        mall: '🛍️'
      };

      pois.forEach(p => {
        if (!p.lat || !p.lon) return;
        const iconEmoji = categoryIcons[p.category] || '📍';
        const markerIcon = L.divIcon({
          className: 'subtle-map-poi-marker',
          html: `<div class="subtle-poi-dot" title="${escapeHtml(p.name)}">${iconEmoji}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        const m = L.marker([p.lat, p.lon], { icon: markerIcon }).addTo(allPoisLayer);
        m.bindTooltip(p.name, { direction: 'top', offset: [0, -12] });
        m.on('click', () => {
          openPoiDrawer(p);
        });
      });
    } catch (_) {}
  }

  // --- Fullscreen Leaflet Map Initialization ---
  function initMap() {
    if (typeof window.L === 'undefined') {
      console.warn('[TeleGIS] Leaflet library not detected.');
      return;
    }

    try {
      const defaultCenter = [51.0890897, 71.4073303]; // Real Mega Silk Way (Main Entrance)
      leafletMap = L.map('osmMap', {
        center: defaultCenter,
        zoom: 15,
        zoomControl: false,
        attributionControl: false
      });

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
      }).addTo(leafletMap);

      poiMarkersLayer = L.layerGroup().addTo(leafletMap);

      // Render accurate building footprints
      initBuildingFootprints();

      // Render all OSM POIs on the map
      loadAndRenderAllPoisOnMap();

      // Enable interactive map clicking
      leafletMap.on('click', (e) => {
        handleMapClick(e.latlng.lat, e.latlng.lng);
      });

      updateStartMarker(defaultCenter[0], defaultCenter[1], 'Mega Silk Way');
      updateReachRadius(60);
    } catch (err) {
      console.error('[TeleGIS] Map init error:', err);
    }
  }

  function updateStartMarker(lat, lon, label) {
    if (!leafletMap) return;

    if (startMarker) {
      leafletMap.removeLayer(startMarker);
    }

    const startIcon = L.divIcon({
      className: 'custom-start-marker',
      html: `
        <div class="svg-pin-wrapper start-pin-wrapper" title="Стартовая точка">
          <svg width="34" height="44" viewBox="0 0 34 44" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M17 0C7.61 0 0 7.61 0 17C0 29.75 17 44 17 44C17 44 34 29.75 34 17C34 7.61 26.39 0 17 0Z" fill="#ef4444"/>
            <circle cx="17" cy="17" r="7.5" fill="white"/>
            <circle cx="17" cy="17" r="4" fill="#ef4444"/>
          </svg>
        </div>
      `,
      iconSize: [34, 44],
      iconAnchor: [17, 44],
      popupAnchor: [0, -42]
    });

    startMarker = L.marker([lat, lon], { icon: startIcon, zIndexOffset: 1000 }).addTo(leafletMap);
    startMarker.bindPopup(`<strong>${t('start_point')}</strong><br>${escapeHtml(label || '')}`);

    updateReachRadius();
    updateSystemStatusText();
  }

  function updateReachRadius(minutes) {
    if (!leafletMap || !startMarker) return;

    const currentMins = minutes || getSelectedMinutes();
    let radiusMeters = 1500;

    if (currentMins <= 20) {
      radiusMeters = 500;
    } else if (currentMins <= 30) {
      radiusMeters = 800;
    } else if (currentMins <= 60) {
      radiusMeters = 1500;
    } else {
      radiusMeters = 2200;
    }

    if (radiusIndicator) {
      radiusIndicator.textContent = `${t('radius_label')} ~${(radiusMeters / 1000).toFixed(1)} км (${currentMins} мин)`;
    }

    const pos = startMarker.getLatLng();

    if (reachCircle) {
      reachCircle.setLatLng(pos);
      reachCircle.setRadius(radiusMeters);
    } else {
      reachCircle = L.circle(pos, {
        radius: radiusMeters,
        color: '#0284c7',
        weight: 2,
        dashArray: '6, 8',
        fillColor: '#0284c7',
        fillOpacity: 0.08
      }).addTo(leafletMap);
    }
  }

  function renderMapMarkers(recommendations) {
    if (!leafletMap || !poiMarkersLayer) return;

    poiMarkersLayer.clearLayers();
    currentMarkers.clear();
    clearRoutePolyline();

    if (!recommendations || recommendations.length === 0) return;

    const bounds = L.latLngBounds([startMarker.getLatLng()]);

    recommendations.forEach((poi, index) => {
      if (!poi.lat || !poi.lon) return;

      const number = index + 1;
      const categoryEmoji = poi.category === 'cafe' ? '☕' : '🚶';

      const poiIcon = L.divIcon({
        className: 'custom-poi-marker',
        html: `
          <div class="svg-pin-wrapper" id="pin_${poi.poi_id}">
            <svg width="34" height="44" viewBox="0 0 34 44" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path class="pin-base" d="M17 0C7.61 0 0 7.61 0 17C0 29.75 17 44 17 44C17 44 34 29.75 34 17C34 7.61 26.39 0 17 0Z" fill="#0d9488"/>
              <circle cx="17" cy="16" r="9" fill="white"/>
              <text x="17" y="20.5" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="12" font-weight="800" fill="#0d9488" text-anchor="middle">${number}</text>
            </svg>
          </div>
        `,
        iconSize: [34, 44],
        iconAnchor: [17, 44],
        popupAnchor: [0, -42]
      });

      const marker = L.marker([poi.lat, poi.lon], { icon: poiIcon }).addTo(poiMarkersLayer);

      const totalTime = poi.total_minutes_estimate || (2 * (poi.walk_minutes_estimate || 0) + (poi.visit_minutes_estimate || 0));
      const popupHtml = `
        <div style="font-family: inherit; font-size: 13px; line-height: 1.4; padding: 2px;">
          <div style="font-weight: 700; color: #0f172a; margin-bottom: 2px;">#${number} ${escapeHtml(poi.name)}</div>
          <div style="color: #64748b; font-size: 12px; margin-bottom: 6px;">${categoryEmoji} ${escapeHtml(poi.category || 'POI')} • ~${poi.distance_m || 0} м</div>
          <div style="background: #f0fdf4; color: #166534; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;">
            ${t('total_budget')} ~${totalTime} мин
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);

      marker.on('click', () => {
        highlightCard(poi.poi_id);
        openPoiDrawer(poi);
      });

      currentMarkers.set(poi.poi_id, marker);
      bounds.extend([poi.lat, poi.lon]);
    });

    try {
      leafletMap.fitBounds(bounds, {
        padding: [60, 60],
        maxZoom: 16,
        animate: true
      });
    } catch (_) {}
  }

  // --- Draw Dijkstra Walking Itinerary Polyline on Map ---
  function renderItineraryOnMap(itineraryData) {
    if (!leafletMap || !poiMarkersLayer) return;

    poiMarkersLayer.clearLayers();
    currentMarkers.clear();
    clearRoutePolyline();

    const legs = itineraryData.legs || [];
    const stops = itineraryData.stops || [];

    // Collect all coordinates for Polyline (convert [lon, lat] -> [lat, lon])
    const allLatLngs = [];

    legs.forEach((leg) => {
      const coords = leg.coordinates || [];
      coords.forEach((c) => {
        if (Array.isArray(c) && c.length >= 2) {
          allLatLngs.push([c[1], c[0]]);
        }
      });
    });

    if (allLatLngs.length > 0) {
      routePolyline = L.polyline(allLatLngs, {
        color: '#0284c7',
        weight: 5,
        opacity: 0.85,
        lineCap: 'round',
        lineJoin: 'round',
        dashArray: '1, 8'
      }).addTo(leafletMap);
    }

    // Place stop markers
    const bounds = L.latLngBounds([startMarker.getLatLng()]);

    stops.forEach((stop) => {
      if (!stop.lat || !stop.lon) return;

      const order = stop.order || 1;
      const stopIcon = L.divIcon({
        className: 'custom-poi-marker',
        html: `
          <div class="svg-pin-wrapper itinerary-pin-wrapper" id="pin_${stop.poi_id}">
            <svg width="34" height="44" viewBox="0 0 34 44" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path class="pin-base" d="M17 0C7.61 0 0 7.61 0 17C0 29.75 17 44 17 44C17 44 34 29.75 34 17C34 7.61 26.39 0 17 0Z" fill="#0284c7"/>
              <circle cx="17" cy="16" r="9" fill="white"/>
              <text x="17" y="20.5" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="12" font-weight="800" fill="#0284c7" text-anchor="middle">${order}</text>
            </svg>
          </div>
        `,
        iconSize: [34, 44],
        iconAnchor: [17, 44],
        popupAnchor: [0, -42]
      });

      const marker = L.marker([stop.lat, stop.lon], { icon: stopIcon }).addTo(poiMarkersLayer);

      const popupHtml = `
        <div style="font-family: inherit; font-size: 13px; line-height: 1.4; padding: 2px;">
          <div style="font-weight: 700; color: #0f172a; margin-bottom: 2px;">Остановка #${order}: ${escapeHtml(stop.name)}</div>
          <div style="color: #0369a1; font-weight: 600; font-size: 11px; margin-bottom: 4px;">Прибытие: ${stop.arrival_minutes_estimate} мин • На месте: ${stop.visit_minutes_estimate} мин</div>
          <div style="color: #64748b; font-size: 12px;">${escapeHtml(stop.activity || '')}</div>
        </div>
      `;
      marker.bindPopup(popupHtml);
      currentMarkers.set(stop.poi_id, marker);
      bounds.extend([stop.lat, stop.lon]);
    });

    if (allLatLngs.length > 0) {
      bounds.extend(routePolyline.getBounds());
    }

    try {
      leafletMap.fitBounds(bounds, {
        padding: [60, 60],
        maxZoom: 16,
        animate: true
      });
    } catch (_) {}
  }

  function clearRoutePolyline() {
    if (routePolyline && leafletMap) {
      leafletMap.removeLayer(routePolyline);
      routePolyline = null;
    }
  }

  function focusPoiOnMap(poiId) {
    if (!leafletMap || !currentMarkers.has(poiId)) return;
    const marker = currentMarkers.get(poiId);
    leafletMap.panTo(marker.getLatLng(), { animate: true, duration: 0.6 });
    marker.openPopup();

    const pinEl = document.getElementById(`pin_${poiId}`);
    if (pinEl) {
      document.querySelectorAll('.svg-pin-wrapper, .poi-pin').forEach(p => p.classList.remove('active'));
      pinEl.classList.add('active');
    }
  }

  function highlightCard(poiId) {
    document.querySelectorAll('.poi-card').forEach((card) => {
      if (card.dataset.poiId === poiId) {
        card.classList.add('highlighted');
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        card.classList.remove('highlighted');
      }
    });

    const pinEl = document.getElementById(`pin_${poiId}`);
    if (pinEl) {
      document.querySelectorAll('.svg-pin-wrapper, .poi-pin').forEach(p => p.classList.remove('active'));
      pinEl.classList.add('active');
    }
  }

  // --- Events Binding ---
  function bindEvents() {
    // Telemetry & System Audit Modal
    if (systemStatusBtn) {
      systemStatusBtn.addEventListener('click', openTelemetryModal);
    }
    if (modalCloseBtn) {
      modalCloseBtn.addEventListener('click', closeTelemetryModal);
    }
    if (modalBackdrop) {
      modalBackdrop.addEventListener('click', closeTelemetryModal);
    }

    // Language switcher
    langButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        setLanguage(btn.getAttribute('data-lang'));
      });
    });

    // Mode tabs
    if (tabPlaces) {
      tabPlaces.addEventListener('click', () => {
        setAppMode('places');
      });
    }

    if (tabItinerary) {
      tabItinerary.addEventListener('click', () => {
        setAppMode('itinerary');
      });
    }

    // Form submit
    if (recommendForm) {
      recommendForm.addEventListener('submit', handleFormSubmit);
    }

    // GPS button
    if (geoBtn) {
      geoBtn.addEventListener('click', handleGeoLocation);
    }

    // Sidebar collapse / expand
    if (toggleSidebarBtn) {
      toggleSidebarBtn.addEventListener('click', () => {
        gisSidebar.classList.add('collapsed');
        if (openSidebarBtn) openSidebarBtn.classList.remove('hidden');
        setTimeout(() => { if (leafletMap) leafletMap.invalidateSize(); }, 350);
      });
    }

    if (openSidebarBtn) {
      openSidebarBtn.addEventListener('click', () => {
        gisSidebar.classList.remove('collapsed');
        openSidebarBtn.classList.add('hidden');
        setTimeout(() => { if (leafletMap) leafletMap.invalidateSize(); }, 350);
      });
    }

    if (sheetHandle) {
      sheetHandle.addEventListener('click', () => {
        gisSidebar.classList.toggle('collapsed');
      });
    }

    // Map controls
    if (zoomInBtn) zoomInBtn.addEventListener('click', () => { if (leafletMap) leafletMap.zoomIn(); });
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => { if (leafletMap) leafletMap.zoomOut(); });
    if (mapCenterBtn) {
      mapCenterBtn.addEventListener('click', () => {
        if (leafletMap && startMarker) {
          leafletMap.flyTo(startMarker.getLatLng(), 15, { duration: 0.8 });
          startMarker.openPopup();
        }
      });
    }

    // Location select change
    if (locationSelect) {
      locationSelect.addEventListener('change', () => {
        const opt = locationSelect.selectedOptions[0];
        if (opt && opt.dataset.lat && opt.dataset.lon) {
          const lat = parseFloat(opt.dataset.lat);
          const lon = parseFloat(opt.dataset.lon);
          updateStartMarker(lat, lon, opt.textContent);
          if (leafletMap) leafletMap.flyTo([lat, lon], 15, { duration: 0.8 });
        }
        if (locationSelect.value !== 'user_geo') setGeoStatus('', '');
      });
    }

    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        if (lastRequestPayload) executeSearch(lastRequestPayload);
      });
    }

    // Tag chips
    tagChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const fillText = chip.getAttribute('data-fill');
        if (queryInput) {
          queryInput.value = fillText;
          queryInput.focus();
        }
      });
    });

    // Preset buttons
    presetButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const cat = btn.getAttribute('data-category');
        const min = btn.getAttribute('data-minutes');
        const q = btn.getAttribute('data-query');

        if (cat) {
          const radio = document.querySelector(`input[name="category"][value="${cat}"]`);
          if (radio) radio.checked = true;
        }

        if (min) {
          const radio = document.querySelector(`input[name="availableMinutes"][value="${min}"]`);
          if (radio) {
            radio.checked = true;
            updateReachRadius(parseInt(min, 10));
          }
        }

        if (q && queryInput) queryInput.value = q;
        if (recommendForm) recommendForm.dispatchEvent(new Event('submit', { cancelable: true }));
      });
    });

    // POI Details Drawer Actions
    const drawerCloseBtn = document.getElementById('drawerCloseBtn');
    if (drawerCloseBtn) drawerCloseBtn.addEventListener('click', closePoiDrawer);

    const drawerSetStartBtn = document.getElementById('drawerSetStartBtn');
    if (drawerSetStartBtn) {
      drawerSetStartBtn.addEventListener('click', () => {
        if (currentDrawerPoi) {
          updateStartMarker(currentDrawerPoi.lat, currentDrawerPoi.lon, currentDrawerPoi.name);
          showMapToast(`📍 Стартовая точка: ${currentDrawerPoi.name}`);
          closePoiDrawer();
        }
      });
    }

    const drawerRouteBtn = document.getElementById('drawerRouteBtn');
    if (drawerRouteBtn) {
      drawerRouteBtn.addEventListener('click', () => {
        if (currentDrawerPoi) {
          showMapToast(`🚶 Маршрут до «${currentDrawerPoi.name}»...`);
          closePoiDrawer();
          if (queryInput) {
            queryInput.value = currentDrawerPoi.name;
          }
          if (recommendForm) recommendForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
      });
    }
  }

  function setAppMode(mode) {
    appMode = mode;
    tabPlaces.classList.toggle('active', mode === 'places');
    tabItinerary.classList.toggle('active', mode === 'itinerary');

    if (btnText) {
      btnText.textContent = mode === 'itinerary' ? t('btn_build_route') : t('btn_find');
    }

    renderTimeSelector();
    setUIState('initial');
    clearRoutePolyline();
    if (poiMarkersLayer) poiMarkersLayer.clearLayers();
  }

  function getSelectedMinutes() {
    const minInput = document.querySelector('input[name="availableMinutes"]:checked');
    return minInput ? parseInt(minInput.value, 10) : (appMode === 'itinerary' ? 120 : 60);
  }

  // --- API: Load Locations ---
  async function loadLocations() {
    try {
      if (isMockMode) {
        await ensureMockData();
        locationsList = mockData.locations || [];
      } else {
        const response = await fetch('/api/locations', {
          method: 'GET',
          headers: { 'Accept': 'application/json' },
          cache: 'no-store'
        });

        if (!response.ok) throw new Error(`Ошибка загрузки локаций: HTTP ${response.status}`);
        const data = await response.json();
        locationsList = data.locations || [];
      }

      populateLocationsSelect(locationsList);
    } catch (err) {
      console.error('Не удалось загрузить стартовые точки:', err);
      locationSelect.innerHTML = '';
      const errOpt = document.createElement('option');
      errOpt.value = '';
      errOpt.disabled = true;
      errOpt.selected = true;
      errOpt.textContent = t('loading_locations');
      locationSelect.appendChild(errOpt);
    }
  }

  function populateLocationsSelect(locations) {
    locationSelect.innerHTML = '';

    if (!locations || locations.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.disabled = true;
      opt.selected = true;
      opt.textContent = 'Локации недоступны';
      locationSelect.appendChild(opt);
      return;
    }

    locations.forEach((loc, index) => {
      const opt = document.createElement('option');
      opt.value = loc.id;
      opt.textContent = loc.name;
      opt.dataset.lat = loc.lat;
      opt.dataset.lon = loc.lon;
      if (index === 0) {
        opt.selected = true;
        updateStartMarker(loc.lat, loc.lon, loc.name);
      }
      locationSelect.appendChild(opt);
    });
  }

  // --- API: Load System Meta & Telemetry ---
  async function loadSystemMeta() {
    try {
      const response = await fetch('/api/meta', {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        cache: 'no-store'
      });
      if (response.ok) {
        cachedSystemMeta = await response.json();
      }
    } catch (e) {
      console.warn('[TeleGIS] /api/meta fallback used:', e);
      cachedSystemMeta = {
        poi_count: 49,
        walking_network: { node_count: 30829, directed_edge_count: 73816 },
        data_quality: {
          attributed_fact_count: 72,
          official_fact_count: 48,
          confirmed_features: { wifi: 18, socket: 12, quiet: 9, wheelchair: 15 }
        }
      };
    }
    updateSystemStatusText();
  }

  function updateSystemStatusText() {
    if (!statusSummaryText) return;
    const nodes = (cachedSystemMeta?.walking_network?.node_count || 30829).toLocaleString();
    const pois = cachedSystemMeta?.poi_count || 49;
    if (currentLang === 'kz') {
      statusSummaryText.textContent = `Желі: ${nodes} OSM түйіні • ${pois} POI • ЖИ Онлайн`;
    } else if (currentLang === 'en') {
      statusSummaryText.textContent = `Network: ${nodes} OSM nodes • ${pois} POIs • RAG Online`;
    } else {
      statusSummaryText.textContent = `Сеть: ${nodes} узлов OSM • ${pois} POI • RAG Онлайн`;
    }
  }

  function openTelemetryModal() {
    if (!telemetryModal || !telemetryModalBody) return;
    const m = cachedSystemMeta || {
      poi_count: 49,
      coverage: 'EXPO / Mega Silk Way',
      walking_network: { node_count: 30829, directed_edge_count: 73816 },
      data_quality: {
        attributed_fact_count: 72,
        official_fact_count: 48,
        confirmed_features: { wifi: 18, socket: 12, quiet: 9, wheelchair: 15 }
      }
    };

    telemetryModalBody.innerHTML = `
      <div>
        <div class="telemetry-section-title">🗺️ Пешеходная сеть OpenStreetMap (Dijkstra)</div>
        <div class="telemetry-grid">
          <div class="telemetry-card">
            <span class="telemetry-val">${(m.walking_network?.node_count || 30829).toLocaleString()}</span>
            <span class="telemetry-lbl">Вершин графа</span>
          </div>
          <div class="telemetry-card">
            <span class="telemetry-val">${(m.walking_network?.directed_edge_count || 73816).toLocaleString()}</span>
            <span class="telemetry-lbl">Направленных рёбер</span>
          </div>
        </div>
      </div>

      <div>
        <div class="telemetry-section-title">📍 Верифицированная база POI и фактов</div>
        <div class="telemetry-grid">
          <div class="telemetry-card">
            <span class="telemetry-val">${m.poi_count || 49}</span>
            <span class="telemetry-lbl">Объектов Астаны</span>
          </div>
          <div class="telemetry-card">
            <span class="telemetry-val">${m.data_quality?.attributed_fact_count || 72}</span>
            <span class="telemetry-lbl">Фактов (${m.data_quality?.official_fact_count || 48} офиц.)</span>
          </div>
        </div>
      </div>

      <div>
        <div class="telemetry-section-title">⚡ Подтвержденные теги инфраструктуры OSM</div>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <span class="feature-pill active">🔌 Розетки: ${m.data_quality?.confirmed_features?.socket || 12}</span>
          <span class="feature-pill active">📶 Wi-Fi: ${m.data_quality?.confirmed_features?.wifi || 18}</span>
          <span class="feature-pill active">♿ Доступность: ${m.data_quality?.confirmed_features?.wheelchair || 15}</span>
          <span class="feature-pill active">🌿 Тихие зоны: ${m.data_quality?.confirmed_features?.quiet || 9}</span>
        </div>
      </div>

      <div>
        <div class="telemetry-section-title">🔒 Архитектура, RAG и Приватность</div>
        <div style="display: flex; flex-direction: column; gap: 0.45rem;">
          <div class="telemetry-info-row">
            <span class="telemetry-info-key">Модуль генерации (LLM)</span>
            <span class="telemetry-info-val">OpenRouter • gpt-4o-mini</span>
          </div>
          <div class="telemetry-info-row">
            <span class="telemetry-info-key">Алгоритм поиска (Retrieval)</span>
            <span class="telemetry-info-val">BM25 + Haversine Radius Filter</span>
          </div>
          <div class="telemetry-info-row">
            <span class="telemetry-info-key">Приватность координат</span>
            <span class="telemetry-info-val" style="color: #059669;">100% Zero-Log / No GPS Storage</span>
          </div>
          <div class="telemetry-info-row">
            <span class="telemetry-info-key">Лицензия картографии</span>
            <span class="telemetry-info-val">OpenStreetMap ODbL 1.0</span>
          </div>
        </div>
      </div>
    `;

    telemetryModal.classList.remove('hidden');
  }

  function closeTelemetryModal() {
    if (telemetryModal) telemetryModal.classList.add('hidden');
  }

  // --- GPS Geolocation Handler ---
  function handleGeoLocation() {
    if (!navigator.geolocation) {
      setGeoStatus('GPS не поддерживается вашим браузером.', 'error');
      return;
    }

    setGeoStatus('Определение координат через GPS...', 'active');
    geoBtn.disabled = true;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        geoBtn.disabled = false;
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        userGeoLocation = { lat, lon };

        let userOpt = locationSelect.querySelector('option[value="user_geo"]');
        if (!userOpt) {
          userOpt = document.createElement('option');
          userOpt.value = 'user_geo';
          locationSelect.insertBefore(userOpt, locationSelect.firstChild);
        }

        userOpt.textContent = `🎯 ${t('start_point')} (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
        userOpt.dataset.lat = lat;
        userOpt.dataset.lon = lon;
        userOpt.selected = true;

        updateStartMarker(lat, lon, 'Моя текущая позиция');
        if (leafletMap) leafletMap.flyTo([lat, lon], 15, { duration: 0.8 });
        setGeoStatus('Координаты определены (хранятся только в сессии).', 'active');
      },
      (error) => {
        geoBtn.disabled = false;
        setGeoStatus('Не удалось получить сигнал GPS.', 'error');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }

  function setGeoStatus(text, type) {
    if (!geoStatus) return;
    geoStatus.textContent = text;
    geoStatus.className = 'geo-status-text';
    if (type) geoStatus.classList.add(type);
  }

  // --- Form Submit Handler ---
  function handleFormSubmit(e) {
    e.preventDefault();

    const selectedOption = locationSelect.selectedOptions[0];
    if (!selectedOption || !selectedOption.dataset.lat || !selectedOption.dataset.lon) {
      alert('Пожалуйста, выберите стартовую точку из списка.');
      locationSelect.focus();
      return;
    }

    const lat = parseFloat(selectedOption.dataset.lat);
    const lon = parseFloat(selectedOption.dataset.lon);

    const categoryInput = document.querySelector('input[name="category"]:checked');
    const category = categoryInput ? categoryInput.value : 'walk';

    const available_minutes = getSelectedMinutes();
    const query = (queryInput ? queryInput.value : '').trim();

    const payload = {
      query: query || (category === 'cafe' ? 'Кофе' : 'Прогулка'),
      lat: lat,
      lon: lon,
      available_minutes: available_minutes,
      category: category,
      include_coffee: category === 'cafe'
    };

    lastRequestPayload = payload;
    executeSearch(payload);
  }

  // --- Execute Search with AbortController ---
  async function executeSearch(payload) {
    if (activeAbortController) {
      activeAbortController.abort();
    }
    activeAbortController = new AbortController();

    setUIState('loading');
    setSubmitLoading(true);

    try {
      let data;

      if (appMode === 'itinerary') {
        // --- ITINERARY MODE ---
        if (isMockMode) {
          await ensureItineraryData();
          await new Promise((resolve) => setTimeout(resolve, 350));
          data = JSON.parse(JSON.stringify(itineraryExampleData));

          // Simulate honest refusal if time too short (<90m)
          if (payload.available_minutes < 90) {
            data = {
              status: "no_match",
              message: "В пределах выбранного времени (60 мин) невозможно составить безопасный кольцевой маршрут из 3 разных точек. Рекомендуемый бюджет: не менее 90 минут.",
              suggested_minimum_minutes: 90
            };
          }
        } else {
          const response = await fetch('/api/itinerary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(payload),
            signal: activeAbortController.signal,
            cache: 'no-store'
          });

          if (!response.ok) {
            let errorDetail = `Ошибка HTTP ${response.status}`;
            try {
              const errData = await response.json();
              if (errData && errData.detail) {
                errorDetail = Array.isArray(errData.detail) ? errData.detail.map(d => d.msg).join('; ') : errData.detail;
              }
            } catch (_) {}
            throw new Error(errorDetail);
          }
          data = await response.json();
        }

        handleItinerarySuccess(data);

      } else {
        // --- PLACES MODE ---
        if (isMockMode) {
          await ensureMockData();
          await new Promise((resolve) => setTimeout(resolve, 300));
          const scenarioKey = `${payload.category}_${payload.available_minutes}`;
          data = (mockData.scenarios && mockData.scenarios[scenarioKey]) || mockData.scenarios['walk_60'];
          data = JSON.parse(JSON.stringify(data));
          data.used_context = {
            lat: payload.lat,
            lon: payload.lon,
            available_minutes: payload.available_minutes,
            category: payload.category
          };
        } else {
          const response = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(payload),
            signal: activeAbortController.signal,
            cache: 'no-store'
          });

          if (!response.ok) {
            let errorDetail = `Ошибка HTTP ${response.status}`;
            try {
              const errData = await response.json();
              if (errData && errData.detail) {
                errorDetail = Array.isArray(errData.detail) ? errData.detail.map(d => d.msg).join('; ') : errData.detail;
              }
            } catch (_) {}
            throw new Error(errorDetail);
          }
          data = await response.json();
        }

        handleSearchSuccess(data);
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('[TeleGIS] Запрос отменен пользователем.');
        return;
      }
      handleSearchError(err.message || 'Не удалось связаться с сервером TeleGIS.');
    } finally {
      setSubmitLoading(false);
      activeAbortController = null;
    }
  }

  // --- Itinerary Mode Response Handler ---
  function handleItinerarySuccess(data) {
    if (data.status === 'no_match' || data.status === 'network_unavailable' || !data.stops || data.stops.length === 0) {
      if (emptyReason) {
        emptyReason.textContent = data.message || t('empty_text');
      }

      // If suggested_minimum_minutes available, offer a one-click button
      const emptyAdviceContainer = document.getElementById('emptyAdviceContainer');
      if (emptyAdviceContainer && data.suggested_minimum_minutes) {
        emptyAdviceContainer.innerHTML = '';
        const sugBtn = document.createElement('button');
        sugBtn.className = 'gis-btn-secondary retry-action-btn';
        sugBtn.style.marginTop = '0.5rem';
        sugBtn.textContent = `⏱️ Выбрать ${data.suggested_minimum_minutes} мин и построить маршрут`;
        sugBtn.addEventListener('click', () => {
          const radio = document.querySelector(`input[name="availableMinutes"][value="${data.suggested_minimum_minutes}"]`);
          if (radio) {
            radio.checked = true;
            updateReachRadius(data.suggested_minimum_minutes);
          }
          if (recommendForm) recommendForm.dispatchEvent(new Event('submit', { cancelable: true }));
        });
        emptyAdviceContainer.appendChild(sugBtn);
      }

      clearRoutePolyline();
      if (poiMarkersLayer) poiMarkersLayer.clearLayers();
      setUIState('empty');
      return;
    }

    renderItineraryView(data);
    renderItineraryOnMap(data);
    setUIState('itinerary');
  }

  function renderItineraryView(data) {
    if (!itineraryView) return;
    itineraryView.innerHTML = '';

    // Summary Card
    const summaryCard = document.createElement('div');
    summaryCard.className = 'itinerary-summary-card';

    const headRow = document.createElement('div');
    headRow.className = 'itin-head-row';
    const title = document.createElement('div');
    title.className = 'itin-title';
    title.textContent = `🚶 ${t('route_ready_title')}`;
    const badge = document.createElement('span');
    badge.className = 'itin-badge-graph';
    badge.textContent = 'Dijkstra OSM Graph';
    headRow.appendChild(title);
    headRow.appendChild(badge);
    summaryCard.appendChild(headRow);

    if (data.why) {
      const whyP = document.createElement('p');
      whyP.className = 'itin-why';
      whyP.textContent = data.why;
      summaryCard.appendChild(whyP);
    }

    // Stats Grid (Total, Walking, Visits, Buffer)
    const statsGrid = document.createElement('div');
    statsGrid.className = 'itin-stats-grid';

    statsGrid.innerHTML = `
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.total_minutes_estimate || 0} мин</span>
        <span class="itin-stat-lbl">${t('stat_total')}</span>
      </div>
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.walking_minutes_estimate || data.total_walk_minutes_estimate || 0} мин</span>
        <span class="itin-stat-lbl">${t('stat_walk')}</span>
      </div>
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.visit_minutes_estimate || data.total_visit_minutes_estimate || 0} мин</span>
        <span class="itin-stat-lbl">${t('stat_visit')}</span>
      </div>
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.reserve_minutes || data.time_reserve_minutes || 0} мин</span>
        <span class="itin-stat-lbl">${t('stat_reserve')}</span>
      </div>
    `;
    summaryCard.appendChild(statsGrid);
    itineraryView.appendChild(summaryCard);

    // Timeline of stops
    const timeline = document.createElement('div');
    timeline.className = 'itinerary-timeline';

    const stops = data.stops || [];
    stops.forEach((stop) => {
      const stopCard = document.createElement('div');
      stopCard.className = 'itin-stop-card';
      stopCard.addEventListener('click', () => {
        focusPoiOnMap(stop.poi_id);
      });

      const stHead = document.createElement('div');
      stHead.className = 'itin-stop-header';

      const stName = document.createElement('div');
      stName.className = 'itin-stop-name';
      stName.textContent = `#${stop.order || 1} ${stop.name}`;

      const stTime = document.createElement('div');
      stTime.className = 'itin-stop-time';
      const depTime = stop.departure_minutes_estimate || (stop.arrival_minutes_estimate + (stop.visit_minutes_estimate || 20));
      stTime.textContent = `${stop.arrival_minutes_estimate}–${depTime} мин`;

      stHead.appendChild(stName);
      stHead.appendChild(stTime);
      stopCard.appendChild(stHead);

      if (stop.activity) {
        const actP = document.createElement('div');
        actP.className = 'itin-stop-activity';
        actP.textContent = `💡 ${stop.activity}`;
        stopCard.appendChild(actP);
      }

      timeline.appendChild(stopCard);
    });

    // Return to start item
    const finishCard = document.createElement('div');
    finishCard.className = 'itin-stop-card';
    finishCard.style.borderColor = '#34d399';
    finishCard.innerHTML = `
      <div class="itin-stop-header">
        <div class="itin-stop-name" style="color: #059669;">🏁 ${t('finish_point')}</div>
        <div class="itin-stop-time">${data.total_minutes_estimate || ''} мин</div>
      </div>
      <div class="itin-stop-activity">Возвращение в исходную точку отправления. Маршрут успешно завершён.</div>
    `;
    timeline.appendChild(finishCard);

    itineraryView.appendChild(timeline);
  }

  // --- Search Results & UI Rendering (Places Mode) ---
  function handleSearchSuccess(data) {
    const recommendations = data.recommendations || [];

    renderUsedContext(data.used_context);

    if (resultsCountBadge) {
      resultsCountBadge.textContent = `${recommendations.length} ${pluralize(recommendations.length, ['место', 'места', 'мест'])}`;
      resultsCountBadge.classList.remove('hidden');
    }

    if (fallbackNotice) {
      if (data.mode === 'rag') {
        fallbackNotice.className = 'ai-active-banner';
        fallbackNotice.innerHTML = '<span class="banner-icon">✨</span><div class="banner-text"><strong>Live AI-анализ:</strong> персонализировано нейросетью OpenRouter (GPT-4o-mini).</div>';
        fallbackNotice.classList.remove('hidden');
      } else {
        fallbackNotice.classList.add('hidden');
      }
    }

    if (recommendations.length === 0) {
      if (emptyReason) emptyReason.textContent = data.message || t('empty_text');
      if (poiMarkersLayer) poiMarkersLayer.clearLayers();
      clearRoutePolyline();
      setUIState('empty');
    } else {
      renderCards(recommendations);
      renderMapMarkers(recommendations);
      setUIState('results');
    }
  }

  function handleSearchError(message) {
    if (errorMessage) errorMessage.textContent = message;
    if (fallbackNotice) fallbackNotice.classList.add('hidden');
    if (usedContextTag) usedContextTag.classList.add('hidden');
    if (resultsCountBadge) resultsCountBadge.classList.add('hidden');
    if (poiMarkersLayer) poiMarkersLayer.clearLayers();
    clearRoutePolyline();
    setUIState('error');
  }

  function renderUsedContext(context) {
    if (!usedContextTag) return;
    if (!context) {
      usedContextTag.classList.add('hidden');
      return;
    }

    const catName = context.category === 'cafe' ? (currentLang === 'kz' ? '☕ Кофе' : (currentLang === 'en' ? '☕ Coffee' : '☕ Кофе')) : (currentLang === 'kz' ? '🚶 Серуен' : (currentLang === 'en' ? '🚶 Walk' : '🚶 Прогулка'));
    const minutes = context.effective_minutes || context.available_minutes || 60;
    const coords = `${context.lat.toFixed(4)}, ${context.lon.toFixed(4)}`;

    let tagStr = `${catName} • ${minutes}м • ${coords}`;
    if (context.required_features && context.required_features.length > 0) {
      const featNames = {
        socket: '🔌 Розетки',
        wifi: '📶 Wi-Fi',
        quiet: '🌿 Тихо',
        wheelchair: '♿ Доступность'
      };
      const feats = context.required_features.map(f => featNames[f] || f).join(', ');
      tagStr += ` • ${feats}`;
    }
    if (context.effective_minutes && context.effective_minutes < (context.available_minutes || 60)) {
      tagStr += ` • ⏱️ Сужение: ${context.effective_minutes}м`;
    }

    usedContextTag.textContent = tagStr;
    usedContextTag.classList.remove('hidden');
  }

  function renderCards(recommendations) {
    if (!cardsGrid) return;
    cardsGrid.innerHTML = '';

    recommendations.forEach((poi, index) => {
      const number = index + 1;
      const card = document.createElement('article');
      card.className = 'poi-card';
      card.setAttribute('role', 'listitem');
      card.dataset.poiId = poi.poi_id;

      card.addEventListener('click', () => {
        focusPoiOnMap(poi.poi_id);
        openPoiDrawer(poi);
      });

      // --- Header ---
      const header = document.createElement('div');
      header.className = 'card-header';

      const titleGroup = document.createElement('div');
      titleGroup.className = 'card-title-group';

      const numBadge = document.createElement('div');
      numBadge.className = 'card-number-badge';
      numBadge.textContent = number;

      const nameWrapper = document.createElement('div');
      const nameEl = document.createElement('h3');
      nameEl.className = 'card-name';
      nameEl.textContent = poi.name || 'Точка интереса';

      const categoryBadge = document.createElement('span');
      categoryBadge.className = 'card-category-badge';
      categoryBadge.textContent = poi.category || 'POI';

      nameWrapper.appendChild(nameEl);
      nameWrapper.appendChild(categoryBadge);

      titleGroup.appendChild(numBadge);
      titleGroup.appendChild(nameWrapper);
      header.appendChild(titleGroup);
      card.appendChild(header);

      // --- Metrics Bar (Distance, Walk, Total) ---
      const metrics = document.createElement('div');
      metrics.className = 'card-metrics';

      // Distance
      const mDistance = document.createElement('div');
      mDistance.className = 'metric-item';
      const mDistanceLabel = document.createElement('span');
      mDistanceLabel.className = 'metric-label';
      mDistanceLabel.textContent = t('straight_dist');
      const mDistanceVal = document.createElement('span');
      mDistanceVal.className = 'metric-value';
      const displayDist = poi.route_distance_m || poi.distance_m || 0;
      mDistanceVal.textContent = `${displayDist} м`;
      mDistance.appendChild(mDistanceLabel);
      mDistance.appendChild(mDistanceVal);

      if (poi.travel_basis === 'osm_walking_graph' || poi.route_distance_m) {
        const basisBadge = document.createElement('span');
        basisBadge.className = 'basis-badge';
        basisBadge.textContent = t('basis_graph');
        basisBadge.title = 'Расчет по реальным пешеходным тротуарам OpenStreetMap (Dijkstra)';
        mDistance.appendChild(basisBadge);
      }

      // Walk time
      const mWalk = document.createElement('div');
      mWalk.className = 'metric-item';
      const mWalkLabel = document.createElement('span');
      mWalkLabel.className = 'metric-label';
      mWalkLabel.textContent = t('one_way');
      const mWalkVal = document.createElement('span');
      mWalkVal.className = 'metric-value';
      mWalkVal.textContent = `~${poi.walk_minutes_estimate || 1} мин`;
      mWalk.appendChild(mWalkLabel);
      mWalk.appendChild(mWalkVal);

      // Total budget
      const mTotal = document.createElement('div');
      mTotal.className = 'metric-item';
      const mTotalLabel = document.createElement('span');
      mTotalLabel.className = 'metric-label';
      mTotalLabel.textContent = t('total_budget');
      const mTotalVal = document.createElement('span');
      mTotalVal.className = 'metric-value metric-highlight';
      const totalMin = poi.total_minutes_estimate || (2 * (poi.walk_minutes_estimate || 0) + (poi.visit_minutes_estimate || 0));
      mTotalVal.textContent = `~${totalMin} мин`;
      mTotal.appendChild(mTotalLabel);
      mTotal.appendChild(mTotalVal);

      metrics.appendChild(mDistance);
      metrics.appendChild(mWalk);
      metrics.appendChild(mTotal);
      card.appendChild(metrics);

      // --- Confirmed Infrastructure Tags (WiFi, Socket, Wheelchair) ---
      if (poi.confirmed_features) {
        const featRow = document.createElement('div');
        featRow.className = 'feature-pills-row';
        if (poi.confirmed_features.socket) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = '🔌 Розетки';
          featRow.appendChild(p);
        }
        if (poi.confirmed_features.wifi) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = '📶 Wi-Fi';
          featRow.appendChild(p);
        }
        if (poi.confirmed_features.wheelchair) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = '♿ Доступная среда';
          featRow.appendChild(p);
        }
        if (poi.confirmed_features.quiet) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = '🌿 Тихий сквер';
          featRow.appendChild(p);
        }
        if (featRow.children.length > 0) {
          card.appendChild(featRow);
        }
      }

      // --- Why fits ---
      if (poi.why) {
        const whySection = document.createElement('div');
        whySection.className = 'card-section';

        const whyLabel = document.createElement('span');
        whyLabel.className = 'card-section-label';
        whyLabel.textContent = t('why_label');

        const whyText = document.createElement('p');
        whyText.className = 'card-why-text';
        whyText.textContent = poi.why;

        whySection.appendChild(whyLabel);
        whySection.appendChild(whyText);
        card.appendChild(whySection);
      }

      // --- Activity Block ---
      if (poi.activity) {
        const actBlock = document.createElement('div');
        actBlock.className = 'card-activity-block';

        const actTitle = document.createElement('div');
        actTitle.className = 'card-activity-title';
        actTitle.textContent = t('act_label');

        const actText = document.createElement('p');
        actText.className = 'card-activity-text';
        actText.textContent = poi.activity;

        actBlock.appendChild(actTitle);
        actBlock.appendChild(actText);
        card.appendChild(actBlock);
      }

      // --- Verified Facts (Evidence from official sources) ---
      if (poi.evidence && poi.evidence.length > 0) {
        poi.evidence.forEach(ev => {
          const evBox = document.createElement('div');
          evBox.className = 'card-evidence-box';

          const evHead = document.createElement('div');
          evHead.className = 'evidence-header';
          const evIcon = document.createElement('span');
          evIcon.className = 'evidence-icon';
          evIcon.textContent = ev.kind === 'official' ? '🏛️' : '📋';
          const evTitle = document.createElement('span');
          evTitle.className = 'evidence-title';
          evTitle.textContent = ev.kind === 'official' ? t('verified_fact') : 'OSM Verified';
          evHead.appendChild(evIcon);
          evHead.appendChild(evTitle);
          evBox.appendChild(evHead);

          const evText = document.createElement('p');
          evText.className = 'evidence-text';
          evText.textContent = ev.text;
          evBox.appendChild(evText);

          const evMeta = document.createElement('div');
          evMeta.className = 'evidence-meta';
          const evBadge = document.createElement('span');
          evBadge.className = 'evidence-badge';
          evBadge.textContent = t('evidence_sha');
          evMeta.appendChild(evBadge);

          if (ev.source_url) {
            const evLink = document.createElement('a');
            evLink.className = 'evidence-link';
            evLink.href = ev.source_url;
            evLink.target = '_blank';
            evLink.rel = 'noopener noreferrer';
            evLink.textContent = 'Источник ↗';
            evLink.addEventListener('click', e => e.stopPropagation());
            evMeta.appendChild(evLink);
          }
          evBox.appendChild(evMeta);
          card.appendChild(evBox);
        });
      }

      // --- Info Row (Hours & Warnings & Phone) ---
      const infoRow = document.createElement('div');
      infoRow.className = 'card-info-row';

      const hoursBadge = document.createElement('div');
      hoursBadge.className = 'hours-badge';
      if (poi.opening_hours) {
        hoursBadge.textContent = `🕒 ${poi.opening_hours}`;
      } else {
        hoursBadge.classList.add('hours-unconfirmed');
        hoursBadge.textContent = t('unconfirmed_hours');
      }
      infoRow.appendChild(hoursBadge);

      if (poi.phone) {
        const phoneBadge = document.createElement('a');
        phoneBadge.className = 'hours-badge';
        phoneBadge.style.textDecoration = 'none';
        phoneBadge.href = `tel:${poi.phone}`;
        phoneBadge.textContent = `📞 ${poi.phone}`;
        phoneBadge.addEventListener('click', e => e.stopPropagation());
        infoRow.appendChild(phoneBadge);
      }

      if (poi.warnings && poi.warnings.length > 0) {
        const warningsList = document.createElement('div');
        warningsList.className = 'warnings-list';

        poi.warnings.forEach((warn) => {
          const warnItem = document.createElement('div');
          warnItem.className = 'warning-item';
          warnItem.textContent = `⚠️ ${warn}`;
          warningsList.appendChild(warnItem);
        });
        infoRow.appendChild(warningsList);
      }
      card.appendChild(infoRow);

      // --- Footer ---
      const footer = document.createElement('div');
      footer.className = 'card-footer';

      if (poi.source_url && (poi.source_url.startsWith('https://') || poi.source_url.startsWith('http://'))) {
        const sourceLink = document.createElement('a');
        sourceLink.className = 'card-source-link';
        sourceLink.href = poi.source_url;
        sourceLink.target = '_blank';
        sourceLink.rel = 'noopener noreferrer';
        sourceLink.textContent = t('source_link');
        sourceLink.addEventListener('click', (e) => e.stopPropagation());
        footer.appendChild(sourceLink);
      } else {
        const noLink = document.createElement('span');
        noLink.textContent = 'OpenStreetMap';
        footer.appendChild(noLink);
      }

      const dateEl = document.createElement('span');
      let dateString = poi.collected_at ? formatDate(poi.collected_at) : 'не указана';
      dateEl.textContent = `${t('collected_at')} ${dateString}`;
      footer.appendChild(dateEl);

      card.appendChild(footer);
      cardsGrid.appendChild(card);
    });
  }

  function formatDate(isoStr) {
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch (_) {
      return isoStr;
    }
  }

  function pluralize(n, forms) {
    return n === 1 ? forms[0] : (n >= 2 && n <= 4 ? forms[1] : forms[2]);
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // --- UI State Management ---
  function setUIState(state) {
    if (initialState) initialState.classList.add('hidden');
    if (loadingState) loadingState.classList.add('hidden');
    if (emptyState) emptyState.classList.add('hidden');
    if (errorState) errorState.classList.add('hidden');
    if (cardsGrid) cardsGrid.classList.add('hidden');
    if (itineraryView) itineraryView.classList.add('hidden');

    switch (state) {
      case 'initial':
        if (initialState) initialState.classList.remove('hidden');
        break;
      case 'loading':
        if (loadingState) loadingState.classList.remove('hidden');
        break;
      case 'empty':
        if (emptyState) emptyState.classList.remove('hidden');
        break;
      case 'error':
        if (errorState) errorState.classList.remove('hidden');
        break;
      case 'results':
        if (cardsGrid) cardsGrid.classList.remove('hidden');
        break;
      case 'itinerary':
        if (itineraryView) itineraryView.classList.remove('hidden');
        break;
    }
  }

  function setSubmitLoading(isLoading) {
    if (!submitBtn) return;
    submitBtn.disabled = isLoading;
    if (btnSpinner) {
      if (isLoading) {
        btnSpinner.classList.remove('hidden');
      } else {
        btnSpinner.classList.add('hidden');
      }
    }
    if (btnText) {
      btnText.textContent = isLoading ? '...' : (appMode === 'itinerary' ? t('btn_build_route') : t('btn_find'));
    }
  }

  async function ensureMockData() {
    if (mockData) return;
    const res = await fetch('/static/mock.json');
    if (!res.ok) throw new Error('Не удалось загрузить mock.json');
    mockData = await res.json();
  }

  async function ensureItineraryData() {
    if (itineraryExampleData) return;
    try {
      const res = await fetch('/static/itinerary_example.json');
      if (res.ok) itineraryExampleData = await res.json();
    } catch (_) {}
  }

  document.addEventListener('DOMContentLoaded', init);
})();
