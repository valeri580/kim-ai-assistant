"""HTTP-клиент для веб-поиска через SerpAPI или DuckDuckGo."""

import re
from html import unescape
from typing import Optional
from urllib.parse import quote, unquote

import httpx

from kim_core.logging import logger


class WebSearchClient:
    """Клиент для выполнения веб-поиска."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10) -> None:
        """
        Инициализирует клиент веб-поиска.

        Args:
            api_key: API-ключ SerpAPI (если есть, будет использоваться SerpAPI)
            timeout: Таймаут запроса в секундах
        """
        self.api_key = api_key
        self.timeout = timeout
        self.use_serpapi = bool(api_key)
        if self.use_serpapi:
            logger.info("WebSearchClient: используется SerpAPI")
        else:
            logger.info("WebSearchClient: используется DuckDuckGo (fallback)")

    async def search(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Выполняет поиск в интернете.

        Args:
            query: Поисковый запрос
            num_results: Количество результатов

        Returns:
            Список словарей с результатами: [{"title": "...", "snippet": "...", "link": "..."}, ...]
        """
        if not query or not query.strip():
            logger.warning("Пустой поисковый запрос")
            return []

        query = query.strip()

        try:
            if self.use_serpapi:
                return await self._search_serpapi(query, num_results)
            else:
                return await self._search_duckduckgo(query, num_results)
        except Exception as e:
            logger.error(f"Ошибка веб-поиска для запроса '{query}': {e}")
            return []

    async def _search_serpapi(self, query: str, num_results: int) -> list[dict]:
        """
        Выполняет поиск через SerpAPI.

        Args:
            query: Поисковый запрос
            num_results: Количество результатов

        Returns:
            Список результатов
        """
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": min(num_results, 20),  # SerpAPI ограничение
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            organic_results = data.get("organic_results", [])

            for item in organic_results[:num_results]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")

                if title or snippet or link:
                    results.append({
                        "title": self._clean_html(title),
                        "snippet": self._clean_html(snippet),
                        "link": link,
                    })

            logger.info(f"SerpAPI: найдено {len(results)} результатов для '{query}'")
            return results

    async def _search_duckduckgo(self, query: str, num_results: int) -> list[dict]:
        """
        Выполняет поиск через DuckDuckGo HTML (fallback).

        Args:
            query: Поисковый запрос
            num_results: Количество результатов

        Returns:
            Список результатов
        """
        # Используем HTML-версию DuckDuckGo Lite
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        data = {"q": query}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()
            html = response.text

            # Парсим HTML-ответ
            results = self._parse_ddg_html(html, num_results)

            logger.info(f"DuckDuckGo: найдено {len(results)} результатов для '{query}'")
            return results

    def _parse_ddg_html(self, html: str, max_results: int) -> list[dict]:
        """
        Парсит HTML-ответ DuckDuckGo.

        Args:
            html: HTML-содержимое страницы
            max_results: Максимальное количество результатов

        Returns:
            Список результатов
        """
        results = []

        # Паттерны для поиска результатов в HTML DuckDuckGo
        # DuckDuckGo Lite использует классы result, result__title, result__snippet и т.д.
        # Ищем блоки результатов
        result_pattern = re.compile(
            r'<div class="result[^"]*">.*?</div>\s*(?=<div class="result|</body>)',
            re.DOTALL,
        )

        matches = result_pattern.findall(html)
        for match in matches[:max_results]:
            # Извлекаем заголовок
            title_match = re.search(
                r'<a[^>]*class="result__a[^"]*"[^>]*>(.*?)</a>',
                match,
                re.DOTALL,
            )
            title = title_match.group(1).strip() if title_match else ""

            # Извлекаем ссылку
            link_match = re.search(
                r'<a[^>]*class="result__a[^"]*"[^>]*href="([^"]+)"',
                match,
            )
            link = link_match.group(1).strip() if link_match else ""

            # Извлекаем сниппет
            snippet_match = re.search(
                r'<a[^>]*class="result__snippet[^"]*"[^>]*>(.*?)</a>',
                match,
                re.DOTALL,
            )
            snippet = snippet_match.group(1).strip() if snippet_match else ""

            # Если нет сниппета в result__snippet, ищем в другом месте
            if not snippet:
                snippet_match = re.search(
                    r'<span[^>]*class="result__snippet[^"]*"[^>]*>(.*?)</span>',
                    match,
                    re.DOTALL,
                )
                snippet = snippet_match.group(1).strip() if snippet_match else ""

            # Очищаем HTML-теги
            title = self._clean_html(title)
            snippet = self._clean_html(snippet)

            # Декодируем HTML-сущности
            title = unescape(title)
            snippet = unescape(snippet)

            if title or snippet or link:
                results.append({
                    "title": title or "Без заголовка",
                    "snippet": snippet or "Без описания",
                    "link": link or "",
                })

        return results

    def _clean_html(self, text: str) -> str:
        """
        Удаляет HTML-теги из текста.

        Args:
            text: Текст с HTML-тегами

        Returns:
            Очищенный текст
        """
        if not text:
            return ""

        # Удаляем HTML-теги
        text = re.sub(r"<[^>]+>", "", text)
        # Удаляем множественные пробелы
        text = re.sub(r"\s+", " ", text)
        # Обрезаем пробелы по краям
        return text.strip()

