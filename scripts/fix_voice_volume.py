"""Попытка исправить проблему с громкостью TTS."""

import pyttsx3
import time

print("=" * 60)
print("Исправление проблемы с громкостью TTS")
print("=" * 60)

# Создаём движок с явным указанием драйвера
print("\nИнициализация TTS с максимальными настройками...")
engine = pyttsx3.init(driverName='sapi5')

# Устанавливаем русский голос
voices = engine.getProperty("voices")
if voices:
    for voice in voices:
        if "IRINA" in str(voice.id).upper():
            engine.setProperty("voice", voice.id)
            print(f"Голос: {voice.name}")
            break

# МАКСИМАЛЬНЫЕ настройки
engine.setProperty("rate", 150)  # Нормальная скорость
engine.setProperty("volume", 1.0)  # МАКСИМАЛЬНАЯ громкость

# Проверяем фактические значения
actual_rate = engine.getProperty("rate")
actual_volume = engine.getProperty("volume")
print(f"Скорость: {actual_rate} слов/минуту")
print(f"Громкость: {actual_volume} (должна быть 1.0)")

if actual_volume < 0.9:
    print(f"⚠  ВНИМАНИЕ: Громкость низкая ({actual_volume})!")
    print("Пробую установить максимальную громкость...")
    engine.setProperty("volume", 1.0)
    actual_volume = engine.getProperty("volume")
    print(f"Громкость после исправления: {actual_volume}")

print("\n" + "=" * 60)
print("ТЕСТ 1: Короткое громкое сообщение")
print("=" * 60)
print("Сейчас прозвучит: 'ВНИМАНИЕ! ТЕСТ ГРОМКОСТИ!'")
print("Увеличьте громкость системы до максимума!")
print("\nОзвучивание через 3 секунды...")
time.sleep(3)

engine.say("ВНИМАНИЕ! ТЕСТ ГРОМКОСТИ!")
engine.runAndWait()

print("\n✓ Тест 1 завершён")
print("\nСлышали ли вы звук? (y/n)")

# Тест 2: Длинное сообщение
print("\n" + "=" * 60)
print("ТЕСТ 2: Длинное сообщение")
print("=" * 60)
print("Озвучивание: 'Привет! Это тест синтеза речи. Если вы меня слышите, значит всё работает правильно.'")

engine.say("Привет! Это тест синтеза речи. Если вы меня слышите, значит всё работает правильно.")
engine.runAndWait()

print("\n✓ Тест 2 завершён")

# Важная информация
print("\n" + "=" * 60)
print("ВАЖНО: Проверьте настройки Windows")
print("=" * 60)
print("1. Откройте 'Параметры' → 'Система' → 'Звук'")
print("2. Прокрутите вниз до 'Громкость приложений'")
print("3. Найдите 'Python' или 'python.exe' в списке")
print("4. Убедитесь, что громкость Python не на минимуме")
print("5. Если Python нет в списке, запустите скрипт ещё раз")
print("=" * 60)

print("\nЕсли звука всё ещё нет:")
print("- Попробуйте запустить PowerShell от имени администратора")
print("- Проверьте настройки Windows Speech (Панель управления → Речь)")
print("- Убедитесь, что выбран правильный голос и он работает")

