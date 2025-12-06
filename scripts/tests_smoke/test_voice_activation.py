"""Smoke-тест для проверки активации голосового ассистента."""

import sys
import time
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import sounddevice as sd
from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_voice.hotword.kim_hotword import HotwordConfig, KimHotwordListener


def test_voice_activation() -> bool:
    """
    Проверяет, что голосовой ассистент может запустить микрофон.

    Returns:
        bool: True если микрофон запускается успешно
    """
    try:
        # Инициализация логирования
        config = load_config()
        init_logger(config)
        
        logger.info("=" * 60)
        logger.info("Smoke test: Voice Activation")
        logger.info("=" * 60)
        
        # Проверка доступности микрофона
        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            
            if default_input is None:
                logger.error("❌ Микрофон не найден (нет устройства по умолчанию)")
                return False
            
            device_info = sd.query_devices(default_input)
            logger.info(f"✓ Найдено устройство ввода: [{default_input}] {device_info['name']}")
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке микрофона: {e}")
            return False
        
        # Проверка инициализации hotword listener
        try:
            model_path = config.vosk_model_path if hasattr(config, 'vosk_model_path') else "models/vosk-ru"
            
            hotword_config = HotwordConfig(
                model_path=model_path,
                device_index=config.mic_device_index if hasattr(config, 'mic_device_index') else None,
                sample_rate=config.mic_sample_rate if hasattr(config, 'mic_sample_rate') else 16000,
                chunk_size=config.mic_chunk_size if hasattr(config, 'mic_chunk_size') else 4000,
            )
            
            listener = KimHotwordListener(hotword_config)
            logger.info("✓ HotwordListener инициализирован")
            
            # Попытка открыть поток микрофона на 2 секунды
            logger.info("Проверка открытия микрофона...")
            time.sleep(1)
            
            # Проверяем, что можем открыть поток
            input_kwargs = {
                "samplerate": hotword_config.sample_rate,
                "blocksize": hotword_config.chunk_size,
                "dtype": "int16",
                "channels": 1,
                "latency": "low",
            }
            if hotword_config.device_index is not None:
                input_kwargs["device"] = hotword_config.device_index
            
            with sd.InputStream(**input_kwargs) as stream:
                logger.info("✓ Микрофон успешно открыт")
                time.sleep(2)  # Держим поток открытым 2 секунды
                logger.info("✓ Микрофон работает корректно")
            
            logger.info("✅ Voice activation test: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации hotword: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_voice_activation()
    sys.exit(0 if success else 1)
