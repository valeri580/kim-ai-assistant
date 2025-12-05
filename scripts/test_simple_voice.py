"""Простой тест TTS - одно короткое сообщение."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger
from kim_voice.tts.voice import KimVoice

config = load_config()
init_logger(config)

print("Создание KimVoice...")
voice = KimVoice()

print("\nТестовое сообщение (короткое): 'Тест'")
voice.speak("Тест")

print("\nГотово! Слышали ли вы слово 'Тест'?")

