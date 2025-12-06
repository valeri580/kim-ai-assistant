"""Модуль для генерации резюме файлов через LLM."""

from kim_core.config.settings import AppConfig
from kim_core.llm import LLMRouter
from kim_core.logging import logger
from kim_desktop.files.reader import truncate_text


async def summarize_text_with_llm(
    text: str,
    llm_router: LLMRouter,
    config: AppConfig,
) -> str:
    """
    Генерирует краткое резюме текста через LLM.

    Args:
        text: Исходный текст файла
        llm_router: Маршрутизатор LLM
        config: Конфигурация приложения

    Returns:
        Краткое резюме текста
    """
    # Обрезаем текст до максимальной длины перед отправкой в LLM
    original_length = len(text)
    truncated_text = truncate_text(text, config.file_summary_max_chars)
    final_length = len(truncated_text)
    
    if original_length > final_length:
        logger.info(
            f"Текст обрезан перед отправкой в LLM: "
            f"{original_length} → {final_length} символов"
        )
    else:
        logger.info(f"Текст отправляется в LLM без обрезки: {original_length} символов")

    # Формируем системное сообщение
    system_message = {
        "role": "system",
        "content": (
            "Ты помощник, который делает краткие выжимки из документов. "
            "Дай структурированное резюме и основные тезисы. "
            "Не придумывай факты, которых нет в тексте."
        ),
    }

    # Формируем пользовательское сообщение
    user_message = {
        "role": "user",
        "content": (
            f"Вот содержимое файла:\n\n{truncated_text}\n\n"
            "Сделай краткое резюме и выдели ключевые моменты."
        ),
    }

    messages = [system_message, user_message]

    try:
        logger.info("Отправка запроса в LLM для генерации резюме...")
        
        # Вызываем LLM с ограничением токенов для краткого ответа
        summary = await llm_router.run(messages, max_tokens=512, temperature=0.5)
        
        logger.info(f"Резюме сгенерировано, длина: {len(summary)} символов")
        return summary

    except Exception as e:
        error_msg = f"Ошибка при генерации резюме через LLM: {e}"
        logger.error(error_msg, exc_info=True)
        # Возвращаем усечённую версию исходного текста как fallback
        fallback = truncate_text(text, 500)
        return f"Не удалось сгенерировать резюме. Первые 500 символов файла:\n\n{fallback}"

