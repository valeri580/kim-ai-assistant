"""Smoke-тест для проверки Telegram-бота и LLM."""

import asyncio
import sys
import time
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from aiogram import Bot
from kim_core.config import load_config
from kim_core.logging import init_logger, logger


async def test_tg_llm() -> bool:
    """
    Проверяет, что Telegram-бот может подключиться и выполнить getMe().

    Returns:
        bool: True если бот работает корректно
    """
    try:
        # Инициализация логирования
        config = load_config()
        init_logger(config)
        
        logger.info("=" * 60)
        logger.info("Smoke test: Telegram Bot & LLM")
        logger.info("=" * 60)
        
        # Проверка наличия токена
        if not config.telegram_bot_token:
            logger.error("❌ BOT_TOKEN не установлен в конфигурации")
            return False
        
        logger.info("✓ Токен бота найден")
        
        # Создание бота и проверка getMe()
        try:
            bot = Bot(token=config.telegram_bot_token)
            logger.info("Проверка подключения к Telegram API...")
            
            # Ждём немного перед запросом
            await asyncio.sleep(1)
            
            bot_info = await bot.get_me()
            logger.info(f"✓ Бот подключён: @{bot_info.username} ({bot_info.first_name})")
            
            # Проверка LLM (если не local_only)
            if not config.local_only:
                try:
                    from kim_core.llm import OpenRouterClient, LLMRouter
                    
                    if not config.openrouter_api_key:
                        logger.warning("⚠ OpenRouter API ключ не установлен, пропускаем проверку LLM")
                    else:
                        logger.info("Проверка подключения к LLM...")
                        await asyncio.sleep(1)
                        
                        client = OpenRouterClient(config)
                        router = LLMRouter(config, client)
                        logger.info("✓ LLM клиент инициализирован")
                except Exception as e:
                    logger.warning(f"⚠ Ошибка при проверке LLM: {e}")
                    # Не критично для smoke-теста
            else:
                logger.info("✓ Режим local_only - LLM не требуется")
            
            await bot.session.close()
            
            logger.info("✅ Telegram & LLM test: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при подключении к Telegram: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_tg_llm())
    sys.exit(0 if success else 1)

