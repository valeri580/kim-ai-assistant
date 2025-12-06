"""LLM tool для веб-поиска."""

from pydantic import BaseModel

from kim_tools.web_search.client import WebSearchClient
from kim_tools.web_search.parser import normalize_results


class WebSearchRequest(BaseModel):
    """Модель запроса для веб-поиска."""

    query: str
    num_results: int = 5


class WebSearchTool:
    """Инструмент веб-поиска для LLM."""

    name = "web_search"
    description = (
        "Поиск в интернете для получения свежей информации. "
        "Используй этот инструмент, когда нужно найти актуальную информацию в интернете, "
        "проверить факты или получить свежие данные. "
        "Параметры: query (строка запроса, обязательно), num_results (количество результатов, по умолчанию 5)."
    )
    request_model = WebSearchRequest

    def __init__(self, client: WebSearchClient) -> None:
        """
        Инициализирует инструмент веб-поиска.

        Args:
            client: Клиент веб-поиска
        """
        self.client = client

    async def run(self, request: WebSearchRequest) -> dict:
        """
        Выполняет веб-поиск.

        Args:
            request: Запрос на поиск

        Returns:
            Словарь с результатами поиска
        """
        results = await self.client.search(request.query, request.num_results)
        normalized = normalize_results(results, request.num_results)

        return {
            "results": normalized,
            "count": len(normalized),
            "query": request.query,
        }

