"""Финальный тест TTS с установленным устройством."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger
from kim_voice.tts.voice import KimVoice

print("=" * 60)
print("ФИНАЛЬНЫЙ ТЕСТ TTS")
print("=" * 60)

config = load_config()
init_logger(config)

print("\nСоздание KimVoice...")
voice = KimVoice()

print("\nОзвучивание тестового сообщения...")
print("Сообщение: 'Привет! Это финальный тест. Если вы меня слышите через Bluetooth колонку, значит всё работает отлично!'")

voice.speak("Привет! Это финальный тест. Если вы меня слышите через Bluetooth колонку, значит всё работает отлично!")

print("\n✓ Тест завершён")
print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ:")
print("=" * 60)

print("\nЕсли вы СЛЫШАЛИ звук:")
print("  ✓ TTS работает!")
print("  ✓ Голосовой ассистент готов к использованию")

print("\nЕсли вы НЕ СЛЫШАЛИ звук:")
print("  → Возможно, pyttsx3 не использует установленное устройство")
print("  → Можем перейти на прямой вызов Windows COM")
print("=" * 60)

