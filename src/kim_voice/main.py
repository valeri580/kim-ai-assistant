"""Точка входа голосового ассистента (локально, Windows)."""

import asyncio
import os
import sys

from dotenv import load_dotenv

from kim_core.config import load_config
from kim_core.llm import BudgetExceededError, LLMError, LLMRouter, OpenRouterClient
from kim_core.logging import init_logger, logger
from kim_core.prompts import get_system_prompt
from kim_voice.hotword.kim_hotword import HotwordConfig, KimHotwordListener
from kim_voice.stt.speech_to_text import KimSTT, STTConfig
from kim_voice.tts.voice import KimVoice


def get_vosk_model_path() -> str:
    """
    Получает путь к модели Vosk из переменной окружения или возвращает значение по умолчанию.

    Returns:
        str: Путь к модели Vosk
    """
    load_dotenv()

    # Проверяем переменную окружения
    model_path = os.getenv("VOSK_MODEL_PATH")

    if model_path:
        return model_path

    # Значение по умолчанию
    default_path = "models/vosk-ru"

    if not os.path.exists(default_path):
        logger.warning(
            f"Модель Vosk не найдена по пути по умолчанию: {default_path}. "
            f"Установите переменную окружения VOSK_MODEL_PATH"
        )

    return default_path


def main() -> None:
    """Основная функция запуска голосового ассистента."""
    # Загрузка конфигурации
    config = load_config()

    # Инициализация логирования
    init_logger(config)

    logger.info("=" * 60)
    logger.info("Запуск голосового ассистента «Ким»")
    logger.info("=" * 60)

    # Проверка наличия VOSK_MODEL_PATH
    model_path = get_vosk_model_path()

    if not model_path or not os.path.exists(model_path):
        error_msg = (
            f"Модель Vosk не найдена!\n"
            f"Пожалуйста:\n"
            f"1. Скачайте модель Vosk (например, русскую) с https://alphacephei.com/vosk/models\n"
            f"2. Распакуйте её в папку models/vosk-ru\n"
            f"3. Или укажите путь через переменную окружения VOSK_MODEL_PATH в .env"
        )
        logger.error(error_msg)
        print(f"\n❌ ОШИБКА: {error_msg}\n")
        sys.exit(1)

    logger.info(f"Используется модель Vosk: {model_path}")

    # Проверка наличия OPENROUTER_API_KEY (только если не включён режим local_only)
    if not config.local_only:
        if not config.openrouter_api_key:
            error_msg = (
                "OPENROUTER_API_KEY не установлен!\n"
                "Пожалуйста, добавьте OPENROUTER_API_KEY в файл .env\n"
                "Или включите режим LOCAL_ONLY=1 для работы без LLM"
            )
            logger.error(error_msg)
            print(f"\n❌ ОШИБКА: {error_msg}\n")
            sys.exit(1)
    else:
        logger.info("Режим LOCAL_ONLY включён — LLM не будет использоваться")

    try:
        # Загрузка дополнительных настроек из переменных окружения
        load_dotenv()
        stt_use_vad = os.getenv("STT_USE_VAD", "0").lower() in ("1", "true", "yes", "on")
        stt_vad_aggressiveness = int(os.getenv("STT_VAD_AGGRESSIVENESS", "2"))
        hotword_adaptive_threshold = os.getenv("HOTWORD_ADAPTIVE_THRESHOLD", "1").lower() in ("1", "true", "yes", "on")
        
        # Логируем используемое устройство ввода
        if config.mic_device_index is not None:
            logger.info(f"Используется микрофон с индексом: {config.mic_device_index}")
        else:
            logger.info("Используется микрофон по умолчанию")
        
        # Создание конфигурации hotword с настройками микрофона из config
        hotword_config = HotwordConfig(
            model_path=model_path,
            sample_rate=config.mic_sample_rate,
            chunk_size=config.mic_chunk_size,
            confidence_threshold=0.7,
            debounce_seconds=1.2,
            adaptive_threshold=hotword_adaptive_threshold,
            device_index=config.mic_device_index,
        )

        # Создание слушателя hotword
        logger.info("Инициализация детектора hotword...")
        listener = KimHotwordListener(hotword_config)

        # Создание конфигурации STT с настройками микрофона из config
        stt_config = STTConfig(
            model_path=model_path,
            sample_rate=config.mic_sample_rate,
            chunk_size=config.mic_chunk_size,
            max_phrase_duration=10.0,
            silence_timeout=1.5,
            use_vad=stt_use_vad,
            vad_aggressiveness=stt_vad_aggressiveness,
            device_index=config.mic_device_index,
        )

        # Создание распознавателя речи
        logger.info("Инициализация распознавателя речи (STT)...")
        stt = KimSTT(stt_config)

        # Создание синтезатора речи
        logger.info("Инициализация синтезатора речи (TTS)...")
        # rate: для COM это -10 до 10, где 0 - нормальная скорость
        # 2-4 делает речь немного быстрее и более живой, но не слишком быстро
        voice = KimVoice(rate=3, volume=100)

        # Создание LLM-клиента и маршрутизатора (только если не local_only)
        llm_client = None
        llm_router = None

        if not config.local_only:
            logger.info("Инициализация LLM-клиента...")
            llm_client = OpenRouterClient(config)
            llm_router = LLMRouter(config, llm_client)
        else:
            logger.info("LLM-клиент пропущен (режим LOCAL_ONLY)")

        logger.info("Все компоненты инициализированы")

        # Вспомогательная функция для синхронного вызова LLM
        def ask_llm_sync(user_text: str) -> str:
            """
            Синхронно отправляет запрос в LLM и возвращает ответ.

            Args:
                user_text: Текст вопроса пользователя

            Returns:
                str: Текст ответа от LLM или сообщение об ошибке
            """
            logger.info(f"Вопрос пользователя: {user_text}")

            # Формируем сообщения
            messages = [
                get_system_prompt(),
                {"role": "user", "content": user_text},
            ]

            # Асинхронный вызов через asyncio.run
            async def _run_llm() -> str:
                try:
                    response = await llm_router.run(messages)
                    return response
                except BudgetExceededError as e:
                    logger.warning(f"Превышен лимит токенов: {e}")
                    return "На сегодня исчерпан лимит запросов, попробуйте завтра."
                except LLMError as e:
                    logger.error(f"Ошибка LLM: {e}")
                    return "Сейчас не могу ответить, попробуйте позже."

            try:
                answer = asyncio.run(_run_llm())
                logger.info(f"Ответ LLM: {answer[:100]}...")
                return answer
            except Exception as e:
                logger.exception(f"Неожиданная ошибка при запросе к LLM: {e}")
                return "Произошла ошибка, попробуйте позже."

        # Функция для получения локального ответа
        def get_local_response(user_text: str) -> str:
            """
            Формирует локальный ответ без обращения к LLM.

            Args:
                user_text: Текст пользователя

            Returns:
                str: Локальный ответ
            """
            text_lower = user_text.lower()

            if any(word in text_lower for word in ["привет", "здравствуй", "добрый"]):
                return "Привет! Сейчас я работаю в локальном режиме и не обращаюсь к интернету."
            elif any(word in text_lower for word in ["время", "который час"]):
                from datetime import datetime
                current_time = datetime.now().strftime("%H:%M")
                return f"Сейчас {current_time}."
            else:
                return "Сейчас включён режим только локально, я не обращаюсь к ИИ-модели."

        # Пороги для мягкого подтверждения
        CONFIRMATION_CONF_THRESHOLD = 0.75  # если уверенность выше - не спрашиваем
        CONFIRMATION_LENGTH_THRESHOLD = 25  # если фраза длиннее - спрашиваем

        # Определение callback при обнаружении hotword
        def on_hotword_triggered() -> None:
            """Обработчик срабатывания hotword."""
            logger.info(">>> Hotword «Ким» активирован!")

            # Озвучиваем ответ
            voice.speak("Да, слушаю.")

            # Получаем фразу с уверенностью для мягкого подтверждения
            result = stt.listen_once_with_confidence()
            
            if result is None:
                # Если не удалось распознать, пробуем с обычным методом
                user_text = stt.listen_with_retries(max_retries=2)
                if not user_text or not user_text.strip():
                    logger.warning("Речь не распознана после нескольких попыток")
                    voice.speak("Не расслышала, повторите позже.")
                    return
                user_text_final = user_text
                avg_conf = 1.0  # По умолчанию полная уверенность
            else:
                user_text_final, avg_conf = result

            logger.info(f"Распознанная фраза: '{user_text_final}', уверенность: {avg_conf:.2f}")
            print(f"\n>>> Распознано: {user_text_final}\n")

            # Определяем, нужно ли подтверждение
            needs_confirmation = (
                avg_conf < CONFIRMATION_CONF_THRESHOLD or
                len(user_text_final) >= CONFIRMATION_LENGTH_THRESHOLD
            )

            if not needs_confirmation:
                logger.info(
                    f"Подтверждение не требуется "
                    f"(уверенность={avg_conf:.2f} >= {CONFIRMATION_CONF_THRESHOLD}, "
                    f"длина={len(user_text_final)} < {CONFIRMATION_LENGTH_THRESHOLD})"
                )
                user_text = user_text_final
            else:
                # Озвучиваем подтверждение распознанной фразы
                logger.info(
                    f"Требуется подтверждение "
                    f"(уверенность={avg_conf:.2f} < {CONFIRMATION_CONF_THRESHOLD} "
                    f"или длина={len(user_text_final)} >= {CONFIRMATION_LENGTH_THRESHOLD})"
                )
                voice.speak(f"Кажется, вы сказали: {user_text_final}. Всё верно?")

                # Слушаем подтверждение пользователя (короткий ответ)
                confirmation_text = stt.listen_once_for_confirmation(min_chars=2)

                # Обрабатываем подтверждение
                if confirmation_text:
                    confirmation_lower = confirmation_text.lower()
                    logger.info(f"Ответ на подтверждение: '{confirmation_text}'")

                    # Если пользователь сказал "нет"
                    if any(word in confirmation_lower for word in ["нет", "неверно", "не так", "неправильно"]):
                        logger.info("Пользователь отклонил распознанную фразу, просим повторить")
                        voice.speak("Хорошо, повторите, пожалуйста.")

                        # Повторная попытка распознавания
                        result_retry = stt.listen_once_with_confidence()
                        if result_retry is None:
                            user_text = stt.listen_with_retries(max_retries=2)
                            if not user_text or not user_text.strip():
                                logger.warning("Речь не распознана после повторной попытки")
                                voice.speak("Не расслышала, повторите позже.")
                                return
                            user_text = user_text
                        else:
                            user_text, _ = result_retry

                        logger.info(f"Повторно распознанная фраза: '{user_text}'")
                        print(f"\n>>> Распознано: {user_text}\n")
                    else:
                        # Если "да" или неясный ответ - используем первоначальную фразу
                        logger.info("Подтверждение получено, используем первоначальную фразу")
                        user_text = user_text_final
                else:
                    # Если подтверждение не распознано - используем первоначальную фразу
                    logger.info("Подтверждение не распознано, используем первоначальную фразу")
                    user_text = user_text_final

            # Ветвление по режиму local_only
            if config.local_only:
                logger.info("Использование локального режима (без LLM)")
                answer = get_local_response(user_text)
                logger.info(f"Локальный ответ: {answer}")
            else:
                # Получаем ответ от LLM
                logger.info("Отправка запроса в LLM...")
                answer = ask_llm_sync(user_text)

            # Озвучиваем ответ
            logger.info("Озвучивание ответа...")
            voice.speak(answer)

        # Запуск прослушивания
        mode_info = " (режим только локально)" if config.local_only else ""
        logger.info("\n" + "=" * 60)
        logger.info(f"Голосовой ассистент готов к работе!{mode_info}")
        logger.info("Произнесите «Ким» для активации")
        logger.info("После активации задайте вопрос голосом")
        logger.info("Для остановки нажмите Ctrl+C")
        logger.info("=" * 60 + "\n")

        listener.listen(on_hotword_triggered)

    except KeyboardInterrupt:
        logger.info("\nОстановка голосового ассистента по запросу пользователя...")
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        print(f"\n❌ ОШИБКА: Файл не найден: {e}\n")
        sys.exit(1)
    except RuntimeError as e:
        error_msg = str(e)
        if "Vosk" in error_msg or "модель" in error_msg.lower():
            logger.exception(f"Voice assistant crashed: {e}")
            print(
                f"\n❌ Голосовой ассистент не смог запуститься.\n"
                f"Проверьте модель Vosk и путь к ней в VOSK_MODEL_PATH.\n"
                f"Детали: {error_msg}\n"
            )
        else:
            logger.exception(f"Voice assistant crashed: {e}")
            print(
                f"\n❌ Голосовой ассистент не смог запуститься.\n"
                f"Проверьте микрофон, модель Vosk и настройки.\n"
                f"Детали: {error_msg}\n"
            )
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Voice assistant crashed: {e}")
        print(
            f"\n❌ Голосовой ассистент не смог запуститься.\n"
            f"Проверьте микрофон, модель Vosk и настройки.\n"
            f"Детали: {str(e)}\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
