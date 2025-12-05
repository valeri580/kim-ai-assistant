"""Установка правильного аудиоустройства для SAPI."""

import win32com.client
import time

print("=" * 60)
print("Установка аудиоустройства для SAPI")
print("=" * 60)

speaker = win32com.client.Dispatch("SAPI.SpVoice")

# Получаем доступные устройства
audio_outputs = speaker.GetAudioOutputs()
print(f"\nНайдено устройств: {audio_outputs.Count}\n")

# Ищем Bluetooth устройство (SberBoom)
target_device = None
for i in range(audio_outputs.Count):
    output = audio_outputs.Item(i)
    desc = output.GetDescription()
    print(f"{i+1}. {desc}")
    
    # Ищем Bluetooth устройство
    if "SberBoom" in desc or "Headphones" in desc or "Bluetooth" in desc.upper():
        target_device = output
        print(f"   ← Это похоже на ваше Bluetooth устройство!")

if target_device:
    print(f"\n✓ Найдено целевое устройство: {target_device.GetDescription()}")
    
    # Устанавливаем устройство
    try:
        speaker.SetAudioOutput(target_device)
        print(f"✓ Установлено устройство: {target_device.GetDescription()}")
        
        # Проверяем
        try:
            current_id = speaker.GetAudioOutputId()
            print(f"✓ Текущее устройство SAPI установлено")
        except:
            print("⚠  Не удалось проверить текущее устройство, но установка выполнена")
        
        # Настраиваем голос
        voices = speaker.GetVoices()
        for i in range(voices.Count):
            voice = voices.Item(i)
            if "IRINA" in str(voice.Id).upper():
                speaker.Voice = voice
                print(f"✓ Установлен голос: {voice.GetDescription()}")
                break
        
        speaker.Volume = 100
        speaker.Rate = 0
        
        # Тест
        print("\n" + "=" * 60)
        print("ТЕСТ ОЗВУЧИВАНИЯ")
        print("=" * 60)
        print("Сейчас прозвучит тестовое сообщение через ваше Bluetooth устройство")
        print("Ожидание 2 секунды...\n")
        time.sleep(2)
        
        print("Озвучивание: 'Тест через Bluetooth устройство. Если вы меня слышите, значит всё работает!'")
        speaker.Speak("Тест через Bluetooth устройство. Если вы меня слышите, значит всё работает!")
        
        print("\n✓ Тест завершён")
        
        if not target_device:
            print("\n⚠  Если звука не было, попробуйте:")
            print("   1. Убедитесь, что Bluetooth колонка выбрана как устройство по умолчанию в Windows")
            print("   2. Перезапустите скрипт")
            print("   3. Проверьте настройки звука в Windows")
        
    except Exception as e:
        print(f"✗ Ошибка установки устройства: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n⚠  Не удалось найти Bluetooth устройство")
    print("Попробуем использовать устройство по умолчанию Windows...")
    
    # Пробуем установить первое устройство
    if audio_outputs.Count > 0:
        default_device = audio_outputs.Item(0)
        try:
            speaker.SetAudioOutput(default_device)
            print(f"Установлено устройство: {default_device.GetDescription()}")
            
            # Тест
            voices = speaker.GetVoices()
            for i in range(voices.Count):
                voice = voices.Item(i)
                if "IRINA" in str(voice.Id).upper():
                    speaker.Voice = voice
                    break
            
            speaker.Volume = 100
            print("\nТест через устройство по умолчанию...")
            speaker.Speak("Тест")
            
        except Exception as e:
            print(f"Ошибка: {e}")

print("\n" + "=" * 60)

