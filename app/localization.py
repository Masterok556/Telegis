"""Deterministic translations of application explanations; no model or network.

Proper place names, coordinates, IDs, URLs, source dates and opening-hour syntax
remain intact. Unrecognized source prose stays visible with an original-text
label, instead of being silently omitted or translated by an unreliable guess.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Literal


Locale = Literal["ru", "kz", "en"]
TEXT_KEYS = {"message", "why", "activity", "description", "summary", "tip", "text", "privacy"}
TEXT_LIST_KEYS = {"warnings", "limitations"}

# Each entry is an exact source sentence, followed by English and Kazakh.
PHRASES: dict[str, tuple[str, str]] = {
    "Часы работы не подтверждены.": ("Opening hours are unconfirmed.", "Жұмыс уақыты расталмаған."),
    "Часы работы неизвестны.": ("Opening hours are unknown.", "Жұмыс уақыты белгісіз."),
    "Расписание взято из OpenStreetMap; актуальность и доступность сейчас не подтверждены.": (
        "Hours come from OpenStreetMap; their accuracy and current access are unconfirmed.",
        "Кесте OpenStreetMap дерегінен алынған; оның өзектілігі мен қазіргі қолжетімділік расталмаған."),
    "Расписание указано в OSM; актуальность и доступность сейчас не подтверждены.": (
        "OSM reports these hours; their accuracy and current access are unconfirmed.",
        "Бұл кесте OSM-де көрсетілген; оның өзектілігі мен қазіргі қолжетімділік расталмаған."),
    "Часы работы взяты из OSM и могут быть неактуальны.": (
        "Opening hours come from OSM and may be outdated.", "Жұмыс уақыты OSM-нен алынған және ескірген болуы мүмкін."),
    "Координаты обозначают центр объекта, не проверенный вход.": (
        "Coordinates identify the site's center, not a verified entrance.",
        "Координаттар тексерілген кіреберісті емес, нысанның ортасын көрсетеді."),
    "Точка обозначает центр объекта, а не проверенный вход.": (
        "This point identifies the site's center, not a verified entrance.",
        "Бұл нүкте тексерілген кіреберісті емес, нысанның ортасын көрсетеді."),
    "Датасет собран более недели назад; сведения могли измениться.": (
        "The dataset was collected over a week ago; details may have changed.",
        "Деректер бір аптадан астам уақыт бұрын жиналған; мәліметтер өзгеруі мүмкін."),
    "Расстояние по прямой; время приблизительное, пешеходный маршрут не рассчитан.": (
        "Distance is straight-line; time is approximate and no walking path was calculated.",
        "Қашықтық тікелей өлшенген; уақыт жуық, жаяу жүретін жол есептелмеген."),
    "Расстояние distance_m — по прямой; время рассчитано по сети OSM с приблизительными подходами и запасом на вход.": (
        "distance_m is straight-line distance; time uses the OSM network with approximate connectors and an entrance allowance.",
        "distance_m — тікелей қашықтық; уақыт OSM жолдары, жуық жалғау жолдары және кіруге арналған қор арқылы есептелген."),
    "Обходы, временные ограничения и доступность входов не проверены.": (
        "Detours, temporary restrictions and entrance access have not been checked.",
        "Айналма жолдар, уақытша шектеулер және кіреберістердің қолжетімділігі тексерілмеген."),
    "Доступность сейчас не подтверждена; время посещения — оценка по категории.": (
        "Current access is unconfirmed; visiting time is an estimate based on category.",
        "Қазіргі қолжетімділік расталмаған; бару ұзақтығы санат бойынша бағаланған."),
    "Подробные особенности места в источниках не указаны.": (
        "The sources do not describe this place in detail.", "Дереккөздерде орынның ерекшеліктері толық сипатталмаған."),
    "Затем переходите к следующему этапу маршрута.": (
        "Then continue to the next stage of the route.", "Одан кейін бағыттың келесі кезеңіне өтіңіз."),
    "Проходимость дорожек уточните на месте.": (
        "Check path conditions on arrival.", "Жолдардың жағдайын сол жерде тексеріңіз."),
    "Выбирайте доступные общественные дорожки.": (
        "Use accessible public paths.", "Қолжетімді қоғамдық жолдарды таңдаңыз."),
    "Не заходите за ограждения.": (
        "Do not go beyond barriers.", "Қоршаулардан өтпеңіз."),
    "Сначала уточните часы, билеты и доступность входа.": (
        "First check opening hours, tickets and entrance access.",
        "Алдымен жұмыс уақытын, билеттерді және кіреберістің қолжетімділігін нақтылаңыз."),
    "Доступность уточните на месте.": (
        "Check access on arrival.", "Қолжетімділікті сол жерде нақтылаңыз."),
    "Посещение внутренних помещений и смотровой в этот план не входит.": (
        "This plan does not include interior spaces or the viewing platform.",
        "Бұл жоспарға ішкі бөлмелер мен шолу алаңы кірмейді."),
    "В OpenStreetMap отмечена детская площадка: это конкретная остановка для игры с ребёнком.": (
        "OpenStreetMap marks a playground: a specific stop for playing with a child.",
        "OpenStreetMap-та балалар алаңы белгіленген: баламен ойнауға арналған нақты аялдама."),
    "Оборудование и подходящий возраст не подтверждены.": (
        "Equipment and suitable ages are unconfirmed.", "Жабдық пен қолайлы жас расталмаған."),
    "В OpenStreetMap обозначена детская площадка без собственного названия.": (
        "OpenStreetMap marks a playground with no recorded name.",
        "OpenStreetMap-та өз атауы көрсетілмеген балалар алаңы белгіленген."),
    "Для ориентира показано описательное имя и идентификатор OSM; это не официальное название.": (
        "A descriptive label and OSM ID identify it; this is not an official name.",
        "Бағдар үшін сипаттамалық атау мен OSM идентификаторы берілген; бұл ресми атау емес."),
    "Текущий доступ, оборудование, состояние и подходящий возраст не подтверждены.": (
        "Current access, equipment, condition and suitable ages are unconfirmed.",
        "Қазіргі қолжетімділік, жабдық, жағдайы және қолайлы жас расталмаған."),
    "На месте сначала осмотрите покрытие и оборудование, выберите подходящую возрасту активность; при закрытом или повреждённом оборудовании не используйте его.": (
        "First inspect the surface and equipment and choose an age-appropriate activity; do not use closed or damaged equipment.",
        "Алдымен жабынды мен жабдықты қарап, жасына сай әрекетті таңдаңыз; жабық немесе зақымдалған жабдықты қолданбаңыз."),
    "Для ночного запроса найдено указание на круглосуточный режим либо освещение; текущий доступ и освещение всего пути не подтверждены.": (
        "The night-time request matched a source reporting 24-hour hours or lighting; current access and lighting along the whole path are unconfirmed.",
        "Түнгі сұрауға тәулік бойы жұмыс не жарықтандыру туралы дерек табылды; қазіргі қолжетімділік пен бүкіл жолдың жарығы расталмаған."),
    "Ночной вариант основан на указанном в источнике режиме 24/7 или освещении.": (
        "The night-time option is based on source-reported 24/7 hours or lighting.",
        "Түнгі нұсқа дереккөздегі 24/7 кестесіне немесе жарықтандыруға негізделген."),
    "Фактический доступ, безопасность и освещение всего пути ночью не проверены; смотровые и внутренние помещения могут иметь отдельный режим.": (
        "Actual access, safety and lighting along the entire night-time path have not been checked; viewing platforms and interiors may have separate hours.",
        "Нақты қолжетімділік, қауіпсіздік және түндегі бүкіл жолдың жарығы тексерілмеген; шолу алаңдары мен ішкі бөлмелердің кестесі бөлек болуы мүмкін."),
    "Возрастные ограничения и состояние оборудования не проверены.": (
        "Age restrictions and equipment condition have not been checked.",
        "Жас шектеулері мен жабдықтың жағдайы тексерілмеген."),
    "Время ходьбы рассчитано для общего темпа; с ребёнком может понадобиться больше времени.": (
        "Walking time uses a general pace; walking with a child may take longer.",
        "Жүру уақыты жалпы қарқынға есептелген; баламен көбірек уақыт қажет болуы мүмкін."),
    "Пока доступны только места в районе EXPO / Mega Silk Way.": (
        "Places are currently available only in the EXPO / Mega Silk Way area.",
        "Қазір орындар тек EXPO / Mega Silk Way ауданында қолжетімді."),
    "Пока доступны только маршруты в районе EXPO / Mega Silk Way.": (
        "Routes are currently available only in the EXPO / Mega Silk Way area.",
        "Қазір бағыттар тек EXPO / Mega Silk Way ауданында қолжетімді."),
    "Выберите стартовую точку в зоне покрытия.": (
        "Choose a starting point inside the coverage area.", "Қамтылған аумақтан бастапқы нүктені таңдаңыз."),
    "Текст запроса и выбранная категория расходятся.": (
        "The request text conflicts with the selected category.", "Сұрау мәтіні таңдалған санатқа сәйкес келмейді."),
    "Переключите «Прогулка» / «Кофе» или уточните запрос.": (
        "Switch between Walking and Coffee, or clarify your request.", "«Серуен» / «Кофе» санатын ауыстырыңыз немесе сұрауды нақтылаңыз."),
    "В этой части датасета нет подходящих мест.": (
        "No matching places are available in this part of the dataset.", "Деректердің бұл бөлігінде сәйкес орындар жоқ."),
    "Подходящих мест с посещением и возвращением в указанные ограничения времени и расстояния не найдено.": (
        "No matching place fits the visit, return trip and specified time and distance limits.",
        "Бару, қайту және көрсетілген уақыт пен қашықтық шектеріне сәйкес орын табылмады."),
    "Попробуйте увеличить время или радиус.": (
        "Try increasing the time budget or radius.", "Уақытты немесе радиусты арттырып көріңіз."),
    "Для части мест может не быть связного пути в сохранённой сети OSM.": (
        "Some places may lack a connected path in the saved OSM network.",
        "Кейбір орындарға сақталған OSM желісінде жалғасқан жол болмауы мүмкін."),
    "Доступность сейчас и время поездки в аэропорт не проверяются.": (
        "Current access and airport travel time are not verified.", "Қазіргі қолжетімділік пен әуежайға бару уақыты тексерілмейді."),
    "Нельзя обещать посещение до вылета.": (
        "A visit before your flight cannot be promised.", "Ұшуға дейін барып үлгеруге кепілдік берілмейді."),
    "Доступность всего пути с коляской, отсутствие лестниц и доступность входов не подтверждены.": (
        "Stroller access along the full path, absence of stairs and entrance access are unconfirmed.",
        "Бүкіл жолдың арбамен жүруге жарамдылығы, баспалдақтардың болмауы және кіреберістер расталмаған."),
    "В источниках нет подтверждения указанного специального условия.": (
        "The sources do not confirm the requested special condition.",
        "Дереккөздер сұралған арнайы шартты растамайды."),
    "Оно не будет заменено обычной рекомендацией.": (
        "It will not be silently replaced with a general recommendation.",
        "Ол ескертусіз жалпы ұсыныспен ауыстырылмайды."),
    "Подтверждённых действующих интерактивных экспозиций в текущем датасете нет.": (
        "The current dataset has no confirmed operating interactive exhibitions.",
        "Қазіргі деректерде жұмыс істеп тұрған интерактивті көрмелер расталмаған."),
    "Можно отдельно искать детские площадки или обычную прогулку.": (
        "You can search separately for playgrounds or a regular walk.",
        "Балалар алаңдарын немесе қарапайым серуенді бөлек іздеуге болады."),
    "В данных недостаточно сведений для подтверждения дополнительного условия.": (
        "The data is insufficient to confirm the additional condition.",
        "Қосымша шартты растауға деректер жеткіліксіз."),
    "Уточните запрос.": ("Please clarify the request.", "Сұрауды нақтылаңыз."),
    "Оно не будет молча исключено из маршрута.": (
        "It will not be silently dropped from the route.", "Бұл шарт бағыттан ескертусіз алынып тасталмайды."),
    "Запрошена кофейная остановка, но текст исключает кафе.": (
        "A coffee stop is selected, but the text excludes cafés.", "Кофе аялдамасы таңдалған, бірақ мәтінде кафелер алынып тасталған."),
    "Отключите include_coffee или измените запрос.": (
        "Turn off the coffee-stop option or change the request.", "Кофе аялдамасын өшіріңіз немесе сұрауды өзгертіңіз."),
    "Текст просит кофе, но include_coffee отключён.": (
        "The text asks for coffee, but the coffee-stop option is off.", "Мәтінде кофе сұралған, бірақ кофе аялдамасы өшірілген."),
    "Согласуйте запрос и этот переключатель.": (
        "Make the request and the switch agree.", "Сұрау мен қосқышты сәйкестендіріңіз."),
    "Для мини-маршрута нужны прогулочные остановки.": (
        "A mini-route needs walking stops.", "Шағын бағытқа серуен аялдамалары қажет."),
    "Для одного кофе используйте обычные рекомендации либо добавьте интерес к прогулке или парку.": (
        "For coffee alone, use place recommendations, or add a walk or park to your request.",
        "Тек кофе үшін орын ұсыныстарын пайдаланыңыз немесе сұрауға серуен не саябақ қосыңыз."),
    "Текст ограничивает маршрут только выбранными прогулочными местами, а include_coffee добавляет кафе.": (
        "The text limits the route to walking places, but the coffee-stop option adds a café.",
        "Мәтін бағытты серуен орындарымен шектейді, ал кофе аялдамасы кафе қосады."),
    "Отключите кофейную остановку или уточните запрос.": (
        "Turn off the coffee stop or clarify the request.", "Кофе аялдамасын өшіріңіз немесе сұрауды нақтылаңыз."),
    "Не хватает подтверждённых мест для прогулки с кофейной остановкой.": (
        "There are not enough confirmed places for a walk with a coffee stop.",
        "Кофе аялдамасы бар серуенге расталған орындар жеткіліксіз."),
    "Не хватает подтверждённых мест для прогулки.": (
        "There are not enough confirmed walking stops.", "Серуенге расталған аялдамалар жеткіліксіз."),
    "Безбарьерность всех переходов и входов не подтверждена.": (
        "Step-free access for all paths and entrances is unconfirmed.",
        "Барлық жолдар мен кіреберістердің кедергісіздігі расталмаған."),
    "Даже отметка доступности отдельного места не подтверждает доступность всего маршрута.": (
        "An accessibility tag for one place does not establish accessibility of the whole route.",
        "Бір орынның қолжетімділік белгісі бүкіл бағыттың қолжетімділігін растамайды."),
    "Пешеходная сеть недоступна.": (
        "The walking network is unavailable.", "Жаяу жолдар желісі қолжетімсіз."),
    "Маршрут не построен: прямые линии не заменяют реальные дорожки.": (
        "No route was generated: straight lines cannot replace real paths.",
        "Бағыт құрылмады: түзу сызықтар нақты жолдарды алмастырмайды."),
    "В выбранных ограничениях не найден связный пешеходный круг минимум через два разных места.": (
        "No connected walking loop through at least two distinct places fits these constraints.",
        "Осы шектеулермен кемінде екі бөлек орыннан өтетін жалғасқан жаяу шеңбер табылмады."),
    "Возможно, в OSM не хватает соединяющих дорожек или проверяемых подходов; маршрут не выдуман.": (
        "OSM may lack connecting paths or verifiable approaches; no route was invented.",
        "OSM-де жалғайтын жолдар не тексерілетін кіреберістер жетіспеуі мүмкін; бағыт ойдан шығарылмады."),
    "Не удалось уместить две разные остановки, дорогу обратно и запас времени.": (
        "Two distinct stops, the return walk and reserve time do not fit.",
        "Екі бөлек аялдама, қайту жолы және уақыт қоры берілген уақытқа сыймады."),
    "Длительность посещений не сокращается ради результата.": (
        "Visit durations are not shortened just to produce a result.", "Нәтиже алу үшін бару ұзақтығы қысқартылмайды."),
    "Круговой мини-маршрут с возвращением и запасом времени рассчитан по сохранённой пешеходной сети OSM.": (
        "This loop, including the return walk and reserve time, uses the saved OSM walking network.",
        "Қайту жолы мен уақыт қоры бар айналмалы бағыт сақталған OSM жаяу жолдар желісімен есептелген."),
    "Время приблизительное: скорость 70 м/мин, длительность посещений по категории; запас не гарантирует возвращение к точному сроку.": (
        "Time is approximate: walking pace is 70 m/min and visits depend on category; the reserve does not guarantee a precise return time.",
        "Уақыт жуық: жүру жылдамдығы 70 м/мин, бару ұзақтығы санатқа байланысты; уақыт қоры дәл мерзімде қайтуға кепілдік бермейді."),
    "Дорожки взяты из OSM; временные перекрытия, состояние покрытия и доступность входов не проверены.": (
        "Paths come from OSM; temporary closures, surface condition and entrance access are unverified.",
        "Жолдар OSM-нен алынған; уақытша жабылу, жабын жағдайы және кіреберістер тексерілмеген."),
    "Маршрут и идеи занятий рассчитаны кодом; сведения о местах взяты из OSM и указанных официальных источников.": (
        "The route and activity ideas are generated by code; place facts come from OSM and the cited official sources.",
        "Бағыт пен әрекет идеялары кодпен құрылған; орындар туралы мәліметтер OSM және көрсетілген ресми дереккөздерден алынған."),
    "Короткие соединения координат с сетью приблизительны и могут пересекать препятствия; проверяйте подходы на месте.": (
        "Short connectors to the network are approximate and may cross obstacles; check approaches on arrival.",
        "Желіге қысқа жалғау жолдары жуық және кедергілерді кесіп өтуі мүмкін; оларды сол жерде тексеріңіз."),
    "Их длина включена во время.": (
        "Their length is included in the time estimate.", "Олардың ұзындығы уақыт есебіне қосылған."),
    "Модель не подключена.": ("The language model is not connected.", "Тілдік модель қосылмаған."),
    "Провайдер не принял API-ключ; проверьте настройки сервера.": (
        "The provider rejected the API key; check the server settings.", "Провайдер API кілтін қабылдамады; сервер баптауларын тексеріңіз."),
    "Лимит средств API недостаточен; проверьте баланс и лимит ключа у провайдера.": (
        "API credit is insufficient; check the provider balance and key limit.", "API қаражаты жеткіліксіз; провайдердегі теңгерім мен кілт шегін тексеріңіз."),
    "Провайдер временно ограничил частоту запросов; попробуйте позже.": (
        "The provider temporarily rate-limited requests; try later.", "Провайдер сұрау жиілігін уақытша шектеді; кейінірек көріңіз."),
    "Выбранная модель недоступна; проверьте её ID и доступ у провайдера.": (
        "The selected model is unavailable; check its ID and provider access.", "Таңдалған модель қолжетімсіз; оның ID-ін және провайдердегі рұқсатты тексеріңіз."),
    "Модель не ответила за отведённое время.": (
        "The model did not respond in time.", "Модель берілген уақытта жауап бермеді."),
    "Не удалось связаться с провайдером модели.": (
        "The model provider could not be reached.", "Модель провайдерімен байланыс орнатылмады."),
    "Ответ модели не прошёл проверку по найденным данным.": (
        "The model response failed validation against the retrieved data.", "Модель жауабы табылған деректермен тексеруден өтпеді."),
    "Провайдер модели вернул ошибку.": (
        "The model provider returned an error.", "Модель провайдері қате қайтарды."),
    "Показаны рекомендации по данным и шаблонам (fallback).": (
        "Recommendations use stored data and templates (fallback).", "Ұсыныстар сақталған деректер мен үлгілерге негізделген (fallback)."),
    "В OSM отмечены места внутри помещения.": (
        "OSM reports indoor seating.", "OSM-де үй ішіндегі орындар көрсетілген."),
    "В OSM указан Wi-Fi; работоспособность и условия подключения нужно уточнить.": (
        "OSM reports Wi-Fi; confirm that it works and check connection terms.",
        "OSM-де Wi-Fi көрсетілген; жұмысын және қосылу шарттарын нақтылау қажет."),
    "В OSM указан доступ к интернету; способ подключения не уточнён.": (
        "OSM reports internet access; the connection type is unspecified.",
        "OSM-де интернетке қолжетімділік көрсетілген; қосылу тәсілі нақтыланбаған."),
    "В OSM интернет помечен как бесплатный; актуальные условия нужно уточнить.": (
        "OSM marks internet as free; confirm current terms.",
        "OSM-де интернет тегін деп белгіленген; қазіргі шарттарын нақтылау қажет."),
    "В OSM отмечена возможность заказа с собой; наличие уточните при заказе.": (
        "OSM reports takeaway service; confirm availability when ordering.",
        "OSM-де өзімен алып кету мүмкіндігі көрсетілген; тапсырыс кезінде нақтылаңыз."),
    "В OSM указаны места на улице; сезонную доступность нужно уточнить.": (
        "OSM reports outdoor seating; confirm seasonal availability.",
        "OSM-де сырттағы орындар көрсетілген; маусымдық қолжетімділігін нақтылау қажет."),
    "В OSM указано отсутствие мест на улице.": (
        "OSM reports no outdoor seating.", "OSM-де сырттағы орындардың жоқтығы көрсетілген."),
    "В OSM отмечен запрет курения.": (
        "OSM reports no smoking.", "OSM-де темекі шегуге тыйым салынғаны көрсетілген."),
    "В OSM отмечен туалет; условия доступа не подтверждены.": (
        "OSM reports a toilet; access terms are unconfirmed.",
        "OSM-де дәретхана көрсетілген; кіру шарттары расталмаған."),
    "В OSM сад обозначен как общественный; текущий доступ нужно уточнить.": (
        "OSM marks the garden as public; confirm current access.",
        "OSM-де бақ қоғамдық деп белгіленген; қазіргі қолжетімділігін нақтылау қажет."),
    "По статье Nazarbayev University, камни для этого японского сада привезли из Японии.": (
        "According to Nazarbayev University, the stones for this Japanese garden were brought from Japan.",
        "Nazarbayev University мақаласына сәйкес, бұл жапон бағының тастары Жапониядан әкелінген."),
    "В описании NU — композиция из 15 камней: с одной точки видны 14.": (
        "NU describes an arrangement of 15 stones, with 14 visible from one viewpoint.",
        "NU сипаттамасында 15 тастан тұратын композиция бар: бір нүктеден 14 тас көрінеді."),
    "Это идея для внимательного наблюдения.": (
        "This is an idea for careful observation.", "Бұл мұқият бақылауға арналған идея."),
    "Официальный сайт описывает восемь тематических садов вокруг круглой центральной части.": (
        "The official website describes eight themed gardens around the circular central area.",
        "Ресми сайт дөңгелек орталық бөліктің айналасындағы сегіз тақырыптық бақты сипаттайды."),
    "На официальном сайте отмечен пешеходный мост через искусственный водоём.": (
        "The official website describes a pedestrian bridge over an artificial pond.",
        "Ресми сайтта жасанды су айдынын кесіп өтетін жаяу көпір көрсетілген."),
    "На территории описан оранжерейный комплекс; его посещение требует отдельной проверки часов и билетов.": (
        "The site describes a greenhouse complex; check its hours and tickets separately.",
        "Аумақта жылыжай кешені сипатталған; оның жұмыс уақыты мен билеттерін бөлек тексеру қажет."),
    "Сайт описывает весь ботанический сад; вход в оранжерею, часы и билеты отдельно не проверялись.": (
        "The website describes the entire botanical garden; greenhouse entry, hours and tickets were not separately checked.",
        "Сайт бүкіл ботаникалық бақты сипаттайды; жылыжайға кіру, уақыт пен билеттер бөлек тексерілмеген."),
    "Погода — модельная оценка для района EXPO, а не измерение у вашей точки.": (
        "Weather is a model estimate for the EXPO area, not a measurement at your position.",
        "Ауа райы — сіздің нүктеңіздегі өлшеу емес, EXPO ауданына арналған модельдік баға."),
    "Текущие условия не являются прогнозом на всё время прогулки.": (
        "Current conditions are not a forecast for the entire walk.",
        "Қазіргі жағдай бүкіл серуен уақытына арналған болжам емес."),
    "Пороговые правила Telegis служат выбору формата прогулки и не заменяют официальные предупреждения.": (
        "Telegis thresholds help select the outing format and do not replace official warnings.",
        "Telegis шектері серуен пішімін таңдауға көмектеседі және ресми ескертулерді алмастырмайды."),
    "Показаны устаревшие сведения, не погода сейчас.": (
        "These are outdated values, not current weather.", "Бұл — қазіргі ауа райы емес, ескірген мәліметтер."),
    "Климатическая адаптация по ним не применяется.": (
        "They are not used for climate adaptation.", "Олар климаттық бейімдеуге қолданылмайды."),
    "Текущую погоду получить не удалось.": (
        "Current weather could not be retrieved.", "Қазіргі ауа райы алынбады."),
    "Значения не подставлены; климатическая адаптация недоступна.": (
        "No values were substituted; climate adaptation is unavailable.",
        "Мәндер ойдан толтырылмады; климаттық бейімдеу қолжетімсіз."),
    "Актуальных погодных данных недостаточно для климатической адаптации.": (
        "Current weather data is insufficient for climate adaptation.",
        "Климаттық бейімдеуге өзекті ауа райы деректері жеткіліксіз."),
    "Демонстрационный сценарий с вымышленной погодой.": (
        "A demonstration scenario with synthetic weather.", "Ойдан алынған ауа райы бар демонстрациялық сценарий."),
    "Это не текущие данные Астаны и не ответ Open-Meteo.": (
        "This is neither current Astana weather nor an Open-Meteo response.",
        "Бұл Астананың қазіргі ауа райы да, Open-Meteo жауабы да емес."),
    "Модельные условия неблагоприятны для пешей прогулки.": (
        "Modelled conditions are unfavorable for a walk.", "Модельдік жағдай жаяу серуенге қолайсыз."),
    "Климатический режим не предлагает маршрут с уличными переходами; проверьте местный прогноз и официальные предупреждения.": (
        "Climate mode does not offer a route with outdoor walking legs; check the local forecast and official warnings.",
        "Климаттық режим сыртта жүру бөліктері бар бағыт ұсынбайды; жергілікті болжам мен ресми ескертулерді тексеріңіз."),
    "Для климатического режима подходят только места с подтверждением помещения.": (
        "Climate mode requires places with evidence of indoor space.",
        "Климаттық режимге үй ішіндегі орын екені расталған нысандар ғана сәйкес келеді."),
    "Переходы до них остаются уличными; тепло, часы и текущая доступность не подтверждаются.": (
        "The walks to them remain outdoors; warmth, opening hours and current access are not confirmed.",
        "Оларға баратын жол сыртта қалады; жылу, жұмыс уақыты және қазіргі қолжетімділік расталмайды."),
    "Порогов климатического режима по этим модельным данным не обнаружено.": (
        "These model values do not trigger the climate-mode thresholds.",
        "Бұл модельдік мәндер климаттық режим шектеріне жетпейді."),
    "Это не подтверждение безопасности, проходимости или неизменности погоды.": (
        "This does not confirm safety, path conditions or unchanged weather.",
        "Бұл қауіпсіздікті, жолдың жарамдылығын немесе ауа райының өзгермейтінін растамайды."),
    "Климатический режим допускает только остановки с явными данными о помещении.": (
        "Climate mode permits only stops with explicit evidence of indoor space.",
        "Климаттық режим үй ішінде екені туралы нақты дерегі бар аялдамаларға ғана рұқсат етеді."),
    "Нужны явные данные о помещении; категория кафе или музей этого не подтверждает.": (
        "Explicit indoor evidence is required; a café or museum category does not prove it.",
        "Үй ішінде екені туралы нақты дерек қажет; кафе не музей санаты мұны растамайды."),
    "Климатический режим выключен; погода не влияет на выбор.": (
        "Climate mode is off; weather does not affect the selection.",
        "Климаттық режим өшірулі; ауа райы таңдауға әсер етпейді."),
    "Климатический режим приостановлен: актуальная погода не подтверждена.": (
        "Climate mode is paused: current weather is unconfirmed.",
        "Климаттық режим тоқтатылды: қазіргі ауа райы расталмаған."),
    "Повторите запрос позже или явно выключите этот режим для обычного поиска.": (
        "Try again later or explicitly turn this mode off for a standard search.",
        "Кейінірек қайталаңыз немесе қалыпты іздеу үшін осы режимді өзіңіз өшіріңіз."),
    "Климатическая адаптация недоступна: недостаточно погодных данных.": (
        "Climate adaptation is unavailable: weather data is insufficient.",
        "Климаттық бейімдеу қолжетімсіз: ауа райы деректері жеткіліксіз."),
    "В OSM явно отмечено расположение внутри помещения.": (
        "OSM explicitly marks the location as indoors.", "OSM-де нысанның үй ішінде орналасқаны анық көрсетілген."),
    "В OSM явно отмечены места для сидения внутри.": (
        "OSM explicitly reports indoor seating.", "OSM-де іште отыратын орындар анық көрсетілген."),
    "Старт вне зоны покрытия EXPO / Mega Silk Way.": (
        "The starting point is outside EXPO / Mega Silk Way coverage.",
        "Бастапқы нүкте EXPO / Mega Silk Way қамту аумағынан тыс."),
    "Точка отсутствует в проверенном датасете.": (
        "The place is absent from the verified dataset.", "Орын тексерілген деректерде жоқ."),
    "Доступность этой точки не подтверждена; маршрут к ней не предлагается.": (
        "Access to this place is unconfirmed; no route to it is offered.",
        "Бұл орынның қолжетімділігі расталмаған; оған бағыт ұсынылмайды."),
    "Для этой точки нет явного подтверждения помещения.": (
        "There is no explicit indoor evidence for this place.",
        "Бұл орынның үй ішінде екені туралы нақты растау жоқ."),
    "Климатический режим не допускает её в маршрут.": (
        "Climate mode excludes it from the route.", "Климаттық режим оны бағытқа қоспайды."),
    "Связный путь к этой точке в сети OSM не найден; линия маршрута не выдумана.": (
        "No connected path to this place was found in OSM; no route line has been invented.",
        "OSM желісінде бұл орынға жалғасқан жол табылмады; бағыт сызығы ойдан жасалмады."),
    "Это путь в одну сторону; посещение и возвращение не включены во время.": (
        "This is a one-way walk; visiting and returning are not included in the time.",
        "Бұл — бір бағыттағы жол; нысанда болу уақыты мен кері қайту есепке кірмейді."),
    "Время рассчитано по сети OSM при скорости 70 м/мин; перекрытия, покрытие и доступность входа не подтверждены.": (
        "Time uses the OSM network at 70 m/min; closures, surfaces and entrance access are unconfirmed.",
        "Уақыт OSM желісі бойынша 70 м/мин жылдамдықпен есептелген; жол жабылуы, жабын және кіреберіс расталмаған."),
    "Часы работы и доступность сейчас не подтверждены.": (
        "Opening hours and current access are unconfirmed.", "Жұмыс уақыты мен қазіргі қолжетімділік расталмаған."),
    "Подходы от координат к сети приблизительны и могут пересекать препятствия; их длина включена во время.": (
        "Connections from the coordinates to the network are approximate and may cross obstacles; their length is included in the time.",
        "Координаттардан желіге дейінгі жалғау жолдары жуық және кедергілерді кесіп өтуі мүмкін; ұзындығы уақытқа қосылған."),
    "Путь в одну сторону рассчитан по сохранённой пешеходной сети OSM.": (
        "A one-way path was calculated on the saved OSM walking network.",
        "Бір бағыттағы жол сақталған OSM жаяу жолдар желісімен есептелді."),
    "Эта точка показана для ориентира.": (
        "This place is shown as a reference point.", "Бұл орын бағдар ретінде көрсетілген."),
    "Она не включается в рекомендации и мини-маршруты.": (
        "It is not included in recommendations or mini-routes.", "Ол ұсыныстар мен шағын бағыттарға қосылмайды."),
    "Если вход на кампус и композиция доступны, попробуйте с дорожки найти 14 видимых камней, затем смените точку наблюдения.": (
        "If the campus and composition are accessible, try finding 14 visible stones from the path, then change your viewpoint.",
        "Кампус пен композиция қолжетімді болса, жолдан көрінетін 14 тасты тауып, кейін қарау нүктесін ауыстырып көріңіз."),
    "Оранжерею планируйте отдельно после проверки часов и билетов.": (
        "Plan the greenhouse separately after checking hours and tickets.",
        "Жылыжайға баруды уақыт пен билеттерді тексергеннен кейін бөлек жоспарлаңыз."),
    "В источнике отмечены блины: если кафе доступно, уточните наличие и цену порции к кофе.": (
        "The source reports pancakes: if the café is accessible, ask about availability and price with your coffee.",
        "Дереккөзде құймақ көрсетілген: кафе қолжетімді болса, кофеге қосылатын порцияның бар-жоғын және бағасын сұраңыз."),
    "На месте оцените состояние площадки и соответствие возрасту ребёнка.": (
        "Check the playground's condition and suitability for the child's age on arrival.",
        "Алаңның жағдайын және баланың жасына сәйкестігін сол жерде бағалаңыз."),
    "В OSM отмечен памятный бюст.": (
        "OSM marks a commemorative bust.", "OSM-де естелік бюст белгіленген."),
    "NU Impact Foundation 22.05.2026 описывает будущий NU Park и посадку 50 сибирских елей.": (
        "On 22.05.2026, NU Impact Foundation described the future NU Park and the planting of 50 Siberian spruce trees.",
        "NU Impact Foundation 22.05.2026 күні болашақ NU Park пен 50 сібір шыршасын отырғызуды сипаттады."),
    "Официальная публикация от 22.05.2026 описывает NU Park как будущий проект.": (
        "The official publication dated 22.05.2026 describes NU Park as a future project.",
        "22.05.2026 күнгі ресми жарияланым NU Park-ті болашақ жоба ретінде сипаттайды."),
    "Подтверждения ввода всех зон нет; точка исключена из прогулочных маршрутов.": (
        "Opening of all areas is unconfirmed; the place is excluded from walking routes.",
        "Барлық аумақтың ашылғаны расталмаған; орын серуен бағыттарынан алынып тасталған."),
    "Visit Astana описывает арку как памятник 20-летию независимости Казахстана, построенный в 2011 году.": (
        "Visit Astana describes the arch as a monument to 20 years of Kazakhstan's independence, built in 2011.",
        "Visit Astana арканы 2011 жылы салынған, Қазақстан тәуелсіздігінің 20 жылдығына арналған ескерткіш деп сипаттайды."),
    "На странице Visit Astana отмечены национальные орнаменты и барельефы на стенах арки: детали для осмотра снаружи.": (
        "Visit Astana mentions national ornaments and reliefs on the arch walls: details to view from outside.",
        "Visit Astana арка қабырғаларындағы ұлттық оюлар мен барельефтерді атап көрсетеді: оларды сырттан қарауға болады."),
    "Visit Astana указывает для арки круглосуточный график.": (
        "Visit Astana reports 24-hour hours for the arch.", "Visit Astana арка үшін тәулік бойғы кестені көрсетеді."),
    "Это сведения источника, а не подтверждение текущего доступа.": (
        "This is source-reported information, not confirmation of current access.",
        "Бұл — қазіргі қолжетімділіктің расталуы емес, дереккөздегі мәлімет."),
    "Круглосуточная отметка относится к достопримечательности; доступ внутрь и на смотровую площадку отдельно не подтверждён.": (
        "The 24-hour label applies to the landmark; interior and viewing-platform access are not separately confirmed.",
        "Тәулік бойғы белгі көрікті орынға қатысты; ішіне және шолу алаңына кіру бөлек расталмаған."),
    "Освещение, безопасность ночного подхода и временные ограничения не проверены.": (
        "Lighting, night-time approach safety and temporary restrictions have not been checked.",
        "Жарықтандыру, түнде жақындау қауіпсіздігі және уақытша шектеулер тексерілмеген."),
    "Оставайтесь на доступных пешеходных дорожках.": (
        "Stay on accessible walking paths.", "Қолжетімді жаяу жолдармен жүріңіз."),
    "По статье NU, зимой камни укрывают; видимость композиции зависит от сезона.": (
        "According to the NU article, the stones are covered in winter; visibility depends on the season.",
        "NU мақаласына сәйкес, қыста тастар жабылады; композицияның көрінуі маусымға байланысты."),
    "Не сходите с дорожек и не трогайте камни.": (
        "Stay on the paths and do not touch the stones.", "Жолдан шықпаңыз және тастарды ұстамаңыз."),
    "Сведения об устройстве сада взяты из статьи NU от 09.07.2019; нынешний вид и доступ на кампус не подтверждены.": (
        "The garden layout comes from the NU article dated 09.07.2019; its current appearance and campus access are unconfirmed.",
        "Бақтың құрылымы туралы мәлімет NU-дың 09.07.2019 күнгі мақаласынан алынған; қазіргі көрінісі мен кампусқа кіру расталмаған."),
    "Модель выбрала варианты, причины и занятия из найденных данных.": (
        "The model selected options, reasons and activities from the retrieved data.",
        "Модель табылған деректерден нұсқаларды, себептерді және әрекеттерді таңдады."),
    "Сведения о местах взяты из источника; примерное время рассчитано кодом.": (
        "Place details come from the source; approximate time is calculated by code.",
        "Орындар туралы мәлімет дереккөзден алынған; жуық уақыт кодпен есептелген."),
    "Маршрут рассчитан локально; координаты и текст запроса не сохраняются и не отправляются модели или внешнему маршрутизатору.": (
        "The route is calculated locally; coordinates and request text are not stored or sent to a model or an external router.",
        "Бағыт жергілікті есептеледі; координаттар мен сұрау мәтіні сақталмайды және модельге не сыртқы бағыттау қызметіне жіберілмейді."),
    "Нет хранения запросов/GPS и аналитики; модели передаются выбранные POI и нормализованные ограничения, без исходного текста и координат пользователя.": (
        "Requests and GPS are not stored and there is no analytics; the model receives selected POIs and normalized constraints, without the original text or user coordinates.",
        "Сұраулар мен GPS сақталмайды, аналитика жоқ; модельге бастапқы мәтін мен пайдаланушы координаттарынсыз таңдалған POI және қалыпқа келтірілген шектеулер жіберіледі."),
    "distance_m — расстояние по прямой.": (
        "distance_m is straight-line distance.", "distance_m — тікелей қашықтық."),
    "При наличии сети OSM время рассчитывается по путям с приблизительными подходами до 120 м; travel_basis показывает метод.": (
        "When the OSM network is available, time uses paths with approximate connectors up to 120 m; travel_basis identifies the method.",
        "OSM желісі болса, уақыт 120 м-ге дейінгі жуық жалғау жолдары бар бағыттармен есептеледі; travel_basis әдісті көрсетеді."),
    "Часы и доступность в реальном времени не подтверждаются.": (
        "Real-time opening hours and access are not confirmed.",
        "Нақты уақыттағы жұмыс уақыты мен қолжетімділік расталмайды."),
    "Точки крупных объектов могут быть центрами территории, а не входами.": (
        "Points for large sites may be centers rather than entrances.",
        "Ірі нысан нүктелері кіреберіс емес, аумақтың ортасы болуы мүмкін."),
    "Время посещения — эвристика по категории, не данные объекта.": (
        "Visit duration is a category-based estimate, not a place-specific fact.",
        "Бару ұзақтығы — нысан дерегі емес, санат бойынша баға."),
    "Лексический поиск и правила понимают ограниченный набор условий.": (
        "Lexical search and rules understand a limited set of conditions.",
        "Сөздік іздеу мен ережелер шарттардың шектеулі жиынын түсінеді."),
}

CATEGORIES = {
    "кафе": ("café", "кафе"), "парк": ("park", "саябақ"), "сад": ("garden", "бақ"),
    "детская площадка": ("playground", "балалар алаңы"), "музей": ("museum", "музей"),
    "галерея": ("gallery", "галерея"), "достопримечательность": ("landmark", "көрікті орын"),
    "смотровая площадка": ("viewpoint", "шолу алаңы"), "арт-объект": ("artwork", "өнер нысаны"),
    "памятник": ("monument", "ескерткіш"), "мемориал": ("memorial", "мемориал"),
    "торговый центр": ("shopping center", "сауда орталығы"),
    "mall": ("shopping center", "сауда орталығы"),
}
FEATURES = {
    "розетки": ("power sockets", "электр розеткалары"), "Wi-Fi": ("Wi-Fi", "Wi-Fi"),
    "тишина": ("quietness", "тыныштық"),
    "доступность для кресла-коляски": ("wheelchair access", "мүгедектер арбасына қолжетімділік"),
}
FOOD = {
    "кофе": ("coffee", "кофе"), "завтраки": ("breakfast", "таңғы ас"),
    "десерты": ("desserts", "десерттер"), "русская кухня": ("Russian cuisine", "орыс асханасы"),
    "европейская кухня": ("European cuisine", "еуропалық асхана"),
    "итальянская кухня": ("Italian cuisine", "итальян асханасы"), "паста": ("pasta", "паста"),
    "пончики": ("doughnuts", "пончиктер"), "блины": ("pancakes", "құймақ"),
    "бургеры": ("burgers", "бургерлер"), "блюда на гриле": ("grilled dishes", "гриль тағамдары"),
    "блюда из курицы": ("chicken dishes", "тауық тағамдары"), "рыба": ("fish", "балық"),
    "местная кухня": ("local cuisine", "жергілікті асхана"), "закуски": ("snacks", "жеңіл тағамдар"),
}


def _choice(pair: tuple[str, str], locale: str) -> str:
    return pair[0 if locale == "en" else 1]


def _list(value: str, mapping: dict, locale: str, separator: str = ", ") -> str | None:
    values = value.split(separator)
    if not all(item in mapping for item in values):
        return None
    return separator.join(_choice(mapping[item], locale) for item in values)


def _known(sentence: str, locale: str) -> str | None:
    if sentence in PHRASES:
        return _choice(PHRASES[sentence], locale)
    category = sentence.rstrip(".").casefold()
    if category in CATEGORIES:
        return _choice(CATEGORIES[category], locale).capitalize() + ("." if sentence.endswith(".") else "")
    patterns = [
        (r"Около (\d+) мин с возвращением: (\d+) мин на месте и примерно по (\d+) мин в каждую сторону\.",
         "About {0} min including the return: {1} min at the place and about {2} min each way.",
         "Қайтуды қосқанда шамамен {0} мин: орында {1} мин және әр бағытта шамамен {2} мин."),
        (r"Находится примерно в (\d+) м по прямой от выбранной точки\.",
         "About {0} m in a straight line from the selected point.", "Таңдалған нүктеден тікелей шамамен {0} м."),
        (r"На эту остановку отведено (\d+) мин в пределах общего бюджета с возвращением\.",
         "This stop has {0} min within the total budget including the return.",
         "Бұл аялдамаға қайтуды қамтитын жалпы уақыт ішінде {0} мин бөлінген."),
        (r"Итого примерно (\d+) из (\d+) мин\.", "About {0} of {1} min in total.", "Барлығы шамамен {1} минуттың {0} минуты."),
        (r"Название в OpenStreetMap: (.+)\.", "Name recorded in OpenStreetMap: {0}.", "OpenStreetMap-тағы атауы: {0}."),
        (r"Адрес в OSM: (.+)\.", "Address in OSM: {0}.", "OSM-дегі мекенжайы: {0}."),
        (r"Архитектор по данным OSM: (.+)\.", "Architect according to OSM: {0}.", "OSM бойынша сәулетшісі: {0}."),
        (r"Автор по данным OSM: (.+)\.", "Creator according to OSM: {0}.", "OSM бойынша авторы: {0}."),
        (r"Вид растений по данным OSM: (.+)\.", "Plant species according to OSM: {0}.", "OSM бойынша өсімдік түрі: {0}."),
        (r"Указанная в OSM высота объекта — ([\d.]+) м\.", "OSM reports a height of {0} m.", "OSM-де биіктігі {0} м деп көрсетілген."),
        (r"Указанная в OSM дата создания или открытия объекта — ([\d-]+)\.",
         "OSM gives {0} as the creation or opening date.", "OSM-де құрылу немесе ашылу күні {0} деп көрсетілген."),
        (r"Осадки указаны в мм за предыдущие (\d+) мин, а не в мм/ч\.",
         "Precipitation is in mm over the previous {0} min, not mm/hour.",
         "Жауын-шашын мм/сағ емес, алдыңғы {0} минуттағы мм мөлшерімен берілген."),
        (r"Если заведение доступно, возьмите кофе и сделайте перерыв примерно на (\d+) мин; меню и цены уточните на месте\.",
         "If the café is accessible, get a coffee and take a break for about {0} min; check the menu and prices on arrival.",
         "Кафе қолжетімді болса, кофе алып, шамамен {0} мин демалыңыз; мәзір мен бағаларды сол жерде нақтылаңыз."),
        (r"Если заведение доступно, узнайте о кофе с собой; выделите около (\d+) мин на заказ и короткую паузу\.",
         "If the café is accessible, ask about takeaway coffee; allow about {0} min to order and take a short break.",
         "Кафе қолжетімді болса, өзіңізбен кофе алып кетуді сұраңыз; тапсырыс пен қысқа үзіліске шамамен {0} мин бөліңіз."),
        (r"Если вход доступен, прогуляйтесь около (\d+) мин и возвращайтесь к стартовой точке\.",
         "If access is available, walk for about {0} min and return to the starting point.",
         "Кіруге мүмкіндік болса, шамамен {0} мин серуендеп, бастапқы нүктеге қайтыңыз."),
        (r"Выделите около (\d+) мин на спокойную прогулку и поиск интересного кадра\.",
         "Allow about {0} min for a relaxed walk and an interesting photograph.",
         "Жай серуен мен қызықты суретке шамамен {0} мин бөліңіз."),
        (r"Если посещение возможно, выделите около (\d+) мин на короткий осмотр\.",
         "If a visit is possible, allow about {0} min for a short look around.",
         "Бару мүмкін болса, қысқа шолуға шамамен {0} мин бөліңіз."),
        (r"Если место доступно, выделите примерно (\d+) мин на осмотр и фотографии с разрешённой общедоступной точки\.",
         "If the place is accessible, allow about {0} min to look around and take photos from a permitted public spot.",
         "Орын қолжетімді болса, рұқсат етілген қоғамдық нүктеден қарау мен суретке шамамен {0} мин бөліңіз."),
        (r"Сделайте остановку примерно на (\d+) мин, осмотрите объект и затем возвращайтесь\.",
         "Stop for about {0} min, look at the place and then return.",
         "Шамамен {0} мин тоқтап, нысанды қарап, кейін қайтыңыз."),
        (r"Выделите около (\d+) мин на игру вместе с ребёнком\.",
         "Allow about {0} min to play together with your child.", "Баламен бірге ойнауға шамамен {0} мин бөліңіз."),
        (r"Рассмотрите объект с двух доступных общественных точек и сравните силуэт; на осмотр и фотографию выделите около (\d+) мин\.",
         "View the object from two accessible public spots and compare its silhouette; allow about {0} min for viewing and a photo.",
         "Нысанды қолжетімді екі қоғамдық нүктеден қарап, сұлбасын салыстырыңыз; қарау мен суретке шамамен {0} мин бөліңіз."),
        (r"На заказ и паузу — около (\d+) мин\.", "Allow about {0} min to order and take a break.", "Тапсырыс пен үзіліске шамамен {0} мин."),
        (r"Выделите около (\d+) мин; зимой камни могут быть укрыты\.",
         "Allow about {0} min; the stones may be covered in winter.", "Шамамен {0} мин бөліңіз; қыста тастар жабылуы мүмкін."),
        (r"За примерно (\d+) мин осмотрите арку с доступной общественной дорожки: найдите национальные орнаменты и барельефы, выберите общий ракурс для фотографии\.",
         "Spend about {0} min viewing the arch from an accessible public path: look for national ornaments and reliefs, and choose a wide view for a photograph.",
         "Шамамен {0} мин арканы қолжетімді қоғамдық жолдан қараңыз: ұлттық оюлар мен барельефтерді тауып, суретке жалпы көріністі таңдаңыз."),
        (r"Если сад доступен, выберите один из тематических участков у центральной части и сравните посадки; выделите около (\d+) мин\.",
         "If the garden is accessible, choose a themed area near the center and compare the plantings; allow about {0} min.",
         "Бақ қолжетімді болса, орталыққа жақын тақырыптық аумақты таңдап, өсімдіктерді салыстырыңыз; шамамен {0} мин бөліңіз."),
        (r"Если всё подходит, выделите примерно (\d+) мин на игру под присмотром\.",
         "If suitable, allow about {0} min for supervised play.",
         "Қолайлы болса, бақылаумен ойнауға шамамен {0} мин бөліңіз."),
        (r"Для найденного маршрута нужно ориентировочно от (\d+) мин; увеличьте и поле времени, и ограничение в тексте, если оно есть\.",
         "The found route needs roughly at least {0} min; increase both the time selector and any time limit in the text.",
         "Табылған бағытқа шамамен кемінде {0} мин керек; уақыт өрісін және мәтіндегі уақыт шегін де арттырыңыз."),
    ]
    for pattern, english, kazakh in patterns:
        match = re.fullmatch(pattern, sentence)
        if match:
            return (english if locale == "en" else kazakh).format(*match.groups())
    match = re.fullmatch(r"По данным OpenStreetMap это (.+)\.", sentence)
    if match and match[1] in CATEGORIES:
        category = _choice(CATEGORIES[match[1]], locale)
        return f"According to OpenStreetMap, this is a {category}." if locale == "en" else f"OpenStreetMap дерегі бойынша бұл — {category}."
    match = re.fullmatch(r"В OSM объект описан как (скульптура|статуя|инсталляция|настенная роспись)\.", sentence)
    if match:
        artwork = _choice({"скульптура": ("sculpture", "мүсін"), "статуя": ("statue", "мүсін"),
                           "инсталляция": ("installation", "инсталляция"),
                           "настенная роспись": ("mural", "қабырға суреті")}[match[1]], locale)
        return f"OSM describes the object as a {artwork}." if locale == "en" else f"OSM нысанды {artwork} деп сипаттайды."
    for prefix, mapping, english, kazakh in [
        ("В OSM отмечены: ", FOOD, "OSM reports: ", "OSM-де көрсетілген: "),
        ("В источнике отмечены нужные свойства: ", FEATURES, "The source reports the required features: ", "Дереккөзде қажетті қасиеттер көрсетілген: "),
        ("В источнике отмечены: ", FEATURES, "The source reports: ", "Дереккөзде көрсетілген: "),
        ("Не подтверждены условия: ", FEATURES, "Unconfirmed conditions: ", "Расталмаған шарттар: "),
        ("Требуемые свойства проверяются для каждой остановки: ", FEATURES, "Required features are checked for every stop: ", "Қажетті қасиеттер әр аялдама үшін тексеріледі: "),
    ]:
        if sentence.startswith(prefix) and sentence.endswith("."):
            values = _list(sentence[len(prefix):-1], mapping, locale)
            if values is not None:
                return (english if locale == "en" else kazakh) + values + "."
    match = re.fullmatch(r"(.+): (\d+) разных места, (\d+) мин на все переходы включая возвращение, (\d+) мин на остановки и (\d+) мин запаса\.", sentence)
    if match:
        categories = _list(match[1], CATEGORIES, locale, " → ")
        if categories:
            _, count, walking, visiting, reserve = match.groups()
            return (
                f"{categories}: {count} distinct places, {walking} min walking including the return, {visiting} min at stops and {reserve} min reserve."
                if locale == "en" else
                f"{categories}: {count} бөлек орын, қайтуды қосқанда {walking} мин жүру, аялдамаларға {visiting} мин және {reserve} мин қор."
            )
    return None


def translate_text(value: str, locale: Locale) -> str:
    if locale == "ru" or not value:
        return value
    index = 0 if locale == "en" else 1
    marker = ("[Original source text] ", "[Дереккөз мәтіні: түпнұсқа] ")[index]
    if value.startswith(marker):
        return value
    translated = _known(value, locale)
    if translated is not None:
        return translated
    sentences = re.split(r"(?<=[.!?])\s+", value.strip())
    result = []
    for sentence in sentences:
        translated = _known(sentence, locale)
        if translated is None:
            translated = marker + sentence if re.search(r"[А-Яа-яЁё]", sentence) else sentence
        result.append(translated)
    return " ".join(result)


def localize_response(payload: dict, locale: Locale = "ru") -> dict:
    """Return a new JSON-shaped response; IDs, dates, URLs and names are untouched."""
    if locale not in {"ru", "kz", "en"}:
        raise ValueError("Unsupported locale")
    if locale == "ru":
        return deepcopy(payload)

    def visit(value, key=None):
        if key == "tags":
            return deepcopy(value)
        if isinstance(value, dict):
            return {k: visit(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [translate_text(item, locale) if isinstance(item, str) and key in TEXT_LIST_KEYS
                    else visit(item) for item in value]
        if isinstance(value, str) and key in TEXT_KEYS:
            return translate_text(value, locale)
        return value

    return visit(payload)
