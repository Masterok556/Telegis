/**
 * Telegis — Fullscreen GIS Engine (v3.2)
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
      route_return: 'С возвратом',
      loading_locations: 'Загрузка локаций...',
      cat_walk: 'Пешая прогулка',
      cat_cafe: 'Кофе и отдых',
      time_budget_label: 'Бюджет времени:',
      query_placeholder: 'Пожелание: сквер, панорама, круассан...',
      btn_find: 'Найти',
      btn_build_route: 'Построить маршрут',
      budget_badge: '⏱️ Честный бюджет:',
      budget_desc: 'дорога туда + посещение + возврат к старту',
      tag_child: '👶 С ребёнком',
      tag_tourist: '🏛️ Я турист',
      tag_night: '🌙 Ночью',
      tag_view: '📸 Вид на сферу',
      tag_quiet: '🌿 Тихий сквер',
      tag_togo: '☕ Навынос',
      init_head: 'Интеллектуальный радар прогулок',
      init_text: 'Выберите время и категорию — Telegis подберёт до 3 мест по сохранённым данным OSM и покажет ограничения.',
      preset_label: 'Быстрые сценарии:',
      preset_1: '🚶 60 мин вокруг EXPO',
      preset_2: '☕ Кофе на 30 мин',
      preset_3: '⚡ 20 мин размяться',
      loading_head: 'Telegis анализирует местность...',
      loading_text: 'Вычисляем пешеходные расстояния по графу дорог и ранжируем локации.',
      empty_head: 'Точки не найдены',
      empty_text: 'В заданном радиусе и бюджете времени нет доступных мест.',
      empty_advice: 'Совет: увеличьте время или выберите другой формат отдыха.',
      error_head: 'Ошибка соединения',
      connection_error: 'Не удалось связаться с сервером. Проверьте, что Telegis запущен, и повторите запрос.',
      btn_retry: 'Повторить попытку',
      fallback_title: 'Шаблонный режим:',
      fallback_desc: 'рекомендации подобраны по проверенной базе POI без вызова LLM.',
      radius_label: 'Ориентир по прямой (не изохрона):',
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
      verified_fact: '🏛️ По официальному источнику',
      evidence_sha: 'Сведения источника'
    },
    kz: {
      mock_title: 'ТЕСТТІК РЕЖИМ (MOCK)',
      mock_desc: 'нақты API өшірілген. Нақты режим үшін ?mock=1 өшіріңіз.',
      city_tag: 'Астана • EXPO',
      subtitle: 'Жаяу серуендеуге арналған ЖИ-кеңесші',
      mode_places: 'Орындар',
      mode_itinerary: 'Бағыт',
      route_return: 'Қайтып келу',
      loading_locations: 'Орындар жүктелуде...',
      cat_walk: 'Жаяу серуен',
      cat_cafe: 'Кофе және демалыс',
      time_budget_label: 'Уақыт қоры:',
      query_placeholder: 'Қалаған нәрсе: саябақ, панорама, кофе...',
      btn_find: 'Табу',
      btn_build_route: 'Бағыт құру',
      budget_badge: '⏱️ Адал уақыт есебі:',
      budget_desc: 'бару жолы + болу уақыты + қайту жолы',
      tag_child: '👶 Баламен',
      tag_tourist: '🏛️ Мен туристпін',
      tag_night: '🌙 Түнде',
      tag_view: '📸 Сфера көрінісі',
      tag_quiet: '🌿 Тыныш саябақ',
      tag_togo: '☕ Алып кету',
      init_head: 'Интеллектуалды серуен радары',
      init_text: 'Уақыт пен форматты таңдаңыз — Telegis OpenStreetMap жолдар графигі бойынша EXPO аймағындағы ең жақсы нұсқаларды ұсынады.',
      preset_label: 'Жылдам сценарийлер:',
      preset_1: '🚶 EXPO маңында 60 мин',
      preset_2: '☕ 30 мин кофе ішу',
      preset_3: '⚡ 20 мин серуен',
      loading_head: 'Telegis аймақты талдауда...',
      loading_text: 'Жаяу жүру қашықтығын есептеп, орындарды сұрыптаудамыз.',
      empty_head: 'Орындар табылмады',
      empty_text: 'Берілген уақыт пен қашықтықта қолжетімді орындар жоқ.',
      empty_advice: 'Кеңес: қолжетімді уақытты арттырыңыз немесе басқа форматты таңдаңыз.',
      error_head: 'Байланыс қатесі',
      connection_error: 'Серверге қосылу мүмкін болмады. Telegis іске қосылғанын тексеріп, сұрауды қайталаңыз.',
      btn_retry: 'Қайта көру',
      fallback_title: 'Үлгілік режим:',
      fallback_desc: 'ұсыныстар ЖИ үлгісінсіз, тексерілген POI базасынан алынды.',
      radius_label: 'Тікелей қашықтық бағдары:',
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
      evidence_sha: 'Дереккөз мәліметі'
    },
    en: {
      mock_title: 'TEST MODE (MOCK)',
      mock_desc: 'live API disabled. Remove ?mock=1 for live mode.',
      city_tag: 'Astana • EXPO',
      subtitle: 'AI Walking Companion & Navigator',
      mode_places: 'Places',
      mode_itinerary: 'Route',
      route_return: 'Round trip',
      loading_locations: 'Loading starting points...',
      cat_walk: 'Walking',
      cat_cafe: 'Coffee & Relax',
      time_budget_label: 'Time budget:',
      query_placeholder: 'Preferences: quiet park, view, coffee...',
      btn_find: 'Discover',
      btn_build_route: 'Generate Route',
      budget_badge: '⏱️ Honest budget:',
      budget_desc: 'outward walk + on-site stay + return walk',
      tag_child: '👶 With kids',
      tag_tourist: '🏛️ I am a tourist',
      tag_night: '🌙 At night',
      tag_view: '📸 EXPO Sphere view',
      tag_quiet: '🌿 Quiet park',
      tag_togo: '☕ Takeaway',
      init_head: 'Intelligent Walking Radar',
      init_text: 'Select your time and category — Telegis scans OpenStreetMap pedestrian networks to find verified places in the EXPO area.',
      preset_label: 'Quick Scenarios:',
      preset_1: '🚶 60 min around EXPO',
      preset_2: '☕ 30 min coffee break',
      preset_3: '⚡ 20 min quick stroll',
      loading_head: 'Telegis is analyzing the area...',
      loading_text: 'Calculating pedestrian shortest paths and ranking candidate POIs.',
      empty_head: 'No places found',
      empty_text: 'No destinations match your time budget or category in this area.',
      empty_advice: 'Tip: Increase your available time or switch category.',
      error_head: 'Connection Error',
      connection_error: 'Could not connect to the server. Check that Telegis is running and try again.',
      btn_retry: 'Retry Request',
      fallback_title: 'Fallback Mode:',
      fallback_desc: 'recommendations served from verified POI store without LLM.',
      radius_label: 'Straight-line guide (not an isochrone):',
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
      verified_fact: '🏛️ Official source reports',
      evidence_sha: 'Source-reported information'
    }
  };

  const CATEGORY_NAMES = {
    ru: {
      cafe: 'Кафе', restaurant: 'Ресторан', fast_food: 'Быстрое питание',
      park: 'Парк', garden: 'Сад', attraction: 'Достопримечательность',
      monument: 'Памятник', memorial: 'Мемориал', artwork: 'Арт-объект',
      museum: 'Музей', mall: 'Торговый центр', viewpoint: 'Смотровая площадка',
      playground: 'Детская площадка', unknown: 'Место'
    },
    kz: {
      cafe: 'Кафе', restaurant: 'Мейрамхана', fast_food: 'Жылдам тамақтану',
      park: 'Саябақ', garden: 'Бақ', attraction: 'Көрікті жер',
      monument: 'Ескерткіш', memorial: 'Мемориал', artwork: 'Өнер нысаны',
      museum: 'Мұражай', mall: 'Сауда орталығы', viewpoint: 'Шолу алаңы',
      playground: 'Балалар алаңы', unknown: 'Орын'
    },
    en: {
      cafe: 'Café', restaurant: 'Restaurant', fast_food: 'Fast food',
      park: 'Park', garden: 'Garden', attraction: 'Attraction',
      monument: 'Monument', memorial: 'Memorial', artwork: 'Public art',
      museum: 'Museum', mall: 'Shopping centre', viewpoint: 'Viewpoint',
      playground: 'Playground', unknown: 'Place'
    }
  };

  // --- State & Variables ---
  let currentLang = 'ru';
  let appMode = 'places'; // 'places' | 'itinerary'
  let isMockMode = false;
  let mockData = null;
  let activeAbortController = null;
  let locationsList = [];
  let userGeoLocation = null;
  let lastRequestPayload = null;
  const poiCatalog = new Map();

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
  let systemStatusLoaded = false;

  const climateShieldCheck = document.getElementById('climateShieldCheck');

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
    loadAndRenderAllPoisOnMap();
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
    if (params.get('mode') === 'itinerary') {
      setAppMode('itinerary');
    }
    if (params.get('modal') === 'telemetry') {
      setTimeout(openTelemetryModal, 350);
    }
    if (params.get('drawer')) {
      const drawerKey = params.get('drawer');
      setTimeout(() => {
        const found = Array.from(poiCatalog.values()).find(p => p.poi_id === drawerKey || (p.name && p.name.includes(drawerKey)));
        if (found) {
          openPoiDrawer(found);
        } else if (poiCatalog.size > 0) {
          openPoiDrawer(Array.from(poiCatalog.values())[0]);
        }
      }, 600);
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
      console.warn('[Telegis] Включен тестовый режим (?mock=1).');
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
    document.querySelectorAll('[data-poi-category]').forEach(el => {
      el.textContent = `${el.dataset.categoryPrefix || ''}${categoryName(el.dataset.poiCategory)}`;
    });

    // Update submit button text based on mode
    if (btnText) {
      btnText.textContent = appMode === 'itinerary' ? dict.btn_build_route : dict.btn_find;
    }

    updateCategoryLabels();
    updateReachRadius();
    updateSystemStatusText();
  }

  function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || (I18N['ru'] && I18N['ru'][key]) || key;
  }

  function categoryName(value) {
    const names = CATEGORY_NAMES[currentLang] || CATEGORY_NAMES.ru;
    return Object.prototype.hasOwnProperty.call(names, value) ? names[value] : names.unknown;
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
        invalidateSearch();
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

  // --- Right-Side POI Drawer Logic ---
  let currentDrawerPoi = null;
  let drawerAbortController = null;
  let cachedHealth = null;

  const VERIFIED_LANDMARK_PHOTOS = {
    'Mega Silk Way': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9c/%D0%A2%D0%A0%D0%A6_MEGA_Silk-way_%D0%B8_%D0%BE%D1%82%D0%B5%D0%BB%D1%8C_Hilton.jpg/960px-%D0%A2%D0%A0%D0%A6_MEGA_Silk-way_%D0%B8_%D0%BE%D1%82%D0%B5%D0%BB%D1%8C_Hilton.jpg',
      license: 'Wikimedia Commons · CC BY-SA 4.0'
    },
    'Astana IT University': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5a/%D0%9A%D0%BE%D0%B2%D0%BE%D1%80%D0%BA%D0%B8%D0%BD%D0%B3_Astana_IT_University_%281%29.jpg/960px-%D0%9A%D0%BE%D0%B2%D0%BE%D1%80%D0%BA%D0%B8%D0%BD%D0%B3_Astana_IT_University_%281%29.jpg',
      license: 'Wikimedia Commons · CC BY-SA 4.0'
    },
    'Astana Hub': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/7/77/Oljas_Bektenov_and_Aljaksandar_Tur%C4%8Dyn_at_Astana_Hub.jpg/960px-Oljas_Bektenov_and_Aljaksandar_Tur%C4%8Dyn_at_Astana_Hub.jpg',
      license: 'Wikimedia Commons · CC BY 4.0'
    },
    'Сфера «Нұр Әлем»': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/60/Astana%2C_view.jpg/960px-Astana%2C_view.jpg',
      license: 'Wikimedia Commons · CC0'
    },
    'Alem.ai': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/60/Astana%2C_view.jpg/960px-Astana%2C_view.jpg',
      license: 'Wikimedia Commons · Павильон B1 EXPO'
    },
    'МФЦА / AIFC': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8f/Astana_International_Financial_Centre_logo.jpg/960px-Astana_International_Financial_Centre_logo.jpg',
      license: 'Wikimedia Commons · AIFC'
    },
    'Ботанический сад': {
      thumb: 'https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8a/%D0%90%D1%81%D1%82%D0%B0%D0%BD%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9_%D0%B1%D0%BE%D1%82%D0%B0%D0%BD%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%B0%D0%B4.jpg/960px-%D0%90%D1%81%D1%82%D0%B0%D0%BD%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9_%D0%B1%D0%BE%D1%82%D0%B0%D0%BD%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%B0%D0%B4.jpg',
      license: 'Wikimedia Commons · CC BY-SA 4.0'
    },
    'Триумфальная арка': {
      thumb: 'https://upload.wikimedia.org/wikipedia/commons/1/11/Stamps_of_Kazakhstan%2C_2012-32.jpg',
      license: 'Wikimedia Commons · Общественное достояние'
    }
  };

  const wikiPhotoCache = new Map();

  async function loadWikimediaPhoto(poi, controller) {
    if (typeof window === 'undefined' || !window.location?.protocol?.startsWith('http')) return;
    const name = (poi.name || '').trim();
    if (!name) return;

    for (const [key, val] of Object.entries(VERIFIED_LANDMARK_PHOTOS)) {
      if (name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(name.toLowerCase())) {
        applyPhotoToDrawer(val.thumb, val.license, controller);
        return;
      }
    }

    if (wikiPhotoCache.has(name)) {
      const cached = wikiPhotoCache.get(name);
      if (cached) applyPhotoToDrawer(cached.thumb, cached.license, controller);
      return;
    }

    const cleaned = name.replace(/·\s*OSM.*$/i, '').replace(/[\(\)]/g, '').trim();
    if (cleaned.length < 3) return;

    try {
      const url = 'https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch=' +
        encodeURIComponent(cleaned + ' Astana') + '&gsrlimit=1&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=800&format=json&origin=*';
      const res = await fetch(url, { signal: controller.signal });
      if (!res.ok) return;
      const data = await res.json();
      if (controller.signal.aborted) return;
      const pages = data.query?.pages;
      if (!pages) {
        wikiPhotoCache.set(name, null);
        return;
      }
      const page = Object.values(pages)[0];
      const info = page.imageinfo?.[0];
      const thumb = info?.thumburl || info?.url;
      if (thumb) {
        const license = info.extmetadata?.LicenseShortName?.value || 'Wikimedia Commons';
        const photoData = { thumb, license: `Wikimedia Commons · ${license}` };
        wikiPhotoCache.set(name, photoData);
        applyPhotoToDrawer(thumb, photoData.license, controller);
      } else {
        wikiPhotoCache.set(name, null);
      }
    } catch (_) {}
  }

  function applyPhotoToDrawer(url, licenseText, controller) {
    const img = document.getElementById('drawerHeroImg');
    const placeholder = document.getElementById('drawerHeroPlaceholder');
    const tag = document.getElementById('drawerGalleryTag');
    if (!img) return;

    const onDone = () => {
      if (controller && controller.signal.aborted) return;
      img.classList.remove('hidden');
      img.style.visibility = 'visible';
      if (placeholder) placeholder.classList.add('hidden');
      if (tag) tag.textContent = '📸 ' + licenseText;
    };

    img.onload = onDone;
    img.onerror = () => {
      img.classList.add('hidden');
      img.style.visibility = 'hidden';
      if (placeholder) placeholder.classList.remove('hidden');
    };
    img.referrerPolicy = 'no-referrer';
    img.src = url;
    if (img.complete && img.naturalWidth > 0) {
      onDone();
    }
  }

  function openPoiDrawer(poi) {
    const drawer = document.getElementById('poiDrawer');
    if (!drawer || !poi) return;
    // Recommendations add request-specific timing, while the catalogue owns
    // source amenities/address. Keep both when opening the same canonical POI.
    poi = { ...(poiCatalog.get(poi.poi_id) || {}), ...poi };
    if (drawerAbortController) drawerAbortController.abort();
    const controller = new AbortController();
    drawerAbortController = controller;
    currentDrawerPoi = poi;
    const field = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    field('drawerCategoryBadge', `📍 ${categoryName(poi.category)}`);
    const categoryBadge = document.getElementById('drawerCategoryBadge');
    if (categoryBadge) {
      categoryBadge.dataset.poiCategory = poi.category || '';
      categoryBadge.dataset.categoryPrefix = '📍 ';
    }
    field('drawerDistBadge', Number.isFinite(poi.distance_m) ? `${poi.distance_m} м по прямой` : 'Расстояние не рассчитано');
    field('drawerTitle', poi.name || 'Объект Telegis');
    const street = poi.tags?.['addr:street'];
    field('drawerAddress', street ? `📍 ${street} ${poi.tags['addr:housenumber'] || ''}` : 'Адрес в данных не указан');

    // A stock illustration must never be presented as a photograph of this POI.
    const img = document.getElementById('drawerHeroImg');
    if (img) {
      img.removeAttribute('src');
      img.alt = 'Фотография объекта не подтверждена';
      img.classList.add('hidden');
      img.style.visibility = 'hidden';
    }
    const catIcons = {
      cafe: '☕', restaurant: '🍽️', fast_food: '🍔',
      park: '🌿', garden: '🌸', attraction: '🏛️',
      monument: '🗿', museum: '🖼️', mall: '🛍️', playground: '👶',
      artwork: '🎨', memorial: '🕊️'
    };
    const heroIcon = document.getElementById('drawerHeroIcon');
    if (heroIcon) heroIcon.textContent = catIcons[poi.category] || '🧭';
    const placeholder = document.getElementById('drawerHeroPlaceholder');
    if (placeholder) placeholder.classList.remove('hidden');
    field('drawerGalleryTag', '📍 Фотография объекта пока не подтверждена');

    // Load real sourced photo from Wikimedia Commons (if available)
    loadWikimediaPhoto(poi, controller);
    const features = document.getElementById('drawerFeaturesGrid');
    if (features) {
      features.replaceChildren();
      const f = poi.confirmed_features || {};
      const feature = (key, label) => `${label}: ${f[key] === true ? 'указано в OSM' : f[key] === false ? 'не отмечено как доступное' : 'нет подтверждённых данных'}`;
      [
        poi.opening_hours ? `🕒 По данным источника: ${poi.opening_hours}. Проверьте перед визитом.` : '🕒 Часы не подтверждены',
        feature('wifi', '📶 Wi-Fi'), feature('socket', '⚡ Розетки'),
        feature('wheelchair', '♿ Доступность'), feature('quiet', '🌿 Тишина'),
        poi.phone ? `📞 ${poi.phone}` : '📞 Телефон не указан'
      ].forEach(text => {
        const item = document.createElement('div');
        item.className = 'drawer-feat-item';
        item.textContent = text;
        features.appendChild(item);
      });
    }
    const factsList = document.getElementById('drawerFactsList');
    const factsSection = document.getElementById('drawerFactsSection');
    const showFacts = (facts, warnings) => {
      if (!factsList || !factsSection) return;
      factsList.replaceChildren();
      (facts || []).forEach(fact => {
        const item = document.createElement('li');
        item.className = 'drawer-fact-item';
        item.textContent = fact.text;
        appendSource(item, fact.source_url, `Источник · ${formatDate(fact.collected_at)}`);
        factsList.appendChild(item);
      });
      (warnings || []).forEach(warning => {
        const item = document.createElement('li');
        item.className = 'drawer-fact-item';
        item.textContent = `⚠️ ${warning}`;
        factsList.appendChild(item);
      });
      factsSection.classList.toggle('hidden', factsList.children.length === 0);
    };
    showFacts(poi.evidence, poi.warnings);
    field('drawerAiSummary', poi.description || 'Описание в данных отсутствует.');
    field('drawerAiVibe', isMockMode ? 'Тестовый пример · live API отключён' : 'Сведения из сохранённых источников');
    const tipBox = document.getElementById('drawerAiTipBox');
    if (tipBox) tipBox.style.display = poi.activity ? 'flex' : 'none';
    field('drawerAiTip', poi.activity ? `Идея занятия: ${poi.activity}` : '');
    const osmLink = document.getElementById('drawerOsmLink');
    if (osmLink) {
      const url = safeHttpUrl(poi.source_url);
      if (url) osmLink.href = url;
      else osmLink.removeAttribute('href');
      osmLink.hidden = !url;
    }
    const routeBtn = document.getElementById('drawerRouteBtn');
    if (routeBtn) routeBtn.disabled = poi.recommendable === false;
    if (!isMockMode && poi.poi_id && !String(poi.poi_id).startsWith('loc_') && !String(poi.poi_id).startsWith('bld_')) {
      fetch('/api/poi_ai_info', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poi_id: poi.poi_id }), signal: controller.signal,
        cache: 'no-store'
      }).then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      }).then(data => {
        if (drawerAbortController !== controller || controller.signal.aborted) return;
        field('drawerAiSummary', data.summary || poi.description || 'Описание отсутствует.');
        field('drawerAiTip', data.tip ? `Идея занятия: ${data.tip}` : '');
        if (tipBox) tipBox.style.display = data.tip ? 'flex' : 'none';
        showFacts(data.evidence || poi.evidence, data.warnings || poi.warnings);
      }).catch(error => {
        if (drawerAbortController !== controller || error.name === 'AbortError') return;
        field('drawerAiVibe', 'Дополнительные сведения недоступны; показаны данные карточки.');
      });
    }
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
  }

  function closePoiDrawer() {
    if (drawerAbortController) drawerAbortController.abort();
    drawerAbortController = null;
    const drawer = document.getElementById('poiDrawer');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
  }

  function safeHttpUrl(value) {
    if (!value) return null;
    try {
      const url = new URL(value);
      return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch (_) { return null; }
  }

  function appendSource(container, value, label = 'Источник ↗') {
    const url = safeHttpUrl(value);
    if (!url) return;
    const link = document.createElement('a');
    link.className = 'card-source-link';
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = ` ${label}`;
    link.addEventListener('click', event => event.stopPropagation());
    container.appendChild(link);
  }

  // --- Interactive Map Click Handler ---
  function handleMapClick(lat, lon, label) {
    if (!locationSelect) return;
    invalidateSearch();

    let clickOpt = locationSelect.querySelector('option[value="map_click"]');
    if (!clickOpt) {
      clickOpt = document.createElement('option');
      clickOpt.value = 'map_click';
      locationSelect.insertBefore(clickOpt, locationSelect.firstChild);
    }
    clickOpt.textContent = label || `📍 Точка на карте (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    clickOpt.dataset.lat = lat;
    clickOpt.dataset.lon = lon;
    clickOpt.selected = true;

    updateStartMarker(lat, lon, clickOpt.textContent);
    updateReachRadius();
    showMapToast(`📍 Стартовая точка: ${lat.toFixed(4)}, ${lon.toFixed(4)} (нажмите «Найти»)`);
  }

  // --- Interactive Building & Landmark Badges on Map (2GIS / OSM Style) ---
  const VERIFIED_BUILDINGS = [
    {
      id: 'bld_mega',
      poi_id: 'osm_way_499328514',
      name: 'Mega Silk Way',
      subtitle: 'ТРЦ & Кинотеатр',
      category: 'mall',
      icon: '🛍️',
      lat: 51.0890897,
      lon: 71.4073303,
      description: 'Крупнейший торгово-развлекательный центр в районе EXPO с фудкортом, магазинами и кинотеатром.'
    },
    {
      id: 'bld_hilton',
      poi_id: 'osm_node_5199672688',
      name: 'Hilton Astana',
      subtitle: 'Отель & Бизнес',
      category: 'attraction',
      icon: '🏨',
      lat: 51.0906596,
      lon: 71.4106232,
      description: 'Современный пятизвездочный отель и бизнес-комплекс на территории делового района EXPO.'
    },
    {
      id: 'bld_congress',
      poi_id: 'osm_node_5033100222',
      name: 'Конгресс-центр EXPO',
      subtitle: 'Международный конгресс-холл',
      category: 'attraction',
      icon: '🏛️',
      lat: 51.0924049,
      lon: 71.4113474,
      description: 'Главная конгрессная и концертная арена EXPO для масштабных международных форумов и мероприятий.'
    },
    {
      id: 'bld_astana_hub',
      poi_id: 'loc_astana_hub',
      name: 'Astana Hub',
      subtitle: 'Международный IT-технопарк',
      category: 'attraction',
      icon: '🚀',
      lat: 51.0883541,
      lon: 71.4145878,
      description: 'Крупнейший технологический хаб Центральной Азии (Павильон C4.6 на территории EXPO).'
    },
    {
      id: 'bld_alem',
      poi_id: 'loc_alem_ai',
      name: 'Alem.ai',
      subtitle: 'Центр искусственного интеллекта',
      category: 'attraction',
      icon: '💡',
      lat: 51.0892381,
      lon: 71.4162196,
      description: 'Казахстанский научно-образовательный центр искусственного интеллекта (Павильон B1 на территории EXPO).'
    },
    {
      id: 'bld_aifc',
      poi_id: 'loc_aifc',
      name: 'МФЦА / AIFC',
      subtitle: 'Международный финансовый центр',
      category: 'attraction',
      icon: '🏛️',
      lat: 51.0880703,
      lon: 71.4168534,
      description: 'Международный финансовый центр «Астана» (Павильон C3.3, проспект Мәңгілік Ел 55/18).'
    },
    {
      id: 'bld_aitu',
      poi_id: 'loc_aitu',
      name: 'Astana IT University',
      subtitle: 'Университет AITU',
      category: 'attraction',
      icon: '🎓',
      lat: 51.0908607,
      lon: 71.4184149,
      description: 'Ведущий технологический университет Казахстана (Павильон C1 на территории EXPO).'
    },
    {
      id: 'bld_botanic',
      poi_id: 'osm_way_1196402246',
      name: 'Ботанический сад',
      subtitle: 'Главный парк столицы',
      category: 'park',
      icon: '🌿',
      lat: 51.1061652,
      lon: 71.4165705,
      description: 'Крупнейший ботанический сад Астаны с оранжереей, озером, велосипедными дорожками и прогулочными мостами.'
    },
    {
      id: 'bld_park25',
      poi_id: 'osm_way_1460763574',
      name: '25-ти летие Независимости',
      subtitle: 'Парк у EXPO',
      category: 'park',
      icon: '🌳',
      lat: 51.0934524,
      lon: 71.4175645,
      description: 'Парковая зона и прогулочная аллея рядом с выставочным комплексом EXPO.'
    },
    {
      id: 'bld_arch',
      poi_id: 'osm_way_549307755',
      name: 'Триумфальная арка',
      subtitle: 'Мәңгілік Ел',
      category: 'attraction',
      icon: '🏛️',
      lat: 51.1043034,
      lon: 71.4300836,
      description: 'Архитектурный монумент и смотровая площадка на главном проспекте столицы Мәңгілік Ел.'
    }
  ];

  let landmarksLayer = null;

  function updateAllMarkersZoomVisibility() {
    if (!leafletMap || typeof leafletMap.getZoom !== 'function') return;
    const zoom = leafletMap.getZoom();
    const isLandmarkVisible = zoom >= 14.0;
    const isPoiVisible = zoom >= 14.2;

    const landmarkWraps = document.querySelectorAll('.landmark-pill-marker-wrap');
    landmarkWraps.forEach((el) => {
      el.classList.toggle('landmark-fade-out', !isLandmarkVisible);
    });

    const poiWraps = document.querySelectorAll('.subtle-map-poi-marker');
    poiWraps.forEach((el) => {
      el.classList.toggle('poi-fade-out', !isPoiVisible);
    });
  }

  function updateLandmarksZoomVisibility() {
    updateAllMarkersZoomVisibility();
  }

  function renderLandmarkButtons() {
    if (!leafletMap) return;
    if (!landmarksLayer) {
      landmarksLayer = L.layerGroup().addTo(leafletMap);
    } else {
      landmarksLayer.clearLayers();
    }

    VERIFIED_BUILDINGS.forEach((bld) => {
      poiCatalog.set(bld.poi_id, bld);
      poiCatalog.set(bld.id, bld);

      const landmarkIcon = L.divIcon({
        className: 'landmark-pill-marker-wrap',
        html: `
          <button type="button" class="landmark-pill-btn" title="${escapeHtml(bld.name)} · ${escapeHtml(bld.subtitle)}">
            <span class="landmark-pill-icon">${bld.icon}</span>
            <span class="landmark-pill-title">${escapeHtml(bld.name)}</span>
          </button>
        `,
        iconSize: [140, 32],
        iconAnchor: [70, 16]
      });

      const m = L.marker([bld.lat, bld.lon], { icon: landmarkIcon, zIndexOffset: 700 }).addTo(landmarksLayer);
      if (typeof m.on === 'function') {
        m.on('click', () => {
          if (leafletMap && typeof leafletMap.flyTo === 'function') {
            leafletMap.flyTo([bld.lat, bld.lon], 16, { duration: 0.6 });
          }
          openPoiDrawer(bld);
        });
      }
    });

    if (typeof setTimeout === 'function') {
      setTimeout(updateLandmarksZoomVisibility, 60);
    }
  }

  // --- Render All Verified OSM POIs as Interactive Badges ---
  let allPoisLayer = null;
  async function loadAndRenderAllPoisOnMap() {
    try {
      renderLandmarkButtons();
      let data;
      if (isMockMode) {
        await ensureMockData();
        data = { pois: mockData.pois || [] };
      } else {
        const resp = await fetch('/api/pois', { cache: 'no-store' });
        if (!resp.ok) return;
        data = await resp.json();
      }
      const pois = data.pois || [];
      pois.forEach(poi => poiCatalog.set(poi.poi_id, poi));
      if (!leafletMap) return;

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
        memorial: '🕊️',
        artwork: '🎨',
        museum: '🖼️',
        mall: '🛍️',
        playground: '🛝',
        leisure: '⚽',
        amenity: '📍'
      };

      pois.forEach(p => {
        if (!Number.isFinite(p.lat) || !Number.isFinite(p.lon)) return;
        const iconEmoji = categoryIcons[p.category] || '📍';
        const markerIcon = L.divIcon({
          className: 'subtle-map-poi-marker',
          html: `<div class="subtle-poi-dot" title="${escapeHtml(p.name)}">${iconEmoji}</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        const m = L.marker([p.lat, p.lon], { icon: markerIcon }).addTo(allPoisLayer);
        m.bindTooltip(escapeHtml(p.name), { direction: 'top', offset: [0, -12] });
        m.on('click', () => {
          openPoiDrawer(p);
        });
      });

      if (typeof setTimeout === 'function') {
        setTimeout(updateAllMarkersZoomVisibility, 60);
      }
    } catch (_) {}
  }

  // --- Fullscreen Leaflet Map Initialization ---
  function initMap() {
    if (typeof window.L === 'undefined') {
      console.warn('[Telegis] Leaflet library not detected.');
      return;
    }

    try {
      const defaultCenter = [51.0890897, 71.4073303]; // Real Mega Silk Way (Main Entrance)
      leafletMap = L.map('osmMap', {
        center: defaultCenter,
        zoom: 15,
        zoomControl: false,
        attributionControl: true
      });
      if (typeof window !== 'undefined') {
        window.leafletMap = leafletMap;
      }

      leafletMap.attributionControl.setPrefix(false);
      leafletMap.attributionControl.addAttribution(
        '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors · ODbL</a>'
      );
      const backgroundTiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        referrerPolicy: 'strict-origin-when-cross-origin'
      });
      let backgroundUnavailable = false;
      backgroundTiles.on('tileerror', event => {
        if (event.tile) event.tile.style.visibility = 'hidden';
        if (backgroundUnavailable) return;
        backgroundUnavailable = true;
        // Remove the failing raster layer once, without retry loops or requests
        // to a second provider. Local POIs and computed paths remain usable.
        setTimeout(() => leafletMap.removeLayer(backgroundTiles), 0);
        showMapBackgroundStatus('Фон карты недоступен. Точки и рассчитанные маршруты работают; улицы на фоне не показаны.');
        if (!isMockMode) loadWalkingBackground();
      });
      backgroundTiles.addTo(leafletMap);

      poiMarkersLayer = L.layerGroup().addTo(leafletMap);
      renderLandmarkButtons();

      if (typeof leafletMap.on === 'function') {
        leafletMap.on('zoom', updateAllMarkersZoomVisibility);
        leafletMap.on('zoomend', updateAllMarkersZoomVisibility);
      }

      // Enable interactive map clicking
      leafletMap.on('click', (e) => {
        closePoiDrawer();
        handleMapClick(e.latlng.lat, e.latlng.lng);
      });

      updateStartMarker(defaultCenter[0], defaultCenter[1], 'Mega Silk Way');
      updateReachRadius(60);
    } catch (err) {
      console.error('[Telegis] Map init error:', err);
    }
  }

  function showMapBackgroundStatus(text) {
    let notice = document.getElementById('mapBackgroundStatus');
    if (!notice) {
      notice = document.createElement('div');
      notice.id = 'mapBackgroundStatus';
      notice.className = 'map-background-status';
      notice.setAttribute('role', 'status');
      document.body.appendChild(notice);
    }
    notice.textContent = text;
  }

  async function loadWalkingBackground() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch('/api/walking-map.geojson', {
        cache: 'no-store', signal: controller.signal
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const geometry = await response.json();
      if (geometry.type !== 'FeatureCollection' || !geometry.features?.length) {
        throw new Error('Walking geometry unavailable');
      }
      const pane = leafletMap.createPane('walkingBackground');
      pane.style.zIndex = 250;
      pane.style.pointerEvents = 'none';
      L.geoJSON(geometry, {
        pane: 'walkingBackground',
        renderer: L.canvas({ pane: 'walkingBackground' }),
        interactive: false,
        style: { color: '#94a3b8', weight: 1.4, opacity: 0.75 }
      }).addTo(leafletMap);
      showMapBackgroundStatus('Локальная схема дорожек OSM. Фоновая карта недоступна; показан сохранённый граф, точки и маршруты.');
    } catch (_) {
      // Keep the explicit plain-background notice. A missing graph is never
      // replaced by imaginary streets or an unlabelled external provider.
    } finally {
      clearTimeout(timeout);
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
          <div class="svg-pin-wrapper" id="pin_${escapeHtml(poi.poi_id)}">
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
          <div style="color: #64748b; font-size: 12px; margin-bottom: 6px;">${categoryEmoji} ${escapeHtml(categoryName(poi.category))} • ~${poi.distance_m ?? 0} м по прямой</div>
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
      leafletMap.fitBounds(bounds, mapViewPadding());
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
          <div class="svg-pin-wrapper itinerary-pin-wrapper" id="pin_${escapeHtml(stop.poi_id)}">
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
          <div style="color: #0369a1; font-weight: 600; font-size: 11px; margin-bottom: 4px;">От старта: +${stop.arrival_minutes_estimate} мин • На месте: ${stop.visit_minutes_estimate} мин</div>
          <div style="color: #64748b; font-size: 12px;">${escapeHtml(stop.activity || '')}</div>
        </div>
      `;
      marker.bindPopup(popupHtml);
      marker.on('click', () => openPoiDrawer(stop));
      currentMarkers.set(stop.poi_id, marker);
      bounds.extend([stop.lat, stop.lon]);
    });

    if (allLatLngs.length > 0) {
      bounds.extend(routePolyline.getBounds());
    }

    try {
      leafletMap.fitBounds(bounds, mapViewPadding());
    } catch (_) {}
  }

  function mapViewPadding() {
    const size = leafletMap?.getSize?.() || { x: window.innerWidth || 1024, y: window.innerHeight || 768 };
    const rect = gisSidebar?.getBoundingClientRect();
    const collapsed = gisSidebar?.classList.contains('collapsed');
    if (window.matchMedia?.('(max-width: 768px)').matches) {
      const panelHeight = collapsed ? 64 : rect?.height || size.y * 0.6;
      return {
        paddingTopLeft: [20, 80],
        paddingBottomRight: [40, Math.min(panelHeight + 20, Math.max(20, size.y - 120))],
        maxZoom: 16, animate: true
      };
    }
    const left = collapsed ? 20 : (rect?.width || 440) + 32;
    return {
      paddingTopLeft: [Math.min(left, Math.max(20, size.x - 180)), 70],
      paddingBottomRight: [60, 30],
      maxZoom: 16, animate: true
    };
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

    // Climate Shield Checkbox
    if (climateShieldCheck) {
      climateShieldCheck.addEventListener('change', () => {
        if (climateShieldCheck.checked) {
          showMapBackgroundStatus('💨 Климатический щит: приоритет крытым хабам (Mega Silk Way, коворкинги EXPO).');
          if (locationSelect) {
            const megaOpt = Array.from(locationSelect.options).find(o => o.value.includes('Mega') || o.text.includes('Mega'));
            if (megaOpt) {
              locationSelect.value = megaOpt.value;
              locationSelect.dispatchEvent(new Event('change'));
            }
          }
        }
      });
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

    document.querySelectorAll('input[name="category"]').forEach(input => input.addEventListener('change', invalidateSearch));
    if (queryInput) queryInput.addEventListener('input', invalidateSearch);

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
        if (window.matchMedia?.('(max-width: 768px)').matches) gisSidebar.scrollTop = 0;
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
        gisSidebar.scrollTop = 0;
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
        invalidateSearch();
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
        invalidateSearch();
        const fillText = chip.getAttribute('data-fill');
        if (queryInput) {
          queryInput.value = fillText;
          queryInput.focus();
        }
        // Auto-adapt minutes and category for common scenarios
        if (['С ребёнком', 'Я турист', 'Ночью', 'панорамный вид', 'тихое место'].includes(fillText)) {
          const radioWalk = document.querySelector('input[name="category"][value="walk"]');
          if (radioWalk) radioWalk.checked = true;
          const curMins = getSelectedMinutes();
          if (curMins < 60) {
            selectMinutes(60);
          }
        } else if (fillText === 'кофе навынос') {
          const radioCafe = document.querySelector('input[name="category"][value="cafe"]');
          if (radioCafe) radioCafe.checked = true;
        }
      });
    });

    // Keyboard shortcuts: Escape closes drawer and telemetry modal
    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          closePoiDrawer();
          closeTelemetryModal();
        }
      });
    }

    // Preset buttons
    presetButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        setAppMode('places');
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
          handleMapClick(currentDrawerPoi.lat, currentDrawerPoi.lon, currentDrawerPoi.name);
          showMapToast(`📍 Стартовая точка: ${currentDrawerPoi.name}`);
          closePoiDrawer();
        }
      });
    }

    const drawerRouteBtn = document.getElementById('drawerRouteBtn');
    if (drawerRouteBtn) {
      drawerRouteBtn.addEventListener('click', () => {
        if (currentDrawerPoi) {
          showMapToast(`📍 Ищем рекомендации по запросу «${currentDrawerPoi.name}»`);
          setAppMode('places');
          const category = currentDrawerPoi.category === 'cafe' ? 'cafe' : 'walk';
          const radio = document.querySelector(`input[name="category"][value="${category}"]`);
          if (radio) radio.checked = true;
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
    invalidateSearch();
    appMode = mode;
    tabPlaces.classList.toggle('active', mode === 'places');
    tabItinerary.classList.toggle('active', mode === 'itinerary');

    if (btnText) {
      btnText.textContent = mode === 'itinerary' ? t('btn_build_route') : t('btn_find');
    }

    renderTimeSelector();
    updateCategoryLabels();
    setUIState('initial');
    clearRoutePolyline();
    if (poiMarkersLayer) poiMarkersLayer.clearLayers();
    if (window.matchMedia?.('(max-width: 768px)').matches && gisSidebar) gisSidebar.scrollTop = 0;
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
      errOpt.textContent = 'Локации недоступны — проверьте сервер или выберите точку на карте';
      locationSelect.appendChild(errOpt);
    }
  }

  const VERIFIED_EXPO_ANCHORS = [
    { id: 'osm_way_499328514', name: 'Mega Silk Way', lat: 51.0890897, lon: 71.4073303 },
    { id: 'loc_alem_ai', name: 'Alem.ai (Павильон B1)', lat: 51.0892381, lon: 71.4162196 },
    { id: 'loc_astana_hub', name: 'Astana Hub (Павильон C4.6)', lat: 51.0883541, lon: 71.4145878 },
    { id: 'loc_aifc', name: 'МФЦА / AIFC (Павильон C3.3)', lat: 51.0880703, lon: 71.4168534 },
    { id: 'loc_aitu', name: 'Astana IT University (AITU)', lat: 51.0906792, lon: 71.4181709 },
    { id: 'osm_way_1460763574', name: '25-ти летие Независимости', lat: 51.0934524, lon: 71.4175645 }
  ];

  function populateLocationsSelect(locations) {
    locationSelect.innerHTML = '';

    const list = Array.isArray(locations) ? [...locations] : [];
    VERIFIED_EXPO_ANCHORS.forEach(anchor => {
      const exists = list.some(l => l.id === anchor.id || (Math.abs(l.lat - anchor.lat) < 0.0005 && Math.abs(l.lon - anchor.lon) < 0.0005));
      if (!exists) {
        list.push(anchor);
      }
    });

    if (list.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.disabled = true;
      opt.selected = true;
      opt.textContent = 'Локации недоступны';
      locationSelect.appendChild(opt);
      return;
    }

    list.forEach((loc, index) => {
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
    if (isMockMode) {
      cachedSystemMeta = null;
      cachedHealth = null;
      systemStatusLoaded = true;
      updateSystemStatusText();
      return;
    }
    const responses = await Promise.allSettled(['/api/meta', '/api/health'].map(async path => {
      const response = await fetch(path, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }));
    cachedSystemMeta = responses[0].status === 'fulfilled' ? responses[0].value : null;
    cachedHealth = responses[1].status === 'fulfilled' ? responses[1].value : null;
    systemStatusLoaded = true;
    updateSystemStatusText();
  }

  function modelStatus() {
    if (isMockMode) return 'Тестовый режим';
    if (!systemStatusLoaded) return 'Проверяем состояние API…';
    if (!cachedHealth) return 'Статус API недоступен';
    if (!cachedHealth.llm_configured) return 'Локальный подбор · LLM не настроена';
    if (cachedHealth.llm_last_status === 'ok') return 'Последний вызов LLM: успешно';
    if (cachedHealth.llm_last_status === 'not_checked') return 'LLM настроена, вызов ещё не проверен';
    return `LLM: ${cachedHealth.llm_last_status || 'статус неизвестен'} · доступен локальный подбор`;
  }

  function updateSystemStatusText() {
    if (!statusSummaryText) return;
    const m = cachedSystemMeta;
    statusSummaryText.textContent = m
      ? `Сеть: ${m.walking_network?.node_count?.toLocaleString() ?? '—'} узлов OSM • ${m.poi_count ?? '—'} POI • ${modelStatus()}`
      : modelStatus();
  }

  function openTelemetryModal() {
    if (!telemetryModal || !telemetryModalBody) return;
    const m = cachedSystemMeta || {};
    const number = value => Number.isFinite(value) ? value.toLocaleString() : '—';
    telemetryModalBody.innerHTML = `
      <div>
        <div class="telemetry-section-title">🗺️ Пешеходная сеть OpenStreetMap</div>
        <div class="telemetry-grid">
          <div class="telemetry-card"><span class="telemetry-val">${number(m.walking_network?.node_count)}</span><span class="telemetry-lbl">Вершин графа</span></div>
          <div class="telemetry-card"><span class="telemetry-val">${number(m.walking_network?.directed_edge_count)}</span><span class="telemetry-lbl">Направленных рёбер</span></div>
        </div>
      </div>
      <div>
        <div class="telemetry-section-title">📍 Данные сохранённого снимка</div>
        <div class="telemetry-grid">
          <div class="telemetry-card"><span class="telemetry-val">${number(m.poi_count)}</span><span class="telemetry-lbl">Объектов</span></div>
          <div class="telemetry-card"><span class="telemetry-val">${number(m.data_quality?.attributed_fact_count)}</span><span class="telemetry-lbl">Сведений (${number(m.data_quality?.official_fact_count)} официальных)</span></div>
        </div>
      </div>
      <div>
        <div class="telemetry-section-title">⚡ Теги удобств в OSM</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
          <span class="feature-pill">🔌 Розетки: ${number(m.data_quality?.confirmed_features?.socket)}</span>
          <span class="feature-pill">📶 Wi-Fi: ${number(m.data_quality?.confirmed_features?.wifi)}</span>
          <span class="feature-pill">♿ Доступность: ${number(m.data_quality?.confirmed_features?.wheelchair)}</span>
          <span class="feature-pill">🌿 Тишина: ${number(m.data_quality?.confirmed_features?.quiet)}</span>
        </div>
      </div>
      <div>
        <div class="telemetry-section-title">🔒 Подбор и приватность</div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">Состояние LLM</span><span class="telemetry-info-val">${escapeHtml(modelStatus())}</span></div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">Источники</span><span class="telemetry-info-val">OpenStreetMap и официальные страницы; актуальность не гарантируется</span></div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">Координаты</span><span class="telemetry-info-val">Бэкенд не сохраняет GPS; тайлы OSM загружаются браузером с внешнего сервера</span></div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">Лицензия</span><span class="telemetry-info-val">© OpenStreetMap contributors · ODbL 1.0</span></div>
      </div>`;
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
        invalidateSearch();
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
    const option = locationSelect.selectedOptions[0];
    if (!option?.dataset.lat || !option?.dataset.lon) {
      handleSearchError('Выберите стартовую точку из списка, на карте или через GPS.');
      return;
    }
    const category = document.querySelector('input[name="category"]:checked')?.value || 'walk';
    const common = {
      query: queryInput.value.trim() || (appMode === 'itinerary' ? 'Хочу погулять' : category === 'cafe' ? 'Кофе' : 'Прогулка'),
      lat: Number(option.dataset.lat),
      lon: Number(option.dataset.lon),
      available_minutes: getSelectedMinutes()
    };
    const payload = appMode === 'itinerary'
      ? { ...common, include_coffee: category === 'cafe' }
      : { ...common, category };
    lastRequestPayload = payload;
    executeSearch(payload);
  }

  function invalidateSearch() {
    if (activeAbortController) activeAbortController.abort();
    activeAbortController = null;
    lastRequestPayload = null;
    setSubmitLoading(false);
    clearRoutePolyline();
    if (poiMarkersLayer) poiMarkersLayer.clearLayers();
    if (cardsGrid) cardsGrid.innerHTML = '';
    if (itineraryView) itineraryView.innerHTML = '';
    if (fallbackNotice) fallbackNotice.classList.add('hidden');
    if (usedContextTag) usedContextTag.classList.add('hidden');
    if (resultsCountBadge) resultsCountBadge.classList.add('hidden');
    const advice = document.getElementById('emptyAdviceContainer');
    if (advice) advice.replaceChildren();
    setUIState('initial');
  }

  function updateCategoryLabels() {
    const walk = document.querySelector('[data-i18n="cat_walk"]');
    const cafe = document.querySelector('[data-i18n="cat_cafe"]');
    if (walk) walk.textContent = appMode === 'itinerary' ? 'Без кофе' : t('cat_walk');
    if (cafe) cafe.textContent = appMode === 'itinerary' ? 'С остановкой на кофе' : t('cat_cafe');
  }

  function selectMinutes(value) {
    let radio = document.querySelector(`input[name="availableMinutes"][value="${value}"]`);
    if (!radio) {
      const label = document.createElement('label');
      label.className = 'time-chip';
      radio = document.createElement('input');
      radio.type = 'radio'; radio.name = 'availableMinutes'; radio.value = value;
      radio.addEventListener('change', () => { invalidateSearch(); updateReachRadius(value); });
      const text = document.createElement('span');
      text.className = 'time-chip-btn'; text.textContent = `${value} мин`;
      label.append(radio, text);
      timeSelector.appendChild(label);
    }
    radio.checked = true;
    updateReachRadius(value);
  }

  async function mockResponse(payload, mode) {
    await ensureMockData();
    const matches = (mockData.scenarios || []).find(item =>
      item.mode === mode && Object.entries(item.request).every(([key, value]) => payload[key] === value));
    if (matches) return structuredClone(matches.response);
    const used_context = { ...payload, effective_minutes: payload.available_minutes, required_features: [] };
    const message = 'Тестовый режим: для этих параметров нет записанного примера. Отключите ?mock=1 для настоящего расчёта. Записанные ответы не пересчитываются и не выдают выдуманные маршруты.';
    return mode === 'itinerary'
      ? { status: 'no_match', mode: 'mock', message, used_context, stops: [], legs: [] }
      : { mode: 'mock', message, used_context, recommendations: [] };
  }

  async function executeSearch(payload) {
    if (activeAbortController) activeAbortController.abort();
    const controller = new AbortController();
    const mode = appMode;
    activeAbortController = controller;
    if (fallbackNotice) fallbackNotice.classList.add('hidden');
    if (resultsCountBadge) resultsCountBadge.classList.add('hidden');
    if (usedContextTag) usedContextTag.classList.add('hidden');
    const advice = document.getElementById('emptyAdviceContainer');
    if (advice) advice.replaceChildren();
    clearRoutePolyline();
    if (poiMarkersLayer) poiMarkersLayer.clearLayers();
    setUIState('loading');
    setSubmitLoading(true);
    try {
      let data;
      if (isMockMode) {
        data = await mockResponse(payload, mode);
      } else {
        const response = await fetch(mode === 'itinerary' ? '/api/itinerary' : '/api/recommend', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload), signal: controller.signal, cache: 'no-store'
        });
        if (!response.ok) {
          let message = `Ошибка API: HTTP ${response.status}`;
          try {
            const error = await response.json();
            if (error.detail) message = Array.isArray(error.detail) ? error.detail.map(item => item.msg).join('; ') : String(error.detail);
          } catch (_) {}
          throw new Error(message);
        }
        data = await response.json();
      }
      if (controller.signal.aborted || activeAbortController !== controller || appMode !== mode) return;
      if (mode === 'itinerary') handleItinerarySuccess(data);
      else handleSearchSuccess(data);
      if (!isMockMode) loadSystemMeta();
    } catch (error) {
      if (controller.signal.aborted || activeAbortController !== controller || error.name === 'AbortError') return;
      const networkFailure = error instanceof TypeError ||
        /failed to fetch|networkerror|network request failed|load failed/i.test(error.message || '');
      handleSearchError(networkFailure ? t('connection_error') : error.message || t('connection_error'));
    } finally {
      if (activeAbortController === controller) {
        activeAbortController = null;
        setSubmitLoading(false);
      }
    }
  }

  // --- Itinerary Mode Response Handler ---
  function handleItinerarySuccess(data) {
    renderUsedContext(data.used_context);
    if (fallbackNotice) fallbackNotice.classList.add('hidden');
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
          selectMinutes(data.suggested_minimum_minutes);
          if (data.used_context?.effective_minutes < data.used_context?.available_minutes ||
              /\d+\s*(?:мин|min|час|hour|ч\b)/i.test(queryInput.value)) {
            const note = document.createElement('p');
            note.className = 'warning-item';
            note.textContent = 'Время изменено в переключателе. В тексте запроса остаётся более короткий лимит — измените его вручную и нажмите «Построить маршрут». Текстовые ограничения сохранены.';
            emptyAdviceContainer.appendChild(note);
            queryInput.focus();
            return;
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
    badge.textContent = isMockMode ? 'Записанный тестовый пример' : 'Локальный граф OSM';
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
    const contextLine = document.createElement('p');
    contextLine.className = 'itin-why';
    contextLine.textContent = `Бюджет: ${data.used_context?.effective_minutes ?? data.used_context?.available_minutes ?? '—'} мин. Остаток: ${data.remaining_minutes ?? '—'} мин. Запас уже включён в итог. Все времена ниже — от момента старта.`;
    summaryCard.appendChild(contextLine);
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
      stTime.textContent = `+${stop.arrival_minutes_estimate}–${depTime} мин от старта`;

      stHead.appendChild(stName);
      stHead.appendChild(stTime);
      stopCard.appendChild(stHead);

      if (stop.why) {
        const why = document.createElement('p');
        why.className = 'card-why-text';
        why.textContent = `${t('why_label')} ${stop.why}`;
        stopCard.appendChild(why);
      }
      if (stop.activity) {
        const actP = document.createElement('div');
        actP.className = 'itin-stop-activity';
        actP.textContent = `💡 Идея занятия: ${stop.activity}`;
        stopCard.appendChild(actP);
      }

      (stop.evidence || []).forEach(fact => {
        const line = document.createElement('p');
        line.className = 'card-evidence-box';
        line.textContent = `${fact.kind === 'official' ? 'Официальный источник' : 'OSM'}: ${fact.text}`;
        appendSource(line, fact.source_url, `Источник · ${formatDate(fact.collected_at)}`);
        stopCard.appendChild(line);
      });
      const hours = document.createElement('p');
      hours.className = 'hours-badge';
      hours.textContent = stop.opening_hours ? `Часы по источнику: ${stop.opening_hours}` : t('unconfirmed_hours');
      stopCard.appendChild(hours);
      appendWarnings(stopCard, stop.warnings);
      appendSource(stopCard, stop.source_url, `POI в OSM · ${formatDate(stop.collected_at)}`);
      timeline.appendChild(stopCard);
    });

    // Return to start item
    const finishCard = document.createElement('div');
    finishCard.className = 'itin-stop-card';
    finishCard.style.borderColor = '#34d399';
    finishCard.innerHTML = `
      <div class="itin-stop-header">
        <div class="itin-stop-name" style="color: #059669;">🏁 ${t('finish_point')}</div>
        <div class="itin-stop-time">~${data.walking_minutes_estimate + data.visit_minutes_estimate} мин + ${data.reserve_minutes} мин запаса</div>
      </div>
      <div class="itin-stop-activity">План возвращения в исходную точку. Время приблизительное; проверьте доступность проходов на месте.</div>
    `;
    timeline.appendChild(finishCard);

    itineraryView.appendChild(timeline);

    if (data.warnings && data.warnings.length > 0) {
      const warnBox = document.createElement('div');
      warnBox.className = 'itin-warnings-container';
      warnBox.style.marginTop = '0.75rem';
      appendWarnings(warnBox, data.warnings);
      itineraryView.appendChild(warnBox);
    }
  }

  function appendWarnings(container, warnings) {
    (warnings || []).forEach(text => {
      const item = document.createElement('div');
      item.className = 'warning-item';
      item.textContent = `⚠️ ${text}`;
      container.appendChild(item);
    });
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
      if (isMockMode) {
        fallbackNotice.className = 'fallback-banner';
        fallbackNotice.innerHTML = '<span class="banner-icon">ℹ️</span><div class="banner-text"><strong>Тестовый режим:</strong> Live API отключён.</div>';
      } else if (data.mode === 'rag') {
        fallbackNotice.className = 'ai-active-banner';
        fallbackNotice.innerHTML = '<span class="banner-icon">✨</span><div class="banner-text"><strong>RAG-генерация:</strong> модель подобрала места по базе POI с проверкой времени.</div>';
      } else {
        fallbackNotice.className = 'fallback-banner';
        fallbackNotice.innerHTML = '<span class="banner-icon">⚡</span><div class="banner-text"><strong>Локальный расчёт:</strong> проверенная база POI и граф дорог OSM без вызова LLM.</div>';
      }
      fallbackNotice.classList.remove('hidden');
    }

    if (recommendations.length === 0) {
      if (cardsGrid) cardsGrid.innerHTML = '';
      if (emptyReason) emptyReason.textContent = data.message || t('empty_text');
      if (poiMarkersLayer) poiMarkersLayer.clearLayers();
      clearRoutePolyline();
      const emptyAdviceContainer = document.getElementById('emptyAdviceContainer');
      if (emptyAdviceContainer) {
        emptyAdviceContainer.innerHTML = '';
        const curMins = getSelectedMinutes();
        if (curMins < 60) {
          const sugBtn = document.createElement('button');
          sugBtn.className = 'gis-btn-secondary retry-action-btn';
          sugBtn.style.marginTop = '0.75rem';
          sugBtn.textContent = '⏱️ Увеличить время до 60 мин и найти';
          sugBtn.addEventListener('click', () => {
            selectMinutes(60);
            if (recommendForm) recommendForm.dispatchEvent(new Event('submit', { cancelable: true }));
          });
          emptyAdviceContainer.appendChild(sugBtn);
        }
      }
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
    const minutes = context.effective_minutes ?? context.available_minutes;
    const coords = Number.isFinite(context.lat) && Number.isFinite(context.lon) ? `${context.lat.toFixed(4)}, ${context.lon.toFixed(4)}` : 'старт не указан';

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
      categoryBadge.textContent = categoryName(poi.category);
      categoryBadge.dataset.poiCategory = poi.category || '';

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
      mDistanceLabel.textContent = poi.travel_basis === 'osm_walking_graph' && Number.isFinite(poi.route_distance_m) ? 'По графу OSM:' : t('straight_dist');
      const mDistanceVal = document.createElement('span');
      mDistanceVal.className = 'metric-value';
      const displayDist = poi.route_distance_m ?? poi.distance_m ?? 0;
      mDistanceVal.textContent = `${displayDist} м`;
      mDistance.appendChild(mDistanceLabel);
      mDistance.appendChild(mDistanceVal);

      if (poi.travel_basis === 'osm_walking_graph' || poi.route_distance_m) {
        const basisBadge = document.createElement('span');
        basisBadge.className = 'basis-badge';
        basisBadge.textContent = t('basis_graph');
        basisBadge.title = 'Маршрут по сохранённому графу OSM с приблизительными подходами к точкам; доступность проходов не проверена в реальном времени';
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
      mWalkVal.textContent = `~${poi.walk_minutes_estimate ?? 0} мин`;
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
      const duration = document.createElement('p');
      duration.className = 'card-timing-note';
      duration.textContent = `На месте: ${poi.visit_minutes_estimate} мин. Возврат включён в итог. Свободно в бюджете: ${poi.time_margin_minutes ?? '—'} мин.`;
      card.appendChild(duration);

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
          evTitle.textContent = ev.kind === 'official' ? t('verified_fact') : 'По данным OpenStreetMap';
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
          evBadge.textContent = `${t('evidence_sha')} · ${formatDate(ev.collected_at)}${ev.published_at ? ` · публикация: ${formatDate(ev.published_at)}` : ''}`;
          evMeta.appendChild(evBadge);

          if (safeHttpUrl(ev.source_url)) {
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
        hoursBadge.textContent = `🕒 По источнику: ${poi.opening_hours} · уточните перед визитом`;
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
    if (state !== 'initial' && window.matchMedia?.('(max-width: 768px)').matches && gisSidebar) {
      const content = document.getElementById('sidebarContent');
      if (content) {
        gisSidebar.classList.remove('collapsed');
        gisSidebar.scrollTo({
          top: Math.max(0, content.offsetTop - (sheetHandle?.offsetHeight || 0)),
          behavior: 'smooth'
        });
      }
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

  document.addEventListener('DOMContentLoaded', init);
})();
