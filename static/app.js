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
      evidence_sha: 'Сведения источника',
      why_ai_chose: 'ВЫБОР ИИ: ПОЧЕМУ ИМЕННО ЭТО МЕСТО',
      btn_route: 'Маршрут',
      route_to: 'Маршрут к:',
      drawer_build_route: 'Построить пеший маршрут',
      drawer_set_start: 'Начать прогулку отсюда',
      drawer_features_heading: 'Удобства & Параметры',
      drawer_facts_heading: '🏛️ Источники и ограничения',
      close_route: 'Сбросить маршрут',
      climate_label: '💨 Климат Астаны: защита от ветра и холода',
      heading_where: 'Куда хотите сходить?',
      my_location: 'Моё местоположение'
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
      init_text: 'Уақыт пен форматты таңдаңыз — Telegis сақталған OSM деректерінен 3 орынға дейін ұсынып, шектеулерді көрсетеді.',
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
      verified_fact: '🏛️ Ресми дереккөз бойынша',
      evidence_sha: 'Дереккөз мәліметі',
      why_ai_chose: 'ЖИ ТАҢДАУЫ: НЕГЕ БҰЛ ОРЫН ТАҢДАЛДЫ',
      btn_route: 'Бағыт',
      route_to: 'Бағыт:',
      drawer_build_route: 'Жаяу бағыт құру',
      drawer_set_start: 'Серуенді осы жерден бастау',
      drawer_features_heading: 'Қолайлылықтар мен сипаттамалар',
      drawer_facts_heading: '🏛️ Дереккөздер мен шектеулер',
      close_route: 'Бағытты жабу',
      climate_label: '💨 Астана климаты: жел мен суықтан қорғану',
      heading_where: 'Қайда барғыңыз келеді?',
      my_location: 'Менің орналасқан жерім'
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
      init_text: 'Select your time and category — Telegis suggests up to 3 places from saved OSM data and shows their limitations.',
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
      evidence_sha: 'Source-reported information',
      why_ai_chose: 'AI CHOICE: WHY THIS PLACE',
      btn_route: 'Directions',
      route_to: 'Route to:',
      drawer_build_route: 'Build walking route',
      drawer_set_start: 'Start walk from here',
      drawer_features_heading: 'Amenities & Features',
      drawer_facts_heading: '🏛️ Sources & Constraints',
      close_route: 'Clear route',
      climate_label: '💨 Astana Climate: wind & cold shield',
      heading_where: 'Where do you want to go?',
      my_location: 'My location'
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
  let initialized = false;
  let pointRouteController = null;
  let drawerFocusOrigin = null;
  let modalFocusOrigin = null;
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
  const timeRangeSlider = document.getElementById('timeRangeSlider');
  const timeSliderVal = document.getElementById('timeSliderVal');
  const routeSummaryBar = document.getElementById('routeSummaryBar');
  const routeBannerTitle = document.getElementById('routeBannerTitle');
  const routeBannerStats = document.getElementById('routeBannerStats');
  const closeRouteBannerBtn = document.getElementById('closeRouteBannerBtn');

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
    const initialParams = new URLSearchParams(window.location.search);
    setLanguage(initialParams.get('lang') || 'ru');
    initialized = true;
    initMap();
    bindEvents();
    loadAndRenderAllPoisOnMap();
    loadWeather();
    if (window.setInterval) window.setInterval(() => {
      if (!document.hidden) loadWeather();
    }, 300000);
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
        } else showMapToast(t('no_evidence'));
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
    const changed = currentLang !== lang;
    currentLang = lang;
    if (document.documentElement) document.documentElement.lang = lang === 'kz' ? 'kk' : lang;
    document.title = t('page_title');

    langButtons.forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
      btn.setAttribute('aria-pressed', String(btn.getAttribute('data-lang') === lang));
    });

    const dict = new Proxy(I18N[lang], { get: (_, key) => t(key) });

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

    const unit = lang === 'en' ? 'min' : 'мин';
    if (timeSliderVal && timeRangeSlider) {
      timeSliderVal.textContent = `${timeRangeSlider.value} ${unit}`;
    }

    document.querySelectorAll('.time-slider-ticks span').forEach(span => {
      const mins = span.dataset.mins;
      if (mins) span.textContent = `${mins} ${unit}`;
    });

    updateCategoryLabels();
    updateReachRadius();
    updateSystemStatusText();
    applyAccessibleLabels();
    renderWeather();
    document.querySelectorAll('.time-chip-btn').forEach(el => {
      el.textContent = el.textContent.replace(/(?:мин|min)$/, t('minute'));
    });
    if (changed && initialized) {
      invalidateSearch();
      closePoiDrawer();
      closeTelemetryModal();
      poiCatalog.clear();
      allPoisLayer?.clearLayers();
      landmarksLayer?.clearLayers();
      loadAndRenderAllPoisOnMap();
      setGeoStatus('', '');
      loadWeather();
    }
  }

  function t(key, values = {}) {
    const copy = window.TELEGIS_UI_COPY?.[key]?.[currentLang] ||
      (I18N[currentLang] && I18N[currentLang][key]) || (I18N.ru && I18N.ru[key]) || key;
    return copy.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`));
  }

  function categoryName(value) {
    const names = CATEGORY_NAMES[currentLang] || CATEGORY_NAMES.ru;
    return Object.prototype.hasOwnProperty.call(names, value) ? names[value] : names.unknown;
  }

  function httpErrorMessage(status) {
    const key = status === 503 ? 'service_unavailable' : status === 404 ? 'resource_missing'
      : status === 422 ? 'validation_error' : null;
    return key ? `${t(key)} (HTTP ${status})` : t('api_error', { status });
  }

  function applyAccessibleLabels() {
    const labels = {
      locationSelect: 'start_control', geoBtn: 'gps_button', queryInput: 'query_label',
      timeRangeSlider: 'time_label', toggleSidebarBtn: 'collapse', openSidebarBtn: 'expand',
      zoomInBtn: 'zoom_in', zoomOutBtn: 'zoom_out', mapCenterBtn: 'start_control',
      drawerCloseBtn: 'close', modalCloseBtn: 'close', closeRouteBannerBtn: 'close_route',
      systemStatusBtn: 'modal_audit_title', osmMap: 'map_label', gisSidebar: 'panel_label',
      itineraryView: 'route_ready_title', routeSummaryBar: 'route_to', sheetHandle: 'panel_label',
      submitBtn: appMode === 'itinerary' ? 'btn_build_route' : 'btn_find'
    };
    Object.entries(labels).forEach(([id, key]) => {
      const element = document.getElementById(id);
      element?.setAttribute('aria-label', t(key));
      if (element && !['osmMap', 'gisSidebar', 'itineraryView'].includes(id)) element.setAttribute('title', t(key));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => el.setAttribute('title', t(el.getAttribute('data-i18n-title'))));
    document.querySelector('.lang-switch-group')?.setAttribute('aria-label', t('language_label'));
    document.querySelector('.segmented-control')?.setAttribute('aria-label', t('format_label'));
    timeSelector?.setAttribute('aria-label', t('time_label'));
  }

  function setModalBackgroundInert(inert) {
    ['gisSidebar', 'osmMap', 'radiusBadge', 'routeSummaryBar', 'openSidebarBtn'].forEach(id => {
      const element = document.getElementById(id);
      if (inert) element?.setAttribute('inert', '');
      else element?.removeAttribute('inert');
    });
    document.querySelector('.floating-map-controls')?.toggleAttribute?.('inert', inert);
  }

  function trapModalFocus(event) {
    if (event.key !== 'Tab' || !telemetryModal || telemetryModal.classList.contains('hidden')) return;
    const items = Array.from(telemetryModal.querySelectorAll?.('button:not([disabled]), a[href], input:not([disabled]), [tabindex="0"]') || []);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  let weatherSnapshot = null;
  let weatherController = null;
  let weatherLoading = false;
  let lastClimateContext = null;

  async function loadWeather() {
    if (weatherController) weatherController.abort();
    const controller = new AbortController();
    weatherController = controller;
    weatherLoading = true;
    renderWeather();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      let data;
      if (isMockMode) {
        // Mock mode never silently calls a live endpoint.
        data = { status: 'demo', current: null, source: null, warnings: [] };
      } else {
        const demo = new URLSearchParams(window.location.search).get('weather_demo') === '1';
        const response = await fetch(`/api/weather?locale=${currentLang}${demo ? '&demo=true' : ''}`, {
          cache: 'no-store', signal: controller.signal, headers: { Accept: 'application/json' }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        data = await response.json();
      }
      if (weatherController !== controller || controller.signal.aborted) return;
      weatherSnapshot = data;
    } catch (_) {
      if (weatherController === controller) weatherSnapshot = { status: 'unavailable', current: null };
    } finally {
      clearTimeout(timeout);
      if (weatherController === controller) {
        weatherController = null; weatherLoading = false; renderWeather();
      }
    }
  }

  function formatTimestamp(value) {
    if (!value) return t('unknown');
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return t('unknown');
    return date.toLocaleString(currentLang === 'kz' ? 'kk-KZ' : currentLang === 'en' ? 'en-GB' : 'ru-RU', {
      timeZone: 'Asia/Almaty', day: '2-digit', month: '2-digit',
      hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
    });
  }

  function renderWeather() {
    const badge = document.getElementById('climateWeatherBadge');
    if (!badge) return;
    badge.replaceChildren();
    const snapshot = lastClimateContext?.weather || weatherSnapshot || {};
    const status = ['live', 'stale', 'unavailable', 'demo'].includes(snapshot.status) ? snapshot.status : 'unavailable';
    badge.dataset.weatherStatus = weatherLoading && !weatherSnapshot ? 'loading' : status;
    const line = text => {
      const row = document.createElement('div'); row.textContent = text; badge.appendChild(row); return row;
    };
    line(weatherLoading && !weatherSnapshot ? t('weather_loading') : t(`weather_${status}`));
    const current = snapshot.current;
    if (current && status !== 'unavailable') {
      const values = [];
      if (Number.isFinite(current.temperature_c)) values.push(`${current.temperature_c} °C`);
      if (Number.isFinite(current.apparent_temperature_c)) values.push(`${t('weather_feels')} ${current.apparent_temperature_c} °C`);
      if (Number.isFinite(current.wind_m_s)) values.push(`${t('weather_wind')} ${current.wind_m_s} ${t('wind_unit')}`);
      if (Number.isFinite(current.gust_m_s)) values.push(`${t('weather_gusts')} ${current.gust_m_s} ${t('wind_unit')}`);
      if (values.length) line(values.join(' · '));
    }
    if (snapshot.valid_at) line(`${t('weather_observed')}: ${formatTimestamp(snapshot.valid_at)}`);
    if (snapshot.fetched_at) line(`${t('weather_fetched')}: ${formatTimestamp(snapshot.fetched_at)}`);
    if (snapshot.source) {
      const source = line(`${t('source_label')}: ${snapshot.source}`);
      appendSource(source, snapshot.source_url, t('source'));
    }
    if (climateShieldCheck?.checked) line(t('climate_selected'));
    if (lastClimateContext?.requested && lastClimateContext.message) line(lastClimateContext.message);
    badge.classList.remove('hidden');
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
        if (timeRangeSlider) timeRangeSlider.value = mins;
        if (timeSliderVal) {
          const unit = currentLang === 'en' ? 'min' : (currentLang === 'kz' ? 'мин' : 'мин');
          timeSliderVal.textContent = `${mins} ${unit}`;
        }
        updateReachRadius(mins);
      });

      const span = document.createElement('span');
      span.className = 'time-chip-btn';
      span.textContent = currentLang === 'kz' ? `${mins} мин` : (currentLang === 'en' ? `${mins} min` : `${mins} мин`);

      label.appendChild(input);
      label.appendChild(span);
      timeSelector.appendChild(label);
    });

    if (timeRangeSlider) {
      timeRangeSlider.value = defaultVal;
    }
    if (timeSliderVal) {
      const unit = currentLang === 'en' ? 'min' : (currentLang === 'kz' ? 'мин' : 'мин');
      timeSliderVal.textContent = `${defaultVal} ${unit}`;
    }

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
    field('drawerDistBadge', Number.isFinite(poi.distance_m) ? `${poi.distance_m} ${t('meter')} ${t('straight_short')}` : t('distance_unknown'));
    field('drawerTitle', poi.name || categoryName('unknown'));
    const street = poi.tags?.['addr:street'];
    field('drawerAddress', street ? `📍 ${street} ${poi.tags['addr:housenumber'] || ''}` : t('no_address'));

    // A stock illustration must never be presented as a photograph of this POI.
    const img = document.getElementById('drawerHeroImg');
    if (img) {
      img.removeAttribute('src');
      img.alt = t('no_photo');
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
    field('drawerGalleryTag', `📍 ${t('no_photo')}`);

    // Keep the illustration placeholder until a canonical photograph is sourced.
    const features = document.getElementById('drawerFeaturesGrid');
    if (features) {
      features.replaceChildren();
      const f = poi.confirmed_features || {};
      const feature = (key, label) => `${label}: ${f[key] === true ? t('osm_yes') : f[key] === false ? t('osm_no') : t('no_evidence')}`;
      [
        poi.opening_hours ? `🕒 ${t('hours_source', { hours: poi.opening_hours })}` : t('unconfirmed_hours'),
        feature('wifi', '📶 Wi-Fi'), feature('socket', `⚡ ${t('socket')}`),
        feature('wheelchair', `♿ ${t('wheelchair')}`), feature('quiet', `🌿 ${t('quiet')}`),
        poi.phone ? `📞 ${poi.phone}` : `📞 ${t('no_phone')}`
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
        appendSource(item, fact.source_url, `${t('source_label')} · ${formatDate(fact.collected_at)}`);
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
    field('drawerAiSummary', poi.description || t('no_description'));
    field('drawerAiVibe', isMockMode ? `${t('mock_mode_text')} ${currentLang === 'ru' ? '' : t('mock_language')}` : t('saved_sources'));
    const tipBox = document.getElementById('drawerAiTipBox');
    if (tipBox) tipBox.style.display = poi.activity ? 'flex' : 'none';
    field('drawerAiTip', poi.activity ? `${t('act_label')} ${poi.activity}` : '');
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
        body: JSON.stringify({ poi_id: poi.poi_id, locale: currentLang }), signal: controller.signal,
        cache: 'no-store'
      }).then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      }).then(data => {
        if (drawerAbortController !== controller || controller.signal.aborted) return;
        field('drawerAiSummary', data.summary || poi.description || t('no_description'));
        field('drawerAiTip', data.tip ? `${t('act_label')} ${data.tip}` : '');
        if (tipBox) tipBox.style.display = data.tip ? 'flex' : 'none';
        showFacts(data.evidence || poi.evidence, data.warnings || poi.warnings);
      }).catch(error => {
        if (drawerAbortController !== controller || error.name === 'AbortError') return;
        field('drawerAiVibe', t('detail_unavailable'));
      });
    }
    drawer.classList.add('open');
    drawerFocusOrigin = document.activeElement;
    drawer.removeAttribute('inert');
    drawer.setAttribute('aria-hidden', 'false');
    document.getElementById('drawerCloseBtn')?.focus();
  }

  function closePoiDrawer() {
    if (drawerAbortController) drawerAbortController.abort();
    drawerAbortController = null;
    const drawer = document.getElementById('poiDrawer');
    if (drawer) {
      const wasOpen = drawer.classList.contains('open');
      drawer.classList.remove('open');
      drawer.setAttribute('inert', '');
      if (wasOpen) drawerFocusOrigin?.focus?.();
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

  function appendSource(container, value, label = t('source')) {
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
    clickOpt.textContent = label || `📍 ${t('map_point')} (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    clickOpt.dataset.lat = lat;
    clickOpt.dataset.lon = lon;
    clickOpt.selected = true;

    updateStartMarker(lat, lon, clickOpt.textContent);
    updateReachRadius();
    showMapToast(t('start_selected'));
  }

  // --- Interactive Building & Landmark Badges on Map (2GIS / OSM Style) ---
  // Visual emphasis only. All names, coordinates and facts come from the catalogue.
  const LANDMARK_IDS = new Set([
    'osm_way_499328514', 'osm_way_1196402246', 'osm_way_1460763574',
    'osm_way_549307755'
  ]);

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

    Array.from(poiCatalog.values()).filter(poi => LANDMARK_IDS.has(poi.poi_id)).forEach((bld) => {
      const icon = bld.category === 'mall' ? '🛍️' : bld.category === 'park' || bld.category === 'garden' ? '🌿' : '🏛️';

      const landmarkIcon = L.divIcon({
        className: 'landmark-pill-marker-wrap',
        html: `
          <button type="button" class="landmark-pill-btn" title="${escapeHtml(bld.name)} · ${escapeHtml(categoryName(bld.category))}">
            <span class="landmark-pill-icon">${icon}</span>
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
  let catalogController = null;
  async function loadAndRenderAllPoisOnMap() {
    if (catalogController) catalogController.abort();
    const controller = new AbortController();
    catalogController = controller;
    try {
      let data;
      if (isMockMode) {
        await ensureMockData();
        data = { pois: mockData.pois || [] };
      } else {
        const resp = await fetch(`/api/pois?locale=${currentLang}`, { cache: 'no-store', signal: controller.signal });
        if (!resp.ok) return;
        data = await resp.json();
      }
      if (controller.signal.aborted || catalogController !== controller) return;
      const pois = data.pois || [];
      poiCatalog.clear();
      pois.forEach(poi => poiCatalog.set(poi.poi_id, poi));
      if (!leafletMap) return;
      renderLandmarkButtons();

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
        if (!Number.isFinite(p.lat) || !Number.isFinite(p.lon) || p.recommendable === false) return;
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
      const defaultCenter = [51.0890897, 71.4073303]; // Approximate OSM centre, not a verified entrance.
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
        showMapBackgroundStatus(t('map_unavailable'));
        if (!isMockMode) loadWalkingBackground();
      });
      backgroundTiles.addTo(leafletMap);

      poiMarkersLayer = L.layerGroup().addTo(leafletMap);

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
      showMapBackgroundStatus(t('map_local'));
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
        <div class="svg-pin-wrapper start-pin-wrapper" title="${t('start_control')}">
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
      radiusIndicator.textContent = `${t('radius_label')} ~${(radiusMeters / 1000).toFixed(1)} ${t('kilometre')} (${currentMins} ${t('minute')})`;
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
          <div style="color: #64748b; font-size: 12px; margin-bottom: 6px;">${categoryEmoji} ${escapeHtml(categoryName(poi.category))} • ~${poi.distance_m ?? 0} ${t('meter')} ${t('straight_short')}</div>
          <div style="background: #f0fdf4; color: #166534; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;">
            ${t('total_budget')} ~${totalTime} ${t('minute')}
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
          <div style="font-weight: 700; color: #0f172a; margin-bottom: 2px;">${t('stop')} #${order}: ${escapeHtml(stop.name)}</div>
          <div style="color: #0369a1; font-weight: 600; font-size: 11px; margin-bottom: 4px;">${t('elapsed')}: +${stop.arrival_minutes_estimate} ${t('minute')} • ${t('onsite')}: ${stop.visit_minutes_estimate} ${t('minute')}</div>
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
    if (pointRouteController) pointRouteController.abort();
    pointRouteController = null;
    if (routePolyline && leafletMap) {
      leafletMap.removeLayer(routePolyline);
      routePolyline = null;
    }
    if (routeSummaryBar) {
      routeSummaryBar.classList.add('hidden');
    }
  }

  // --- 2GIS / Google Maps Style Point-to-Point Route Builder ---
  async function buildWalkingRouteToPoi(poi) {
    if (!leafletMap || !Number.isFinite(poi?.lat) || !Number.isFinite(poi?.lon)) return;
    clearRoutePolyline();
    const start = locationSelect?.selectedOptions[0];
    if (!start?.dataset.lat || !start?.dataset.lon || poi.recommendable === false) {
      showMapToast(t('route_unavailable')); return;
    }
    if (isMockMode) { showMapToast(t('route_mock_unavailable')); return; }
    const controller = new AbortController();
    pointRouteController = controller;
    const payload = {
      lat: Number(start.dataset.lat), lon: Number(start.dataset.lon),
      poi_id: poi.poi_id, locale: currentLang,
      climate_shield: Boolean(climateShieldCheck?.checked)
    };
    routeBannerTitle.textContent = `${t('route_to')} ${poi.name}`;
    routeBannerStats.textContent = t('route_loading');
    routeSummaryBar.classList.remove('hidden');
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch('/api/route', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(payload), signal: controller.signal, cache: 'no-store'
      });
      if (!response.ok) throw new Error(httpErrorMessage(response.status));
      const data = await response.json();
      if (pointRouteController !== controller || controller.signal.aborted) return;
      if (data.used_context?.climate) { lastClimateContext = data.used_context.climate; renderWeather(); }
      const coordinates = data.coordinates;
      if (data.status !== 'ready' || !Array.isArray(coordinates) || coordinates.length < 2 ||
          !coordinates.every(c => Array.isArray(c) && c.length === 2 && c.every(Number.isFinite))) {
        routeBannerStats.textContent = data.message || t('route_unavailable');
        showMapToast(data.message || t('route_unavailable')); return;
      }
      // Only the backend walking graph may supply a route. Never join start/end with a fabricated line.
      routePolyline = L.polyline(coordinates.map(c => [c[1], c[0]]), {
        color: '#0284c7', weight: 6, opacity: 0.92,
        lineCap: 'round', lineJoin: 'round', dashArray: '2, 8'
      }).addTo(leafletMap);
      routeBannerStats.textContent = `${t('one_way')} ~${data.walk_minutes_estimate} ${t('minute')} (${data.distance_m} ${t('meter')})`;
      if (data.warnings?.length) {
        const note = document.createElement('div');
        note.className = 'route-access-note';
        note.textContent = data.warnings.join(' ');
        routeBannerStats.appendChild(note);
      }
      leafletMap.fitBounds(routePolyline.getBounds(), mapViewPadding());
    } catch (error) {
      if (pointRouteController !== controller) return;
      routeBannerStats.textContent = error.name === 'AbortError' || error instanceof TypeError
        ? t('connection_error') : error.message || t('route_unavailable');
    } finally {
      clearTimeout(timeout);
      if (pointRouteController === controller) pointRouteController = null;
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
        invalidateSearch();
        renderWeather();
        loadWeather();
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
      geoBtn.setAttribute('aria-describedby', 'geoPrivacyNote');
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
      sheetHandle.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sheetHandle.click(); }
      });
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
        const sourceText = chip.getAttribute('data-fill');
        const fillKey = {'С ребёнком':'fill_child','Я турист':'fill_tourist','Ночью':'fill_night','панорамный вид':'fill_view','тихое место':'fill_quiet','кофе навынос':'fill_togo'}[sourceText];
        const fillText = fillKey ? t(fillKey) : sourceText;
        if (queryInput) {
          queryInput.value = fillText;
          queryInput.focus();
        }
        // Auto-adapt minutes and category for common scenarios
        if (['С ребёнком', 'Я турист', 'Ночью', 'панорамный вид', 'тихое место'].includes(sourceText)) {
          const radioWalk = document.querySelector('input[name="category"][value="walk"]');
          if (radioWalk) radioWalk.checked = true;
          const curMins = getSelectedMinutes();
          if (curMins < 60) {
            selectMinutes(60);
          }
        } else if (sourceText === 'кофе навынос') {
          const radioCafe = document.querySelector('input[name="category"][value="cafe"]');
          if (radioCafe) radioCafe.checked = true;
        }
      });
    });

    // Keyboard shortcuts: Escape closes drawer and telemetry modal
    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      window.addEventListener('keydown', (e) => {
        trapModalFocus(e);
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

        if (q && queryInput) queryInput.value = cat === 'cafe' ? t('default_coffee') : t('default_walk');
        if (min) selectMinutes(Number(min));
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
          showMapToast(t('start_selected'));
          closePoiDrawer();
        }
      });
    }

    const drawerRouteBtn = document.getElementById('drawerRouteBtn');
    if (drawerRouteBtn) {
      drawerRouteBtn.addEventListener('click', () => {
        if (currentDrawerPoi) {
          buildWalkingRouteToPoi(currentDrawerPoi);
          closePoiDrawer();
        }
      });
    }

    if (closeRouteBannerBtn) {
      closeRouteBannerBtn.addEventListener('click', () => {
        clearRoutePolyline();
      });
    }

    if (timeRangeSlider) {
      timeRangeSlider.addEventListener('input', () => {
        const val = parseInt(timeRangeSlider.value, 10);
        selectMinutes(val);
        invalidateSearch();
      });
    }

    document.querySelectorAll('.time-slider-ticks span').forEach(span => {
      span.addEventListener('click', () => {
        const mins = parseInt(span.dataset.mins, 10);
        if (mins) {
          selectMinutes(mins);
          invalidateSearch();
        }
      });
    });
  }

  function setAppMode(mode) {
    invalidateSearch();
    appMode = mode;
    tabPlaces.classList.toggle('active', mode === 'places');
    tabItinerary.classList.toggle('active', mode === 'itinerary');
    tabPlaces.setAttribute('aria-pressed', String(mode === 'places'));
    tabItinerary.setAttribute('aria-pressed', String(mode === 'itinerary'));
    if (timeRangeSlider) timeRangeSlider.min = mode === 'itinerary' ? '15' : '10';

    if (btnText) {
      btnText.textContent = mode === 'itinerary' ? t('btn_build_route') : t('btn_find');
    }

    renderTimeSelector();
    applyAccessibleLabels();
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
        const response = await fetch(`/api/locations?locale=${currentLang}`, {
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
      errOpt.textContent = t('locations_unavailable');
      locationSelect.appendChild(errOpt);
    }
  }

  function populateLocationsSelect(locations) {
    locationSelect.innerHTML = '';

    const list = Array.isArray(locations) ? [...locations] : [];
    if (list.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.disabled = true;
      opt.selected = true;
      opt.textContent = t('locations_unavailable');
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
    const responses = await Promise.allSettled([`/api/meta?locale=${currentLang}`, '/api/health'].map(async path => {
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
    if (isMockMode) return t('mock_status');
    if (!systemStatusLoaded) return t('status_loading');
    if (!cachedHealth) return t('api_unavailable');
    if (!cachedHealth.llm_configured) return t('local_no_llm');
    if (cachedHealth.llm_last_status === 'ok') return t('llm_ok');
    if (cachedHealth.llm_last_status === 'not_checked') return t('llm_unchecked');
    return t('llm_fallback');
  }

  function updateSystemStatusText() {
    if (!statusSummaryText) return;
    const m = cachedSystemMeta;
    statusSummaryText.textContent = m
      ? `${t('network_summary', {nodes: m.walking_network?.node_count?.toLocaleString() ?? '—', pois: m.poi_count ?? '—'})} • ${modelStatus()}`
      : modelStatus();
  }

  function openTelemetryModal() {
    if (!telemetryModal || !telemetryModalBody) return;
    const m = cachedSystemMeta || {};
    const number = value => Number.isFinite(value) ? value.toLocaleString() : '—';
    telemetryModalBody.innerHTML = `
      <div>
        <div class="telemetry-section-title">🗺️ ${t('network_title')}</div>
        <div class="telemetry-grid">
          <div class="telemetry-card"><span class="telemetry-val">${number(m.walking_network?.node_count)}</span><span class="telemetry-lbl">${t('nodes')}</span></div>
          <div class="telemetry-card"><span class="telemetry-val">${number(m.walking_network?.directed_edge_count)}</span><span class="telemetry-lbl">${t('edges')}</span></div>
        </div>
      </div>
      <div>
        <div class="telemetry-section-title">📍 ${t('dataset_title')}</div>
        <div class="telemetry-grid">
          <div class="telemetry-card"><span class="telemetry-val">${number(m.poi_count)}</span><span class="telemetry-lbl">${t('objects')}</span></div>
          <div class="telemetry-card"><span class="telemetry-val">${number(m.data_quality?.attributed_fact_count)}</span><span class="telemetry-lbl">${t('facts_count', {official: number(m.data_quality?.official_fact_count)})}</span></div>
        </div>
      </div>
      <div>
        <div class="telemetry-section-title">⚡ ${t('amenities_title')}</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
          <span class="feature-pill">🔌 ${t('socket')}: ${number(m.data_quality?.confirmed_features?.socket)}</span>
          <span class="feature-pill">📶 Wi-Fi: ${number(m.data_quality?.confirmed_features?.wifi)}</span>
          <span class="feature-pill">♿ ${t('wheelchair')}: ${number(m.data_quality?.confirmed_features?.wheelchair)}</span>
          <span class="feature-pill">🌿 ${t('quiet')}: ${number(m.data_quality?.confirmed_features?.quiet)}</span>
        </div>
      </div>
      <div>
        <div class="telemetry-section-title">🔒 ${t('privacy_title')}</div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">${t('llm_status')}</span><span class="telemetry-info-val">${escapeHtml(modelStatus())}</span></div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">${t('sources')}</span><span class="telemetry-info-val">${t('sources_caveat')}</span></div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">${t('coordinates')}</span><span class="telemetry-info-val">${t('geo_explanation')}</span></div>
        <div class="telemetry-info-row"><span class="telemetry-info-key">${t('license')}</span><span class="telemetry-info-val">© OpenStreetMap contributors · ODbL 1.0</span></div>
      </div>`;
    modalFocusOrigin = document.activeElement;
    closePoiDrawer();
    telemetryModal.classList.remove('hidden');
    modalCloseBtn?.focus();
    setModalBackgroundInert(true);
  }

  function closeTelemetryModal() {
    const wasOpen = telemetryModal && !telemetryModal.classList.contains('hidden');
    if (telemetryModal) telemetryModal.classList.add('hidden');
    setModalBackgroundInert(false);
    if (wasOpen) modalFocusOrigin?.focus?.();
  }

  // --- GPS Geolocation Handler ---
  function handleGeoLocation() {
    if (isMockMode) { setGeoStatus(t('gps_mock'), 'active'); return; }
    if (!navigator.geolocation) {
      setGeoStatus(t('gps_unsupported'), 'error');
      return;
    }

    setGeoStatus(t('gps_loading'), 'active');
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

        updateStartMarker(lat, lon, t('my_location'));
        if (leafletMap) leafletMap.flyTo([lat, lon], 15, { duration: 0.8 });
        setGeoStatus(t('gps_ready'), 'active');
      },
      (error) => {
        geoBtn.disabled = false;
        setGeoStatus(error.code === 1 ? t('gps_denied') : t('gps_error'), 'error');
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
      handleSearchError(t('select_start'));
      return;
    }
    const category = document.querySelector('input[name="category"]:checked')?.value || 'walk';
    const common = {
      query: queryInput.value.trim() || (category === 'cafe' && appMode !== 'itinerary' ? t('default_coffee') : t('default_walk')),
      locale: currentLang,
      lat: Number(option.dataset.lat),
      lon: Number(option.dataset.lon),
      available_minutes: getSelectedMinutes(),
      climate_shield: Boolean(climateShieldCheck?.checked)
    };
    const payload = appMode === 'itinerary'
      ? { ...common, include_coffee: category === 'cafe' }
      : { ...common, category };
    lastRequestPayload = payload;
    executeSearch(payload);
  }

  function invalidateSearch() {
    lastClimateContext = null;
    renderWeather();
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
    if (walk) walk.textContent = appMode === 'itinerary' ? t('without_coffee') : t('cat_walk');
    if (cafe) cafe.textContent = appMode === 'itinerary' ? t('with_coffee') : t('cat_cafe');
  }

  function selectMinutes(value) {
    let radio = document.querySelector(`input[name="availableMinutes"][value="${value}"]`);
    if (!radio) {
      const label = document.createElement('label');
      label.className = 'time-chip';
      radio = document.createElement('input');
      radio.type = 'radio'; radio.name = 'availableMinutes'; radio.value = value;
      radio.addEventListener('change', () => {
        invalidateSearch();
        if (timeRangeSlider) timeRangeSlider.value = value;
        if (timeSliderVal) {
          const unit = currentLang === 'en' ? 'min' : (currentLang === 'kz' ? 'мин' : 'мин');
          timeSliderVal.textContent = `${value} ${unit}`;
        }
        updateReachRadius(value);
      });
      const text = document.createElement('span');
      text.className = 'time-chip-btn';
      const unit = currentLang === 'en' ? 'min' : (currentLang === 'kz' ? 'мин' : 'мин');
      text.textContent = `${value} ${unit}`;
      label.append(radio, text);
      timeSelector.appendChild(label);
    }
    radio.checked = true;
    if (timeRangeSlider) {
      timeRangeSlider.value = value;
    }
    if (timeSliderVal) {
      const unit = currentLang === 'en' ? 'min' : (currentLang === 'kz' ? 'мин' : 'мин');
      timeSliderVal.textContent = `${value} ${unit}`;
    }
    updateReachRadius(value);
  }

  async function mockResponse(payload, mode) {
    await ensureMockData();
    const matches = (mockData.scenarios || []).find(item =>
      item.mode === mode && Object.entries(item.request).every(([key, value]) => payload[key] === value));
    if (matches && !payload.climate_shield && (payload.locale || 'ru') === 'ru') return structuredClone(matches.response);
    const used_context = { ...payload, effective_minutes: payload.available_minutes, required_features: [] };
    const message = t('mock_missing');
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
        if (!response.ok) throw new Error(httpErrorMessage(response.status));
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
        sugBtn.textContent = t('suggested_budget', { minutes: data.suggested_minimum_minutes });
        sugBtn.addEventListener('click', () => {
          selectMinutes(data.suggested_minimum_minutes);
          if (data.used_context?.effective_minutes < data.used_context?.available_minutes ||
              /\d+\s*(?:мин|min|час|hour|ч\b)/i.test(queryInput.value)) {
            const note = document.createElement('p');
            note.className = 'warning-item';
            note.textContent = t('query_time_conflict');
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
    badge.textContent = isMockMode ? t('recorded_example') : t('graph_local');
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
        <span class="itin-stat-val">~${data.total_minutes_estimate || 0} ${t('minute')}</span>
        <span class="itin-stat-lbl">${t('stat_total')}</span>
      </div>
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.walking_minutes_estimate || data.total_walk_minutes_estimate || 0} ${t('minute')}</span>
        <span class="itin-stat-lbl">${t('stat_walk')}</span>
      </div>
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.visit_minutes_estimate || data.total_visit_minutes_estimate || 0} ${t('minute')}</span>
        <span class="itin-stat-lbl">${t('stat_visit')}</span>
      </div>
      <div class="itin-stat-item">
        <span class="itin-stat-val">~${data.reserve_minutes || data.time_reserve_minutes || 0} ${t('minute')}</span>
        <span class="itin-stat-lbl">${t('stat_reserve')}</span>
      </div>
    `;
    summaryCard.appendChild(statsGrid);
    const contextLine = document.createElement('p');
    contextLine.className = 'itin-why';
    contextLine.textContent = t('itinerary_budget', {budget: data.used_context?.effective_minutes ?? data.used_context?.available_minutes ?? '—', remaining: data.remaining_minutes ?? '—'});
    summaryCard.appendChild(contextLine);
    itineraryView.appendChild(summaryCard);

    // Timeline of stops
    const timeline = document.createElement('div');
    timeline.className = 'itinerary-timeline';

    const stops = data.stops || [];
    stops.forEach((stop) => {
      const stopCard = document.createElement('div');
      stopCard.className = 'itin-stop-card';
      stopCard.tabIndex = 0;
      stopCard.addEventListener('keydown', event => {
        if (event.target === stopCard && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault(); openPoiDrawer(stop);
        }
      });
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
      stTime.textContent = `+${stop.arrival_minutes_estimate}–${depTime} ${t('minute')} ${t('elapsed')}`;

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
        actP.textContent = `${t('act_label')} ${stop.activity}`;
        stopCard.appendChild(actP);
      }

      (stop.evidence || []).forEach(fact => {
        const line = document.createElement('p');
        line.className = 'card-evidence-box';
        line.textContent = `${fact.kind === 'official' ? t('official_source') : 'OSM'}: ${fact.text}`;
        appendSource(line, fact.source_url, `${t('source_label')} · ${formatDate(fact.collected_at)}`);
        stopCard.appendChild(line);
      });
      const hours = document.createElement('p');
      hours.className = 'hours-badge';
      hours.textContent = stop.opening_hours ? t('hours_source', {hours: stop.opening_hours}) : t('unconfirmed_hours');
      stopCard.appendChild(hours);
      appendWarnings(stopCard, stop.warnings);
      appendSource(stopCard, stop.source_url, `OSM · ${formatDate(stop.collected_at)}`);
      timeline.appendChild(stopCard);
    });

    // Return to start item
    const finishCard = document.createElement('div');
    finishCard.className = 'itin-stop-card';
    finishCard.style.borderColor = '#34d399';
    finishCard.innerHTML = `
      <div class="itin-stop-header">
        <div class="itin-stop-name" style="color: #059669;">🏁 ${t('finish_point')}</div>
        <div class="itin-stop-time">~${data.walking_minutes_estimate + data.visit_minutes_estimate} ${t('minute')} + ${data.reserve_minutes} ${t('minute')} ${t('buffer')}</div>
      </div>
      <div class="itin-stop-activity">${t('return_plan')}</div>
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
      resultsCountBadge.textContent = t('place_count', {count: recommendations.length});
      resultsCountBadge.classList.remove('hidden');
    }

    if (fallbackNotice) {
      fallbackNotice.className = data.mode === 'rag' && !isMockMode ? 'ai-active-banner' : 'fallback-banner';
      fallbackNotice.textContent = isMockMode ? t('mock_mode_text') : data.mode === 'rag' ? t('rag_mode_text') : t('fallback_mode_text');
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
          sugBtn.textContent = t('increase_time');
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
    lastClimateContext = context?.climate || null;
    renderWeather();
    if (!usedContextTag) return;
    if (!context) {
      usedContextTag.classList.add('hidden');
      return;
    }

    const catName = context.category === 'cafe' ? (currentLang === 'kz' ? '☕ Кофе' : (currentLang === 'en' ? '☕ Coffee' : '☕ Кофе')) : (currentLang === 'kz' ? '🚶 Серуен' : (currentLang === 'en' ? '🚶 Walk' : '🚶 Прогулка'));
    const minutes = context.effective_minutes ?? context.available_minutes;
    const coords = Number.isFinite(context.lat) && Number.isFinite(context.lon) ? `${context.lat.toFixed(4)}, ${context.lon.toFixed(4)}` : t('select_start');

    let tagStr = `${catName} • ${minutes} ${t('minute')} • ${coords}`;
    if (context.required_features && context.required_features.length > 0) {
      const featNames = {
        socket: `🔌 ${t('socket')}`,
        wifi: '📶 Wi-Fi',
        quiet: `🌿 ${t('quiet')}`,
        wheelchair: `♿ ${t('wheelchair')}`
      };
      const feats = context.required_features.map(f => featNames[f] || f).join(', ');
      tagStr += ` • ${feats}`;
    }
    if (context.effective_minutes && context.effective_minutes < (context.available_minutes || 60)) {
      tagStr += ` • ⏱️ ${t('narrowed')}: ${context.effective_minutes} ${t('minute')}`;
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
      card.tabIndex = 0;
      card.addEventListener('keydown', event => {
        if (event.target === card && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault(); focusPoiOnMap(poi.poi_id); openPoiDrawer(poi);
        }
      });

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
      nameEl.textContent = poi.name || categoryName('unknown');

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
      mDistanceLabel.textContent = poi.travel_basis === 'osm_walking_graph' && Number.isFinite(poi.route_distance_m) ? t('graph_distance') : t('straight_dist');
      const mDistanceVal = document.createElement('span');
      mDistanceVal.className = 'metric-value';
      const displayDist = poi.route_distance_m ?? poi.distance_m ?? 0;
      mDistanceVal.textContent = `${displayDist} ${t('meter')}`;
      mDistance.appendChild(mDistanceLabel);
      mDistance.appendChild(mDistanceVal);

      if (poi.travel_basis === 'osm_walking_graph' || poi.route_distance_m) {
        const basisBadge = document.createElement('span');
        basisBadge.className = 'basis-badge';
        basisBadge.textContent = t('basis_graph');
        basisBadge.title = t('graph_caveat');
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
      mWalkVal.textContent = `~${poi.walk_minutes_estimate ?? 0} ${t('minute')}`;
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
      mTotalVal.textContent = `~${totalMin} ${t('minute')}`;
      mTotal.appendChild(mTotalLabel);
      mTotal.appendChild(mTotalVal);

      metrics.appendChild(mDistance);
      metrics.appendChild(mWalk);
      metrics.appendChild(mTotal);
      card.appendChild(metrics);
      const duration = document.createElement('p');
      duration.className = 'card-timing-note';
      duration.textContent = t('timing_note', {visit: poi.visit_minutes_estimate, margin: poi.time_margin_minutes ?? '—'});
      card.appendChild(duration);

      // --- Confirmed Infrastructure Tags (WiFi, Socket, Wheelchair) ---
      if (poi.confirmed_features) {
        const featRow = document.createElement('div');
        featRow.className = 'feature-pills-row';
        if (poi.confirmed_features.socket === true) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = `🔌 ${t('socket')}`;
          featRow.appendChild(p);
        }
        if (poi.confirmed_features.wifi === true) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = '📶 Wi-Fi';
          featRow.appendChild(p);
        }
        if (poi.confirmed_features.wheelchair === true) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = `♿ ${t('wheelchair')}`;
          featRow.appendChild(p);
        }
        if (poi.confirmed_features.quiet === true) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.textContent = `🌿 ${t('quiet')}`;
          featRow.appendChild(p);
        }
        if (poi.climate_shielded === true && (poi.indoor_evidence?.length || poi.tags?.indoor === 'yes' || poi.tags?.indoor_seating === 'yes')) {
          const p = document.createElement('span');
          p.className = 'feature-pill active';
          p.style.background = '#e0f2fe';
          p.style.color = '#0369a1';
          p.style.borderColor = '#7dd3fc';
          p.textContent = `🛡️ ${t('climate_indoor')}`;
          featRow.appendChild(p);
        }
        if (featRow.children.length > 0) {
          card.appendChild(featRow);
        }
      }

      // --- Prominent AI Choice Hero Box ---
      if (poi.why || poi.activity) {
        const aiBox = document.createElement('div');
        aiBox.className = 'ai-why-hero-box';

        const aiBadge = document.createElement('div');
        aiBadge.className = 'ai-why-badge';
        const aiSpark = document.createElement('span');
        aiSpark.className = 'ai-spark-icon';
        aiSpark.textContent = '✨';
        const aiTitle = document.createElement('span');
        aiTitle.className = 'ai-why-title';
        aiTitle.textContent = t('why_ai_chose');
        aiBadge.append(aiSpark, aiTitle);
        aiBox.appendChild(aiBadge);

        if (poi.why) {
          const aiText = document.createElement('p');
          aiText.className = 'ai-why-content';
          aiText.textContent = poi.why;
          aiBox.appendChild(aiText);
        }

        if (poi.activity) {
          const actLine = document.createElement('div');
          actLine.className = 'ai-act-line';
          actLine.innerHTML = `<strong>${t('act_label')}</strong> ${escapeHtml(poi.activity)}`;
          aiBox.appendChild(actLine);
        }

        card.appendChild(aiBox);
      }

      // --- 2GIS Style Walking Route Button ---
      const routeBtn = document.createElement('button');
      routeBtn.type = 'button';
      routeBtn.className = 'card-route-btn';
      routeBtn.innerHTML = `<span>🚶</span> <span>${t('btn_route')}</span>`;
      routeBtn.title = `${t('route_to')} ${poi.name}`;
      routeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        focusPoiOnMap(poi.poi_id);
        buildWalkingRouteToPoi(poi);
      });
      card.appendChild(routeBtn);

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
          evTitle.textContent = ev.kind === 'official' ? t('verified_fact') : t('osm_source');
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
          evBadge.textContent = `${t('evidence_sha')} · ${formatDate(ev.collected_at)}${ev.published_at ? ` · ${t('published')}: ${formatDate(ev.published_at)}` : ''}`;
          evMeta.appendChild(evBadge);

          if (safeHttpUrl(ev.source_url)) {
            const evLink = document.createElement('a');
            evLink.className = 'evidence-link';
            evLink.href = ev.source_url;
            evLink.target = '_blank';
            evLink.rel = 'noopener noreferrer';
            evLink.textContent = t('source');
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
        hoursBadge.textContent = `🕒 ${t('hours_source', {hours: poi.opening_hours})}`;
      } else {
        hoursBadge.classList.add('hours-unconfirmed');
        hoursBadge.textContent = t('unconfirmed_hours');
      }
      infoRow.appendChild(hoursBadge);

      if (poi.phone) {
        const phoneBadge = document.createElement('a');
        phoneBadge.className = 'hours-badge';
        phoneBadge.style.textDecoration = 'none';
        phoneBadge.href = `tel:${String(poi.phone).replace(/[^+0-9,;]/g, '')}`;
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

      if (safeHttpUrl(poi.source_url)) {
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
      let dateString = poi.collected_at ? formatDate(poi.collected_at) : t('unknown');
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
      return d.toLocaleDateString(currentLang === 'kz' ? 'kk-KZ' : currentLang === 'en' ? 'en-GB' : 'ru-RU', {
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
    if (!res.ok) throw new Error(t('mock_load_error'));
    mockData = await res.json();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
