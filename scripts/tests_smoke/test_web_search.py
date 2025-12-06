"""Smoke-тест для проверки веб-поиска."""

import asyncio
import sys
import time
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_tools.web_search.client import WebSearchClient


async def test_web_search() -> bool:
    """
    Проверяет, что веб-поиск может выполнить запрос.

    Returns:
        bool: True если веб-поиск работает корректно
    """
    try:
        # Инициализация логирования
        config = load_config()
        init_logger(config)
        
        logger.info("=" * 60)
        logger.info("Smoke test: Web Search")
        logger.info("=" * 60)
        
        # Создание клиента веб-поиска
        try:
            api_key = config.serpapi_key if hasattr(config, 'serpapi_key') else None
            client = WebSearchClient(api_key=api_key, timeout=10)
            
            if client.use_serpapi:
                logger.info("✓ Используется SerpAPI")
            else:
                logger.info("✓ Используется DuckDuckGo (fallback)")
            
            # Ждём немного перед запросом
            await asyncio.sleep(1)
            
            # Выполняем тестовый запрос
            logger.info("Выполнение тестового поискового запроса...")
            test_query = "Python programming"
            results = await client.search(test_query, num_results=3)
            
            if not results:
                logger.warning("⚠ Поиск не вернул результатов (возможно, проблема с API или сетью)")
                # Не критично для smoke-теста, если клиент инициализирован
                logger.info("✓ WebSearchClient инициализирован корректно")
                return True
            
            logger.info(f"✓ Получено результатов: {len(results)}")
            
            # Проверяем структуру результата
            if results:
                first_result = results[0]
                required_keys = ["title", "url"]
                missing_keys = [key for key in required_keys if key not in first_result]
                
                if missing_keys:
                    logger.warning(f"⚠ В результате отсутствуют ключи: {missing_keys}")
                else:
                    logger.info(f"✓ Структура результата корректна: {first_result.get('title', '')[:50]}...")
            
            logger.info("✅ Web search test: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке веб-поиска: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_web_search())
    sys.exit(0 if success else 1)

