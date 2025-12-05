"""Быстрый тест качества голоса TTS с разными параметрами скорости."""

import sys
import time
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger
from kim_voice.tts.voice import KimVoice

print("=" * 60)
print("ТЕСТ КАЧЕСТВА ГОЛОСА TTS")
print("=" * 60)

# Загружаем конфигурацию и инициализируем логгер
config = load_config()
init_logger(config)

print("\nСоздание TTS с текущими настройками (скорость=3)...")
voice = KimVoice(rate=3, volume=100)

test_phrases = [
    "Да, слушаю.",
    "Привет! Я голосовой ассистент Ким.",
    "Как дела? Чем могу помочь?",
]

print("\n" + "=" * 60)
print("ТЕСТ 1: Текущие настройки (скорость=3)")
print("=" * 60)
print("Сейчас прозвучат тестовые фразы с текущими настройками...\n")

for i, phrase in enumerate(test_phrases, 1):
    print(f"{i}. {phrase}")
    voice.speak(phrase)
    time.sleep(1)

print("\n" + "=" * 60)
print("Если звук всё ещё механический или затянутый,")
print("можно попробовать изменить скорость в src/kim_voice/main.py:")
print("  - rate=4-5 для более быстрой и живой речи")
print("  - rate=1-2 для более медленной речи")
print("=" * 60)

