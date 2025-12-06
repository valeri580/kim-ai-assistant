"""Парсинг и нормализация результатов веб-поиска."""

from typing import Any

# Известные СМИ для рейтинга
KNOWN_MEDIA = {
    "bbc.com", "bbc.co.uk", "cnn.com", "reuters.com", "ap.org", "theguardian.com",
    "nytimes.com", "washingtonpost.com", "wsj.com", "bloomberg.com", "forbes.com",
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    "lenta.ru", "ria.ru", "tass.ru", "rbc.ru", "kommersant.ru", "vedomosti.ru",
    "gazeta.ru", "interfax.ru", "rt.com", "sputniknews.com",
}


def get_domain_rating(domain: str) -> int:
    """
    Возвращает рейтинг домена для сортировки результатов.

    Args:
        domain: Домен (например, "example.gov")

    Returns:
        Рейтинг: 3 (высокий), 2 (средний), 1 (низкий)
    """
    if not domain:
        return 1

    domain_lower = domain.lower()

    # Высокий приоритет: .gov, .edu
    if domain_lower.endswith(".gov") or domain_lower.endswith(".edu"):
        return 3

    # Средний приоритет: известные СМИ
    if domain_lower in KNOWN_MEDIA:
        return 2

    # Низкий приоритет: остальные домены
    return 1


def normalize_results(raw_results: list[dict], limit: int = 5) -> list[dict]:
    """
    Нормализует результаты поиска и сортирует по рейтингу доменов.

    Args:
        raw_results: Сырые результаты поиска
        limit: Максимальное количество результатов

    Returns:
        Список нормализованных результатов, отсортированных по рейтингу
    """
    normalized = []

    for item in raw_results:
        # Гарантируем наличие обязательных полей
        url = str(item.get("url", "") or item.get("link", "")).strip()
        source_name = str(item.get("source_name", "")).strip()
        
        # Если source_name не указан, извлекаем из URL
        if not source_name and url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                domain = parsed.netloc or parsed.path
                if domain.startswith("www."):
                    domain = domain[4:]
                source_name = domain
            except Exception:
                pass

        normalized_item = {
            "title": str(item.get("title", "")).strip() or "Без заголовка",
            "snippet": str(item.get("snippet", "")).strip() or "Без описания",
            "short_snippet": str(item.get("short_snippet", "")).strip() or "",
            "url": url,
            "link": url,  # Для обратной совместимости
            "source_name": source_name,
        }

        # Ограничиваем длину полей (чтобы не было слишком длинных ответов)
        normalized_item["title"] = normalized_item["title"][:200]
        normalized_item["snippet"] = normalized_item["snippet"][:300]
        if not normalized_item["short_snippet"]:
            normalized_item["short_snippet"] = normalized_item["snippet"][:100]
            if len(normalized_item["snippet"]) > 100:
                normalized_item["short_snippet"] += "..."

        # Добавляем рейтинг для сортировки
        normalized_item["rating"] = get_domain_rating(source_name)

        normalized.append(normalized_item)

    # Сортируем по рейтингу (высокий рейтинг первым), сохраняя исходный порядок для одинаковых рейтингов
    # Используем enumerate для сохранения исходного индекса
    indexed = list(enumerate(normalized))
    indexed.sort(key=lambda x: (-x[1].get("rating", 1), x[0]))
    normalized = [item[1] for item in indexed]

    return normalized[:limit]


def summarize_results(results: list[dict]) -> str:
    """
    Создаёт краткое человеческое описание результатов поиска.

    Args:
        results: Список нормализованных результатов

    Returns:
        Текстовое описание результатов
    """
    if not results:
        return "По запросу ничего не найдено."

    count = len(results)
    summary_parts = [f"Нашёл {count} {'результат' if count == 1 else 'результата' if count < 5 else 'результатов'}:"]

    for i, result in enumerate(results, 1):
        title = result.get("title", "Без заголовка")
        snippet = result.get("snippet", "")
        link = result.get("link", "")

        summary_parts.append(f"\n{i}. {title}")
        if snippet:
            summary_parts.append(f"   {snippet}")
        if link:
            # Сокращаем длинные ссылки для голосового вывода
            if len(link) > 60:
                link = link[:57] + "..."
            summary_parts.append(f"   Ссылка: {link}")

    return "\n".join(summary_parts)


def create_voice_summary(results: list[dict]) -> str:
    """
    Создаёт короткую выжимку для голосового вывода.

    Args:
        results: Список нормализованных результатов

    Returns:
        Короткая выжимка для голосового вывода
    """
    if not results:
        return "По запросу ничего не найдено."

    count = len(results)
    
    # Формируем короткую выжимку из первых результатов
    main_points = []
    for result in results[:3]:  # Берём до 3 результатов
        short_snippet = result.get("short_snippet", "") or result.get("snippet", "")[:100]
        if short_snippet:
            main_points.append(short_snippet.strip())

    if main_points:
        summary = f"Нашла {count} {'источник' if count == 1 else 'источника' if count < 5 else 'источников'}. Главное: {' '.join(main_points[:2])}"
        # Ограничиваем длину для голосового вывода
        if len(summary) > 400:
            summary = summary[:397] + "..."
        return summary
    
    return f"Нашла {count} {'источник' if count == 1 else 'источника' if count < 5 else 'источников'}."

