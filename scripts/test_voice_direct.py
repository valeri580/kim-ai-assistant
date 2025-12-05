"""Прямой тест TTS с проверкой звука."""

import pyttsx3
import time

print("=" * 60)
print("Прямой тест TTS")
print("=" * 60)

# Инициализация
print("\nИнициализация движка...")
engine = pyttsx3.init()

# Получаем все голоса
voices = engine.getProperty("voices")
print(f"\nДоступно голосов: {len(voices)}")

# Пробуем русский голос (Irina)
print("\n" + "-" * 60)
print("ТЕСТ 1: Русский голос (Irina)")
print("-" * 60)

for voice in voices:
    if "IRINA" in str(voice.id).upper() or "RU-RU" in str(voice.id).upper():
        engine.setProperty("voice", voice.id)
        print(f"Установлен голос: {voice.name}")
        break

engine.setProperty("rate", 150)
engine.setProperty("volume", 1.0)

print("Громкость: 100%")
print("Скорость: 150 слов/минуту")
print("\nОзвучивание: 'Привет! Это тест русского голоса.'")
print("(Проверьте громкость системы!)")

engine.say("Привет! Это тест русского голоса.")
engine.runAndWait()

print("\n✓ Тест 1 завершён")

# Пробуем английский голос (Zira - женский)
print("\n" + "-" * 60)
print("ТЕСТ 2: Английский женский голос (Zira)")
print("-" * 60)

for voice in voices:
    if "ZIRA" in str(voice.id).upper():
        engine.setProperty("voice", voice.id)
        print(f"Установлен голос: {voice.name}")
        break

engine.setProperty("rate", 150)
engine.setProperty("volume", 1.0)

print("Озвучивание: 'Hello! This is a test of English voice.'")
print("(Проверьте громкость системы!)")

engine.say("Hello! This is a test of English voice.")
engine.runAndWait()

print("\n✓ Тест 2 завершён")

# Проверка громкости системы
print("\n" + "-" * 60)
print("ПРОВЕРКА ГРОМКОСТИ")
print("-" * 60)

try:
    import ctypes
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    current_volume = volume.GetMasterVolumeLevelScalar()
    print(f"Текущая громкость системы: {int(current_volume * 100)}%")
    
    if current_volume < 0.1:
        print("⚠  ВНИМАНИЕ: Громкость очень низкая!")
        print("   Увеличьте громкость в Windows")
except Exception as e:
    print(f"Не удалось проверить громкость: {e}")
    print("(Это нормально, если pycaw не установлен)")

print("\n" + "=" * 60)
print("РЕКОМЕНДАЦИИ:")
print("=" * 60)
print("1. Проверьте громкость в Windows (правый нижний угол)")
print("2. Проверьте, что звук не отключён (иконка динамика)")
print("3. Проверьте настройки звука: Параметры → Система → Звук")
print("4. Попробуйте воспроизвести музыку или видео для проверки звука")
print("5. Убедитесь, что выбрано правильное аудиоустройство")
print("=" * 60)

