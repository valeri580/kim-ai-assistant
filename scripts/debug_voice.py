"""Диагностика проблем с TTS."""

import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("=" * 60)
print("Диагностика TTS")
print("=" * 60)

# Проверка 1: Импорт pyttsx3
print("\n1. Проверка импорта pyttsx3...")
try:
    import pyttsx3
    print("   ✓ pyttsx3 импортирован")
except ImportError as e:
    print(f"   ✗ Ошибка импорта: {e}")
    sys.exit(1)

# Проверка 2: Инициализация движка
print("\n2. Инициализация движка...")
try:
    engine = pyttsx3.init()
    print("   ✓ Движок инициализирован")
except Exception as e:
    print(f"   ✗ Ошибка инициализации: {e}")
    sys.exit(1)

# Проверка 3: Доступные голоса
print("\n3. Проверка доступных голосов...")
try:
    voices = engine.getProperty("voices")
    print(f"   Найдено голосов: {len(voices) if voices else 0}")
    
    if voices:
        print("\n   Доступные голоса:")
        for i, voice in enumerate(voices):
            print(f"   {i+1}. ID: {voice.id}")
            print(f"      Имя: {voice.name}")
            print(f"      Язык: {getattr(voice, 'languages', ['неизвестно'])}")
    else:
        print("   ⚠  Голоса не найдены!")
        
except Exception as e:
    print(f"   ✗ Ошибка получения голосов: {e}")

# Проверка 4: Текущие настройки
print("\n4. Текущие настройки TTS...")
try:
    rate = engine.getProperty("rate")
    volume = engine.getProperty("volume")
    voice_id = engine.getProperty("voice")
    
    print(f"   Скорость: {rate} слов/минуту")
    print(f"   Громкость: {volume}")
    print(f"   Текущий голос ID: {voice_id}")
except Exception as e:
    print(f"   ✗ Ошибка получения настроек: {e}")

# Проверка 5: Тест озвучивания
print("\n5. Тест озвучивания...")
try:
    print("   Пробую озвучить короткое сообщение...")
    engine.say("Тест. Один. Два. Три.")
    print("   Запуск синтеза...")
    engine.runAndWait()
    print("   ✓ Озвучивание завершено")
    print("\n   ⚠  Если вы не слышали голос:")
    print("      - Проверьте громкость системы")
    print("      - Проверьте, что звук не отключён")
    print("      - Попробуйте другой голос")
except Exception as e:
    print(f"   ✗ Ошибка озвучивания: {e}")
    import traceback
    traceback.print_exc()

# Проверка 6: Попытка с другим голосом
print("\n6. Попытка с другим голосом...")
try:
    voices = engine.getProperty("voices")
    if voices and len(voices) > 0:
        # Пробуем первый доступный голос
        test_voice = voices[0]
        engine.setProperty("voice", test_voice.id)
        print(f"   Установлен голос: {test_voice.name}")
        print("   Тестовое озвучивание...")
        engine.say("Второй тест. Если слышите, голос работает.")
        engine.runAndWait()
        print("   ✓ Тест завершён")
except Exception as e:
    print(f"   ✗ Ошибка: {e}")

print("\n" + "=" * 60)
print("Диагностика завершена")
print("=" * 60)

