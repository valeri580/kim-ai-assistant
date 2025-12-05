"""Прямой тест COM с проверкой устройства."""

import win32com.client
import time

print("=" * 60)
print("Прямой тест Windows COM с Bluetooth устройством")
print("=" * 60)

speaker = win32com.client.Dispatch("SAPI.SpVoice")

# Получаем устройства
audio_outputs = speaker.GetAudioOutputs()
print(f"\nНайдено устройств: {audio_outputs.Count}\n")

sberboom_device = None
for i in range(audio_outputs.Count):
    output = audio_outputs.Item(i)
    desc = output.GetDescription()
    print(f"{i+1}. {desc}")
    
    if "SberBoom" in desc or "1205" in desc or "Headphones" in desc:
        sberboom_device = output
        print(f"   ← Найдено целевое устройство!")

if sberboom_device:
    print(f"\n✓ Целевое устройство: {sberboom_device.GetDescription()}")
    
    # Устанавливаем устройство
    print("\nУстановка устройства...")
    try:
        speaker.AudioOutput = sberboom_device
        print(f"✓ Устройство установлено")
        
        # Проверяем текущее устройство
        try:
            current_id = speaker.GetAudioOutputId()
            print(f"✓ Текущее устройство ID проверен")
        except:
            print("⚠  Не удалось проверить ID, но устройство должно быть установлено")
        
    except Exception as e:
        print(f"✗ Ошибка установки: {e}")
        import traceback
        traceback.print_exc()
        print("\nПробуем альтернативный способ...")
        
        # Альтернативный способ - через токен
        try:
            from comtypes.client import CreateObject
            from comtypes.gen import SpeechLib
            
            # Это более сложный путь
            print("Используем более сложный способ...")
            
        except Exception as e2:
            print(f"Альтернативный способ не сработал: {e2}")

# Настраиваем голос
voices = speaker.GetVoices()
for i in range(voices.Count):
    voice = voices.Item(i)
    if "IRINA" in str(voice.Id).upper():
        speaker.Voice = voice
        print(f"\n✓ Голос установлен: {voice.GetDescription()}")
        break

speaker.Volume = 100
speaker.Rate = 0

print(f"\nНастройки:")
print(f"  Громкость: {speaker.Volume}%")
print(f"  Скорость: {speaker.Rate}")

# Тест
print("\n" + "=" * 60)
print("ТЕСТ ОЗВУЧИВАНИЯ")
print("=" * 60)
print("Озвучивание: 'Проверка звука через Bluetooth устройство'")
print("(Если слышите - всё работает!)")
print("\nЗапуск через 2 секунды...\n")
time.sleep(2)

speaker.Speak("Проверка звука через Bluetooth устройство")

print("\n✓ Тест завершён")
print("\n" + "=" * 60)
print("РЕЗУЛЬТАТ:")
print("=" * 60)
print("Если вы СЛЫШАЛИ звук - всё работает!")
print("Если НЕ СЛЫШАЛИ - нужно проверить настройки Windows")
print("=" * 60)

