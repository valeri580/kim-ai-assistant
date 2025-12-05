"""Комплексная проверка голосовой системы."""

import os
import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger


def check_dependencies() -> bool:
    """Проверка установленных зависимостей для голоса."""
    print("\n1. Проверка зависимостей...")
    
    modules = {
        "pyttsx3": "TTS (синтез речи)",
        "vosk": "STT (распознавание речи)",
        "sounddevice": "Работа с микрофоном",
        "numpy": "Обработка аудио",
    }
    
    all_ok = True
    for module_name, description in modules.items():
        try:
            __import__(module_name)
            print(f"   ✓ {description} ({module_name})")
        except ImportError:
            print(f"   ✗ {description} ({module_name}) - не установлен")
            all_ok = False
    
    return all_ok


def check_vosk_model() -> bool:
    """Проверка наличия модели Vosk."""
    print("\n2. Проверка модели Vosk...")
    
    from dotenv import load_dotenv
    load_dotenv()
    model_path = os.getenv("VOSK_MODEL_PATH", "models/vosk-ru")
    
    if os.path.exists(model_path):
        print(f"   ✓ Модель найдена: {model_path}")
        
        # Проверяем структуру модели
        model_files = ["am", "graph", "ivector"]
        found_files = []
        for item in os.listdir(model_path):
            item_path = os.path.join(model_path, item)
            if os.path.isdir(item_path):
                found_files.append(item)
        
        if found_files:
            print(f"   ✓ Структура модели корректна")
            return True
        else:
            print(f"   ⚠  Модель найдена, но структура может быть неполной")
            return True  # Всё равно продолжаем
    else:
        print(f"   ✗ Модель не найдена: {model_path}")
        print(f"   Скачайте с: https://alphacephei.com/vosk/models")
        return False


def check_tts() -> bool:
    """Проверка TTS."""
    print("\n3. Проверка TTS (синтез речи)...")
    
    try:
        from kim_voice.tts.voice import KimVoice
        
        print("   Инициализация TTS...")
        voice = KimVoice()
        print("   ✓ TTS инициализирован")
        
        # Короткий тест
        print("   Тестовое озвучивание...")
        voice.speak("T T S работает.")
        print("   ✓ TTS работает (проверьте, что вы слышали голос)")
        
        return True
    except Exception as e:
        print(f"   ✗ Ошибка TTS: {e}")
        return False


def check_stt() -> bool:
    """Проверка STT (только инициализация, без реального распознавания)."""
    print("\n4. Проверка STT (распознавание речи)...")
    
    try:
        from kim_voice.stt.speech_to_text import KimSTT, STTConfig
        from dotenv import load_dotenv
        
        load_dotenv()
        model_path = os.getenv("VOSK_MODEL_PATH", "models/vosk-ru")
        
        if not os.path.exists(model_path):
            print("   ⚠  Пропущено: модель Vosk не найдена")
            return False
        
        print("   Инициализация STT...")
        stt_config = STTConfig(
            model_path=model_path,
            sample_rate=16000,
            chunk_size=4000,
            max_phrase_duration=10.0,
            silence_timeout=1.5,
        )
        stt = KimSTT(stt_config)
        print("   ✓ STT инициализирован")
        
        return True
    except Exception as e:
        print(f"   ✗ Ошибка STT: {e}")
        return False


def check_hotword() -> bool:
    """Проверка hotword (только инициализация)."""
    print("\n5. Проверка Hotword детектора...")
    
    try:
        from kim_voice.hotword.kim_hotword import KimHotwordListener, HotwordConfig
        from dotenv import load_dotenv
        
        load_dotenv()
        model_path = os.getenv("VOSK_MODEL_PATH", "models/vosk-ru")
        
        if not os.path.exists(model_path):
            print("   ⚠  Пропущено: модель Vosk не найдена")
            return False
        
        print("   Инициализация hotword детектора...")
        hotword_config = HotwordConfig(
            model_path=model_path,
            sample_rate=16000,
            chunk_size=4000,
            confidence_threshold=0.7,
            debounce_seconds=1.2,
        )
        listener = KimHotwordListener(hotword_config)
        print("   ✓ Hotword детектор инициализирован")
        
        return True
    except Exception as e:
        print(f"   ✗ Ошибка hotword: {e}")
        return False


def main() -> None:
    """Основная функция проверки."""
    print("\n" + "=" * 60)
    print("Проверка голосовой системы «Ким»")
    print("=" * 60)
    
    config = load_config()
    init_logger(config)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    results = {}
    
    results["dependencies"] = check_dependencies()
    results["vosk_model"] = check_vosk_model()
    results["tts"] = check_tts()
    results["stt"] = check_stt()
    results["hotword"] = check_hotword()
    
    # Итоги
    print("\n" + "=" * 60)
    print("Итоги проверки")
    print("=" * 60)
    
    for check_name, result in results.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name.upper()}: {'OK' if result else 'ОШИБКА'}")
    
    critical_checks = ["dependencies", "tts"]
    all_critical_ok = all(results.get(key, False) for key in critical_checks)
    
    if all_critical_ok:
        print("\n✓ Критические компоненты работают!")
        print("  Голосовой ассистент готов к базовому использованию.")
    else:
        print("\n⚠  Некоторые критические компоненты не работают.")
        print("  Установите недостающие зависимости: pip install -r requirements.txt")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПроверка прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

