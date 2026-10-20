"""Conservative scenario constraints shared by search and itineraries."""
import re
from app.facts import facts_for


def scenario_flags(query: str) -> tuple[str, ...]:
    q = query.lower()
    q = re.sub(r"ноч\w*\s+прогул\w*\s+не\s+нуж\w*|no\s+night\s+walk|без\s+ноч\w*\s+прогул\w*", "", q)
    flags = []
    if re.search(r"реб[её]н\w*|детьми|детск\w*|children|child\b|kids?\b", q):
        flags.append("family")
    if re.search(r"\b(?:ноч\w*|night\w*|круглосуточ\w*)\b", q):
        flags.append("night")
    if re.search(r"\b(?:турист\w*|tourist\w*|sightseeing|впервые)\b", q):
        flags.append("tourist")
    return tuple(flags)


def scenario_rejection(query: str) -> str:
    q = query.lower()
    if re.search(r"открыт\w*\s+сейчас|сейчас\s+открыт\w*|open\s+now|вылет\w*|аэропорт\w*|flight|airport", q):
        return "Доступность сейчас и время поездки в аэропорт не проверяются. Нельзя обещать посещение до вылета."
    if re.search(r"коляск\w*|stroller|без\s+(?:лестниц\w*|ступен\w*)|no\s+stairs|step[ -]?free", q):
        return "Доступность всего пути с коляской, отсутствие лестниц и доступность входов не подтверждены."
    if re.search(r"аллерг\w*|allerg\w*|игров\w*\s+зон\w*|play\s+area|live\s+music|жив\w*\s+музык\w*|ночн\w*\s+клуб\w*|nightclub|вечерин\w*|концерт\w*", q):
        return "В источниках нет подтверждения указанного специального условия. Оно не будет заменено обычной рекомендацией."
    if re.search(r"интерактив\w*|interactive", q):
        return "Подтверждённых действующих интерактивных экспозиций в текущем датасете нет. Можно отдельно искать детские площадки или обычную прогулку."
    if re.search(r"\b(?:бесплат\w*|деш[её]в\w*|бюджетн\w*|бюджет\s+(?:до\s+)?\d+(?!\d)(?!\s*(?:минут\w*|мин\b|час\w*|ч\b))|\d+\s*(?:₸|тенге|тг\b)|под\s+крышей|в\s+помещении)", q):
        return "В данных недостаточно сведений для подтверждения дополнительного условия. Уточните запрос."
    return ""


def scenario_allows(poi, query: str) -> bool:
    flags = scenario_flags(query)
    if poi.category == "playground" and "family" not in flags and not re.search(r"playground|площадк", query.lower()):
        return False
    if "family" in flags and poi.category != "cafe":
        explicit_museum = bool(re.search(r"музе|museum|галере|gallery", query.lower()))
        if not explicit_museum and poi.category not in {"park", "garden", "playground"}:
            return False
    if "tourist" in flags and "family" not in flags and poi.category in {"playground", "mall"}:
        return False
    if "night" in flags:
        official_all_day = any(f["id"] == "official_hours_24_7" for f in facts_for(poi))
        all_day = poi.opening_hours == "24/7" or official_all_day
        lit_outdoor = (poi.tags.get("lit") == "yes" and not poi.opening_hours
                       and poi.category in {"park", "garden", "attraction", "artwork", "monument", "memorial", "viewpoint"})
        if not (all_day or lit_outdoor):
            return False
    return True


def scenario_warnings(query: str) -> list[str]:
    flags = scenario_flags(query)
    notes = []
    if "night" in flags:
        notes.append("Ночной вариант основан на указанном в источнике режиме 24/7 или освещении. Фактический доступ, безопасность и освещение всего пути ночью не проверены; смотровые и внутренние помещения могут иметь отдельный режим.")
    if "family" in flags:
        notes.append("Возрастные ограничения и состояние оборудования не проверены. Время ходьбы рассчитано для общего темпа; с ребёнком может понадобиться больше времени.")
    return notes
