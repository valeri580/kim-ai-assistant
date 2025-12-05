"""Полный тест TTS с четким сообщением."""

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
print("Полный тест TTS - проверка качества звука")
print("=" * 60)

config = load_config()
init_logger(config)

voice = KimVoice()

# Тест 1: Короткое сообщение
print("\nТЕСТ 1: Короткое сообщение")
print("-" * 60)
print("Сообщение: 'Тест один. Тест два. Тест три.'")
voice.speak("Тест один. Тест два. Тест три.")
print("✓ Завершено")

# Небольшая пауза
import time
time.sleep(1)

# Тест 2: Среднее сообщение
print("\nТЕСТ 2: Среднее сообщение")
print("-" * 60)
print("Сообщение: 'Привет! Я голосовой ассистент Ким. Я работаю через Bluetooth колонку. Меня хорошо слышно?'")
voice.speak("Привет! Я голосовой ассистент Ким. Я работаю через Bluetooth колонку. Меня хорошо слышно?")
print("✓ Завершено")

time.sleep(1)

# Тест 3: Проверка качества
print("\nТЕСТ 3: Проверка качества")
print("-" * 60)
print("Сообщение: 'Если вы слышите это сообщение полностью, значит TTS работает правильно и качество звука хорошее.'")
voice.speak("Если вы слышите это сообщение полностью, значит TTS работает правильно и качество звука хорошее.")
print("✓ Завершено")

print("\n" + "=" * 60)
print("✓ Все тесты завершены!")
print("=" * 60)
print("\nЕсли вы слышали все три сообщения полностью и чётко,")
print("значит TTS работает отлично и готов к использованию!")
print("\n")

