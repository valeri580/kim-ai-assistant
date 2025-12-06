"""Модуль веб-поиска для ассистента."""

from kim_tools.web_search.client import WebSearchClient
from kim_tools.web_search.parser import normalize_results, summarize_results
from kim_tools.web_search.tools import WebSearchTool

__all__ = ["WebSearchClient", "WebSearchTool", "normalize_results", "summarize_results"]

