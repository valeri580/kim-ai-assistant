"""Диагностика драйвера TTS и проблем со звуком."""

import pyttsx3
import sys

print("=" * 60)
print("Диагностика драйвера TTS")
print("=" * 60)

# Проверка доступных драйверов
print("\n1. Проверка доступных драйверов pyttsx3...")
try:
    # Пробуем разные драйверы
    drivers_to_try = [
        ('sapi5', 'SAPI5 (Windows Speech API)'),
        ('nsss', 'NSSS (Mac)'),
        ('espeak', 'eSpeak (Linux)'),
    ]
    
    available_drivers = []
    for driver_name, description in drivers_to_try:
        try:
            engine = pyttsx3.init(driverName=driver_name)
            available_drivers.append((driver_name, description, engine))
            print(f"   ✓ {description} ({driver_name}) - доступен")
            engine.stop()
        except Exception as e:
            print(f"   ✗ {description} ({driver_name}) - недоступен: {e}")
    
    if not available_drivers:
        print("   ⚠  Ни один драйвер не доступен!")
        sys.exit(1)
    
except Exception as e:
    print(f"   ✗ Ошибка проверки драйверов: {e}")
    sys.exit(1)

# Тест с явным указанием драйвера
print("\n2. Тест с явным указанием драйвера SAPI5...")
try:
    print("   Инициализация с драйвером sapi5...")
    engine = pyttsx3.init(driverName='sapi5')
    print("   ✓ Движок инициализирован")
    
    # Получаем информацию о движке
    print("\n   Информация о движке:")
    print(f"   Тип: {type(engine)}")
    
    # Проверяем голоса
    voices = engine.getProperty("voices")
    print(f"   Доступно голосов: {len(voices) if voices else 0}")
    
    # Устанавливаем русский голос
    if voices:
        for voice in voices:
            if "IRINA" in str(voice.id).upper() or "RU-RU" in str(voice.id).upper():
                engine.setProperty("voice", voice.id)
                print(f"   Установлен голос: {voice.name}")
                break
    
    # Настройки
    engine.setProperty("rate", 150)
    engine.setProperty("volume", 1.0)
    
    print("\n   Настройки:")
    print(f"   Скорость: {engine.getProperty('rate')} слов/минуту")
    print(f"   Громкость: {engine.getProperty('volume')}")
    print(f"   Голос: {engine.getProperty('voice')}")
    
    # Тест 1: Короткое сообщение
    print("\n   ТЕСТ 1: Короткое сообщение")
    print("   Озвучивание: 'Тест один'")
    engine.say("Тест один")
    print("   Запуск синтеза...")
    engine.runAndWait()
    print("   ✓ Завершено")
    
    # Небольшая пауза
    import time
    time.sleep(1)
    
    # Тест 2: Длинное сообщение
    print("\n   ТЕСТ 2: Длинное сообщение")
    print("   Озвучивание: 'Привет! Это тест синтеза речи. Если вы меня слышите, значит всё работает правильно.'")
    engine.say("Привет! Это тест синтеза речи. Если вы меня слышите, значит всё работает правильно.")
    print("   Запуск синтеза...")
    engine.runAndWait()
    print("   ✓ Завершено")
    
    # Тест 3: Без runAndWait (асинхронно)
    print("\n   ТЕСТ 3: Асинхронное воспроизведение")
    print("   Озвучивание: 'Асинхронный тест'")
    engine.say("Асинхронный тест")
    print("   Запуск синтеза (без ожидания)...")
    engine.startLoop(False)
    engine.iterate()
    time.sleep(3)  # Ждём 3 секунды
    engine.endLoop()
    print("   ✓ Завершено")
    
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()

# Альтернативный тест с проверкой событий
print("\n3. Тест с обработкой событий...")
try:
    engine = pyttsx3.init(driverName='sapi5')
    
    # Устанавливаем русский голос
    voices = engine.getProperty("voices")
    if voices:
        for voice in voices:
            if "IRINA" in str(voice.id).upper():
                engine.setProperty("voice", voice.id)
                break
    
    engine.setProperty("rate", 150)
    engine.setProperty("volume", 1.0)
    
    print("   Озвучивание с обработкой событий...")
    
    # Регистрируем обработчики событий
    def onStart(name):
        print(f"   [Событие] Начало: {name}")
    
    def onWord(name, location, length):
        print(f"   [Событие] Слово: {name} на позиции {location}")
    
    def onEnd(name, completed):
        print(f"   [Событие] Конец: {name}, завершено: {completed}")
    
    engine.connect('started-utterance', onStart)
    engine.connect('started-word', onWord)
    engine.connect('finished-utterance', onEnd)
    
    engine.say("Тест с событиями. Один. Два. Три.")
    print("   Запуск...")
    engine.runAndWait()
    print("   ✓ Завершено")
    
except Exception as e:
    print(f"   ✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("РЕКОМЕНДАЦИИ:")
print("=" * 60)
print("Если звука всё ещё нет:")
print("1. Проверьте настройки Windows Speech (Панель управления → Речь)")
print("2. Попробуйте запустить от имени администратора")
print("3. Проверьте, не блокирует ли антивирус доступ к SAPI")
print("4. Убедитесь, что служба Windows Audio работает")
print("=" * 60)

