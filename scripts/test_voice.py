"""Тест голосового модуля TTS."""

import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger
from kim_voice.tts.voice import KimVoice


def main() -> None:
    """Основная функция тестирования TTS."""
    print("\n" + "=" * 60)
    print("Тест голосового модуля TTS")
    print("=" * 60 + "\n")
    
    try:
        config = load_config()
        init_logger(config)
        
        print("Инициализация TTS движка...")
        voice = KimVoice()
        
        print("Озвучивание тестового сообщения...")
        voice.speak("Привет! Я голос Ким. Если ты меня слышишь, значит T T S работает.")
        
        print("\n" + "=" * 60)
        print("✓ Тест завершён! Проверьте, что вы слышали голосовое сообщение.")
        print("=" * 60 + "\n")
        
    except ImportError as e:
        print(f"\n❌ Ошибка импорта: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

