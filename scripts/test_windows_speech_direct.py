"""Прямой тест Windows Speech API без pyttsx3."""

import sys

print("=" * 60)
print("Прямой тест Windows Speech API")
print("=" * 60)

try:
    import win32com.client
    print("✓ pywin32 установлен\n")
except ImportError:
    print("✗ pywin32 не установлен")
    print("Установите: pip install pywin32")
    sys.exit(1)

# Создаём объект Speech
print("Инициализация Windows Speech API...")
speaker = win32com.client.Dispatch("SAPI.SpVoice")

# Получаем все голоса
voices = speaker.GetVoices()
print(f"Найдено голосов: {voices.Count}\n")

# Показываем все доступные голоса
print("Доступные голоса:")
for i in range(voices.Count):
    voice = voices.Item(i)
    print(f"  {i+1}. {voice.GetDescription()}")
    print(f"     ID: {voice.Id}")

# Ищем русский голос
print("\n" + "=" * 60)
print("Поиск русского голоса...")
russian_voice = None
for i in range(voices.Count):
    voice = voices.Item(i)
    voice_id = str(voice.Id).upper()
    if "IRINA" in voice_id or "RU-RU" in voice_id or "RUSSIAN" in voice_id:
        russian_voice = voice
        print(f"✓ Найден русский голос: {voice.GetDescription()}")
        break

if not russian_voice:
    print("⚠  Русский голос не найден, используем первый доступный")
    russian_voice = voices.Item(0)
    print(f"Используем: {russian_voice.GetDescription()}")

# Устанавливаем голос
speaker.Voice = russian_voice

# Настройки
speaker.Volume = 100  # 0-100
speaker.Rate = 0  # -10 до 10

print(f"\nНастройки:")
print(f"  Громкость: {speaker.Volume}%")
print(f"  Скорость: {speaker.Rate}")

# Тест 1
print("\n" + "=" * 60)
print("ТЕСТ 1: Короткое сообщение")
print("=" * 60)
print("Озвучивание: 'Тест один два три'")
print("\n⚠  ВНИМАНИЕ: Если звука нет, проблема в настройках Windows Speech!")
print("Запуск через 2 секунды...\n")

import time
time.sleep(2)

speaker.Speak("Тест один два три")
print("✓ Тест 1 завершён")

# Тест 2
print("\n" + "=" * 60)
print("ТЕСТ 2: Длинное сообщение")
print("=" * 60)
print("Озвучивание: 'Привет! Это прямой тест Windows Speech API. Если вы меня слышите, значит Windows Speech работает правильно.'")

speaker.Speak("Привет! Это прямой тест Windows Speech API. Если вы меня слышите, значит Windows Speech работает правильно.")
print("✓ Тест 2 завершён")

# Тест 3: С максимальной громкостью
print("\n" + "=" * 60)
print("ТЕСТ 3: Максимальная громкость")
print("=" * 60)
speaker.Volume = 100
speaker.Rate = 0
print(f"Громкость: {speaker.Volume}%")
print("Озвучивание: 'МАКСИМАЛЬНАЯ ГРОМКОСТЬ'")

speaker.Speak("МАКСИМАЛЬНАЯ ГРОМКОСТЬ")
print("✓ Тест 3 завершён")

print("\n" + "=" * 60)
print("РЕЗУЛЬТАТЫ:")
print("=" * 60)

print("\nЕсли вы СЛЫШАЛИ звук:")
print("  ✓ Windows Speech API работает")
print("  ✗ Проблема в библиотеке pyttsx3")
print("  → Нужно использовать альтернативный метод или исправить pyttsx3")

print("\nЕсли вы НЕ СЛЫШАЛИ звук:")
print("  ✗ Проблема в настройках Windows Speech")
print("  → Проверьте: Панель управления → Речь")
print("  → Нажмите 'Прослушать' для теста голоса")
print("  → Убедитесь, что голос работает")

print("\n" + "=" * 60)

