"""Тест с явной установкой устройства SberBoom."""

import win32com.client
import time

print("=" * 60)
print("Тест с устройством SberBoom Home 1205")
print("=" * 60)

speaker = win32com.client.Dispatch("SAPI.SpVoice")

# Получаем устройства
audio_outputs = speaker.GetAudioOutputs()
sberboom_device = None

print("\nПоиск устройства SberBoom...")
for i in range(audio_outputs.Count):
    output = audio_outputs.Item(i)
    desc = output.GetDescription()
    print(f"  {i+1}. {desc}")
    
    if "SberBoom" in desc or "1205" in desc:
        sberboom_device = output
        print(f"     ← Найдено!")

if sberboom_device:
    print(f"\n✓ Устройство найдено: {sberboom_device.GetDescription()}")
    
    # Устанавливаем устройство через свойство AudioOutput
    try:
        speaker.AudioOutput = sberboom_device
        print(f"✓ Устройство установлено через свойство AudioOutput")
    except Exception as e:
        print(f"⚠  Способ 1 не сработал: {e}")
        print("Пробуем альтернативный способ...")
        
        # Альтернативный способ - через ID
        try:
            device_id = sberboom_device.Id
            # Пробуем установить через создание нового объекта
            from comtypes.client import CreateObject
            from comtypes.gen import SpeechLib
            
            # Создаём новый SpVoice с указанием устройства
            token = CreateObject(SpeechLib.SpObjectTokenCategory)
            token.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\AudioOutput", False)
            tokens = token.EnumerateTokens(None, None)
            
            for token_item in tokens:
                token_name = token_item.GetDescription()
                if "SberBoom" in token_name or "1205" in token_name:
                    # Создаём новый SpVoice с этим токеном
                    speaker_new = CreateObject(SpeechLib.SpVoice)
                    speaker_new.AudioOutput = token_item
                    
                    voices = speaker_new.GetVoices()
                    for j in range(voices.Count):
                        voice = voices.Item(j)
                        if "IRINA" in str(voice.Id).upper():
                            speaker_new.Voice = voice
                            break
                    
                    speaker_new.Volume = 100
                    speaker_new.Rate = 0
                    
                    print(f"✓ Создан новый SpVoice с устройством: {token_name}")
                    
                    # Тест
                    print("\nТЕСТ ОЗВУЧИВАНИЯ через новое устройство...")
                    time.sleep(1)
                    speaker_new.Speak("Тест через устройство SberBoom. Если вы меня слышите, всё работает!")
                    print("✓ Тест завершён")
                    break
            
        except Exception as e2:
            print(f"⚠  Альтернативный способ не сработал: {e2}")
            print("\nПробуем самый простой способ - через свойство напрямую...")
            
            # Самый простой способ
            try:
                # Устанавливаем свойство AudioOutput напрямую
                speaker.AudioOutput = sberboom_device
                
                voices = speaker.GetVoices()
                for j in range(voices.Count):
                    voice = voices.Item(j)
                    if "IRINA" in str(voice.Id).upper():
                        speaker.Voice = voice
                        break
                
                speaker.Volume = 100
                speaker.Rate = 0
                
                print("✓ Настройки применены")
                print("\nТЕСТ...")
                time.sleep(1)
                speaker.Speak("Тест через SberBoom устройство")
                print("✓ Тест завершён")
                
            except Exception as e3:
                print(f"✗ Не удалось установить устройство: {e3}")
                import traceback
                traceback.print_exc()

else:
    print("\n✗ Устройство SberBoom не найдено")

print("\n" + "=" * 60)
print("РЕКОМЕНДАЦИЯ:")
print("=" * 60)
print("Если звука всё ещё нет, попробуйте:")
print("1. Убедитесь, что 'Headphones (SberBoom Home 1205)' выбраны")
print("   как устройство по умолчанию в Windows:")
print("   Параметры → Система → Звук → Выбор устройства вывода")
print("2. SAPI должен использовать устройство по умолчанию Windows")
print("=" * 60)

