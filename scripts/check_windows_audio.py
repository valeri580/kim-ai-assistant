"""Проверка настроек аудио Windows для TTS."""

import subprocess
import sys

print("=" * 60)
print("Проверка настроек аудио Windows")
print("=" * 60)

# Проверка 1: Служба Windows Audio
print("\n1. Проверка службы Windows Audio...")
try:
    result = subprocess.run(
        ['sc', 'query', 'Audiosrv'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if 'RUNNING' in result.stdout:
        print("   ✓ Служба Windows Audio запущена")
    else:
        print("   ⚠  Служба Windows Audio не запущена")
        print("   Запустите службу: net start Audiosrv")
except Exception as e:
    print(f"   ⚠  Не удалось проверить службу: {e}")

# Проверка 2: Настройки Speech в Windows
print("\n2. Рекомендации по настройке Windows Speech:")
print("   - Откройте: Панель управления → Речь")
print("   - Проверьте, что выбран голос (например, Microsoft Irina)")
print("   - Нажмите 'Прослушать' для теста")
print("   - Убедитесь, что громкость не на минимуме")

# Проверка 3: Альтернативный способ через Windows API
print("\n3. Попытка прямого вызова Windows SAPI...")
try:
    import win32com.client
    
    print("   Инициализация SAPI через COM...")
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    
    # Получаем доступные голоса
    voices = speaker.GetVoices()
    print(f"   Найдено голосов: {voices.Count}")
    
    # Ищем русский голос
    for i in range(voices.Count):
        voice = voices.Item(i)
        voice_id = str(voice.Id)
        if "IRINA" in voice_id.upper() or "RU-RU" in voice_id.upper():
            speaker.Voice = voice
            print(f"   Установлен голос: {voice.GetDescription()}")
            break
    
    # Устанавливаем громкость и скорость
    speaker.Volume = 100  # 0-100
    speaker.Rate = 0  # -10 до 10
    
    print("\n   Тест через Windows SAPI COM:")
    print("   Озвучивание: 'Тест через Windows SAPI'")
    speaker.Speak("Тест через Windows SAPI")
    print("   ✓ Завершено")
    
    print("\n   Если вы услышали голос через COM, значит проблема в pyttsx3")
    print("   Если не услышали - проблема в настройках Windows")
    
except ImportError:
    print("   ⚠  pywin32 не установлен, пропускаю тест COM")
    print("   Установите: pip install pywin32")
except Exception as e:
    print(f"   ✗ Ошибка COM: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ:")
print("=" * 60)
print("1. Откройте 'Параметры Windows' → 'Система' → 'Звук'")
print("2. Проверьте 'Громкость приложений' - убедитесь, что Python не на минимуме")
print("3. Попробуйте запустить скрипт от имени администратора")
print("4. Проверьте, не блокирует ли антивирус доступ к SAPI")
print("=" * 60)

