"""Парсинг и нормализация результатов веб-поиска."""

from typing import Any


def normalize_results(raw_results: list[dict], limit: int = 5) -> list[dict]:
    """
    Нормализует результаты поиска.

    Args:
        raw_results: Сырые результаты поиска
        limit: Максимальное количество результатов

    Returns:
        Список нормализованных результатов
    """
    normalized = []

    for item in raw_results[:limit]:
        # Гарантируем наличие обязательных полей
        normalized_item = {
            "title": str(item.get("title", "")).strip() or "Без заголовка",
            "snippet": str(item.get("snippet", "")).strip() or "Без описания",
            "link": str(item.get("link", "")).strip() or "",
        }

        # Ограничиваем длину полей (чтобы не было слишком длинных ответов)
        normalized_item["title"] = normalized_item["title"][:200]
        normalized_item["snippet"] = normalized_item["snippet"][:300]

        normalized.append(normalized_item)

    return normalized


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

