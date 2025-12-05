"""Финальный тест TTS через Windows COM."""

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
print("ФИНАЛЬНЫЙ ТЕСТ TTS через Windows COM")
print("=" * 60)

config = load_config()
init_logger(config)

print("\nСоздание KimVoice (должен использовать COM)...")
voice = KimVoice()

# Проверяем, какой метод используется
if hasattr(voice, 'use_com') and voice.use_com:
    print("✓ Используется Windows COM (напрямую)")
else:
    print("⚠  Используется pyttsx3 (резервный вариант)")

print("\n" + "=" * 60)
print("ТЕСТ 1: Короткое сообщение")
print("=" * 60)
print("Сообщение: 'Тест один два три'")
voice.speak("Тест один два три")
print("✓ Завершено")

import time
time.sleep(1)

print("\n" + "=" * 60)
print("ТЕСТ 2: Среднее сообщение")
print("=" * 60)
print("Сообщение: 'Привет! Я голосовой ассистент Ким. Я работаю через Bluetooth колонку.'")
voice.speak("Привет! Я голосовой ассистент Ким. Я работаю через Bluetooth колонку.")
print("✓ Завершено")

time.sleep(1)

print("\n" + "=" * 60)
print("ТЕСТ 3: Полное сообщение")
print("=" * 60)
print("Сообщение: 'Если вы слышите это сообщение полностью, значит синтез речи работает правильно через Bluetooth устройство.'")
voice.speak("Если вы слышите это сообщение полностью, значит синтез речи работает правильно через Bluetooth устройство.")
print("✓ Завершено")

print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ:")
print("=" * 60)
print("\nЕсли вы СЛЫШАЛИ все сообщения:")
print("  ✓ TTS работает отлично!")
print("  ✓ Голосовой ассистент готов к использованию")
print("\nЕсли НЕ СЛЫШАЛИ:")
print("  → Проверьте настройки Windows Speech")
print("  → Убедитесь, что Bluetooth колонка выбрана как устройство по умолчанию")
print("=" * 60)

