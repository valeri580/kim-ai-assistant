"""Проверка и настройка аудиоустройства для SAPI."""

import win32com.client

print("=" * 60)
print("Проверка аудиоустройства SAPI")
print("=" * 60)

# Создаём объект Speech
speaker = win32com.client.Dispatch("SAPI.SpVoice")

# Получаем доступные аудиоустройства
audio_outputs = speaker.GetAudioOutputs()
print(f"\nДоступных аудиоустройств для SAPI: {audio_outputs.Count}\n")

print("Доступные аудиоустройства:")
for i in range(audio_outputs.Count):
    output = audio_outputs.Item(i)
    output_id = str(output.Id)
    output_desc = output.GetDescription()
    
    # Проверяем, используется ли это устройство сейчас
    is_current = False
    try:
        current_output_id = str(speaker.GetAudioOutputId())
        is_current = (output_id == current_output_id)
    except:
        pass
    
    marker = " ← ТЕКУЩЕЕ" if is_current else ""
    print(f"  {i+1}. {output_desc}{marker}")
    print(f"     ID: {output_id[:80]}...")

# Показываем текущее устройство
try:
    current_id = speaker.GetAudioOutputId()
    current_output = None
    for i in range(audio_outputs.Count):
        output = audio_outputs.Item(i)
        if str(output.Id) == str(current_id):
            current_output = output
            break
    
    if current_output:
        print(f"\n✓ Текущее устройство SAPI: {current_output.GetDescription()}")
    else:
        print(f"\n⚠  Текущее устройство не определено")
except Exception as e:
    print(f"\n⚠  Не удалось определить текущее устройство: {e}")

# Пробуем найти Bluetooth устройство
print("\n" + "=" * 60)
print("Поиск Bluetooth устройства...")
print("=" * 60)

bluetooth_device = None
for i in range(audio_outputs.Count):
    output = audio_outputs.Item(i)
    output_desc = output.GetDescription().upper()
    
    if "BLUETOOTH" in output_desc or "BT" in output_desc:
        bluetooth_device = output
        print(f"✓ Найдено Bluetooth устройство: {output.GetDescription()}")
        break

if bluetooth_device:
    print("\nПопытка установить Bluetooth устройство для SAPI...")
    try:
        speaker.SetAudioOutput(bluetooth_device)
        print(f"✓ Установлено устройство: {bluetooth_device.GetDescription()}")
        
        # Тест
        print("\nТест озвучивания через Bluetooth устройство...")
        print("Озвучивание: 'Тест через Bluetooth устройство'")
        
        voices = speaker.GetVoices()
        for i in range(voices.Count):
            voice = voices.Item(i)
            voice_id = str(voice.Id).upper()
            if "IRINA" in voice_id:
                speaker.Voice = voice
                break
        
        speaker.Volume = 100
        speaker.Rate = 0
        speaker.Speak("Тест через Bluetooth устройство")
        print("✓ Тест завершён")
        
    except Exception as e:
        print(f"✗ Ошибка установки устройства: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠  Bluetooth устройство не найдено в списке SAPI")
    print("\nЭто может означать, что:")
    print("1. Устройство не распознано SAPI")
    print("2. Нужно перезапустить Windows Audio службу")
    print("3. SAPI использует устройство по умолчанию")

# Альтернативный способ: установить устройство по умолчанию
print("\n" + "=" * 60)
print("Альтернативный способ: использование устройства по умолчанию")
print("=" * 60)

try:
    # Пробуем установить устройство по умолчанию Windows
    # SAPI должен использовать устройство по умолчанию, если явно не указано другое
    
    # Получаем устройство по умолчанию
    import comtypes.client
    from comtypes.gen import SpeechLib
    
    # Это более сложный путь, но попробуем проще
    print("SAPI должен использовать устройство по умолчанию Windows")
    print("Проверьте настройки Windows:")
    print("  Параметры → Система → Звук → Выбор устройства вывода")
    print("  Убедитесь, что Bluetooth колонка выбрана как устройство по умолчанию")
    
except Exception as e:
    print(f"Информация: {e}")

print("\n" + "=" * 60)
print("РЕКОМЕНДАЦИИ:")
print("=" * 60)
print("1. Убедитесь, что Bluetooth колонка выбрана как устройство по умолчанию")
print("   Параметры → Система → Звук → Выбор устройства вывода")
print("2. Если звука всё ещё нет, попробуйте:")
print("   - Переподключить Bluetooth устройство")
print("   - Перезапустить службу Windows Audio")
print("   - Использовать другое устройство вывода для теста")
print("=" * 60)

