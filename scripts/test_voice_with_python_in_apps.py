"""Тест TTS с проверкой появления Python в списке приложений."""

import sys
from pathlib import Path
import time

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger
from kim_voice.tts.voice import KimVoice

print("=" * 60)
print("Тест TTS - проверка появления Python в списке приложений")
print("=" * 60)

config = load_config()
init_logger(config)

print("\nВАЖНО:")
print("1. Откройте настройки звука Windows (как на скриншоте)")
print("2. Оставьте окно открытым на вкладке 'Громкость приложений'")
print("3. Запустите этот скрипт - Python должен появиться в списке")
print("4. Проверьте громкость Python в списке приложений")
print("\n" + "=" * 60)
print("Запуск теста через 5 секунд...")
print("=" * 60)

for i in range(5, 0, -1):
    print(f"{i}...")
    time.sleep(1)

print("\nСоздание KimVoice...")
voice = KimVoice()

print("\nОзвучивание тестового сообщения...")
print("Сообщение: 'Тест один два три четыре пять'")
print("\n⚠  СМОТРИТЕ НА ЭКРАН НАСТРОЕК - Python должен появиться в списке приложений!")
print("   Проверьте громкость Python в списке!")
print("\nЗапуск через 2 секунды...\n")
time.sleep(2)

voice.speak("Тест один два три четыре пять")

print("\n✓ Тест завершён")
print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ:")
print("=" * 60)
print("\n1. Появился ли Python в списке 'Громкость приложений'?")
print("2. Какая громкость у Python в списке?")
print("3. Слышали ли вы звук?")
print("\n" + "=" * 60)

