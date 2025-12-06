"""Скрипт диагностики микрофона."""

import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kim_core.logging import init_logger, logger
from kim_core.config import load_config


def list_devices():
    """Выводит список доступных аудиоустройств."""
    print("\n" + "=" * 60)
    print("Доступные аудиоустройства")
    print("=" * 60)
    
    try:
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        
        print(f"\nУстройство ввода по умолчанию: индекс {default_input}")
        print(f"Устройство вывода по умолчанию: индекс {default_output}\n")
        
        print("Устройства ввода (микрофоны):")
        print("-" * 60)
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                is_default = " (по умолчанию)" if i == default_input else ""
                print(f"  [{i}] {device['name']}{is_default}")
                print(f"      Частоты: {device['default_samplerate']} Hz")
                print(f"      Каналы: {device['max_input_channels']}")
        
        print("\nУстройства вывода (динамики):")
        print("-" * 60)
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                is_default = " (по умолчанию)" if i == default_output else ""
                print(f"  [{i}] {device['name']}{is_default}")
                print(f"      Частоты: {device['default_samplerate']} Hz")
                print(f"      Каналы: {device['max_output_channels']}")
        
        return devices, default_input
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка устройств: {e}")
        print(f"\n❌ Ошибка: {e}")
        return None, None


def test_microphone(device_index=None, duration=3.0, sample_rate=16000):
    """
    Тестирует микрофон: записывает аудио и анализирует.
    
    Args:
        device_index: Индекс устройства (None = по умолчанию)
        duration: Длительность записи в секундах
        sample_rate: Частота дискретизации
        
    Returns:
        dict: Результаты анализа
    """
    print("\n" + "=" * 60)
    print("Тест записи микрофона")
    print("=" * 60)
    
    device_name = "по умолчанию"
    if device_index is not None:
        try:
            device_info = sd.query_devices(device_index)
            device_name = device_info['name']
            print(f"\nИспользуемое устройство: [{device_index}] {device_name}")
        except Exception as e:
            logger.warning(f"Не удалось получить имя устройства {device_index}: {e}")
            device_name = f"устройство {device_index}"
    else:
        try:
            default_input = sd.default.device[0]
            if default_input is not None:
                device_info = sd.query_devices(default_input)
                device_name = device_info['name']
                print(f"\nИспользуемое устройство: [{default_input}] {device_name}")
        except Exception:
            pass
    
    print(f"Длительность записи: {duration} секунд")
    print(f"Частота дискретизации: {sample_rate} Hz")
    print("\n🎤 Говорите в микрофон...")
    
    try:
        # Записываем аудио
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16',
            device=device_index,
        )
        sd.wait()  # Ждём окончания записи
        
        # Анализируем запись
        audio_data = recording.flatten().astype(np.float32) / 32768.0  # Нормализуем в [-1, 1]
        
        # Вычисляем метрики
        max_amplitude = np.max(np.abs(audio_data))
        mean_amplitude = np.mean(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        # Проверяем на clipping (перегрузку)
        clipping_samples = np.sum(np.abs(audio_data) >= 0.99)
        clipping_percent = (clipping_samples / len(audio_data)) * 100
        
        # Уровень шума (RMS тишины - первые 0.5 секунды)
        silence_samples = int(0.5 * sample_rate)
        if len(audio_data) > silence_samples:
            noise_level = np.sqrt(np.mean(audio_data[:silence_samples] ** 2))
        else:
            noise_level = rms
        
        # Амплитуда в int16 единицах (для сравнения с порогами)
        max_amplitude_int16 = max_amplitude * 32767
        
        results = {
            'device_index': device_index,
            'device_name': device_name,
            'max_amplitude': max_amplitude,
            'max_amplitude_int16': max_amplitude_int16,
            'mean_amplitude': mean_amplitude,
            'rms': rms,
            'noise_level': noise_level,
            'clipping_samples': clipping_samples,
            'clipping_percent': clipping_percent,
            'sample_count': len(audio_data),
            'duration': len(audio_data) / sample_rate,
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при записи с микрофона: {e}")
        print(f"\n❌ Ошибка записи: {e}")
        return None


def analyze_results(results):
    """
    Анализирует результаты теста и выводит рекомендации.
    
    Args:
        results: Результаты теста от test_microphone()
    """
    if results is None:
        print("\n❌ Не удалось получить результаты теста")
        return
    
    print("\n" + "=" * 60)
    print("Результаты анализа")
    print("=" * 60)
    
    print(f"\nУстройство: {results['device_name']}")
    print(f"Максимальная амплитуда: {results['max_amplitude']:.4f} ({results['max_amplitude_int16']:.0f} в int16)")
    print(f"Средняя амплитуда: {results['mean_amplitude']:.4f}")
    print(f"RMS (среднеквадратичное): {results['rms']:.4f}")
    print(f"Уровень шума: {results['noise_level']:.4f}")
    print(f"Clipping (перегрузка): {results['clipping_samples']} сэмплов ({results['clipping_percent']:.2f}%)")
    
    print("\n" + "=" * 60)
    print("Рекомендации")
    print("=" * 60)
    
    recommendations = []
    
    # Проверка 1: Нулевая амплитуда
    if results['max_amplitude_int16'] < 1:
        recommendations.append({
            'level': '❌ КРИТИЧНО',
            'issue': 'Микрофон не работает или драйвер не установлен',
            'solutions': [
                'Проверьте подключение микрофона',
                'Убедитесь, что микрофон включён в настройках Windows',
                'Проверьте настройки приватности Windows (Параметры → Конфиденциальность → Микрофон)',
                'Попробуйте переустановить драйвер микрофона',
                'Проверьте, что микрофон выбран как устройство ввода по умолчанию',
            ],
        })
    
    # Проверка 2: Слишком громко (перегрузка)
    elif results['max_amplitude_int16'] > 30000:
        recommendations.append({
            'level': '⚠️ ПРЕДУПРЕЖДЕНИЕ',
            'issue': 'Слишком высокий уровень сигнала (перегрузка)',
            'solutions': [
                'Снизьте усиление (gain) микрофона в настройках Windows',
                'Отойдите дальше от микрофона',
                'Проверьте настройки микрофона в Панели управления → Звук → Запись',
                'Уменьшите уровень усиления в драйвере микрофона',
            ],
        })
    
    # Проверка 3: Clipping
    elif results['clipping_percent'] > 1.0:
        recommendations.append({
            'level': '⚠️ ПРЕДУПРЕЖДЕНИЕ',
            'issue': f'Обнаружено clipping ({results["clipping_percent"]:.1f}% сэмплов)',
            'solutions': [
                'Снизьте усиление микрофона',
                'Говорите тише или дальше от микрофона',
                'Проверьте настройки усиления в Windows',
            ],
        })
    
    # Проверка 4: Слишком тихо
    elif results['max_amplitude_int16'] < 1000:
        recommendations.append({
            'level': '⚠️ ПРЕДУПРЕЖДЕНИЕ',
            'issue': 'Слишком низкий уровень сигнала',
            'solutions': [
                'Увеличьте усиление микрофона в настройках Windows',
                'Говорите ближе к микрофону',
                'Проверьте настройки микрофона в Панели управления → Звук → Запись',
            ],
        })
    
    # Проверка 5: Высокий уровень шума
    elif results['noise_level'] > 0.01:
        recommendations.append({
            'level': 'ℹ️ ИНФОРМАЦИЯ',
            'issue': 'Высокий уровень фонового шума',
            'solutions': [
                'Используйте более тихое помещение',
                'Включите шумоподавление в настройках микрофона (если доступно)',
                'Рассмотрите использование направленного микрофона',
            ],
        })
    
    # Если всё хорошо
    if not recommendations:
        recommendations.append({
            'level': '✅ ОТЛИЧНО',
            'issue': 'Микрофон работает нормально',
            'solutions': [
                'Уровень сигнала в норме',
                'Clipping не обнаружен',
                'Можно использовать для работы с ассистентом',
            ],
        })
    
    # Выводим рекомендации
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['level']}: {rec['issue']}")
        print("   Решения:")
        for solution in rec['solutions']:
            print(f"   • {solution}")
    
    print("\n" + "=" * 60)


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Диагностика микрофона")
    parser.add_argument(
        "--device-index",
        type=int,
        default=None,
        help="Индекс устройства микрофона (по умолчанию: устройство по умолчанию)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Длительность записи в секундах (по умолчанию: 3.0)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Частота дискретизации (по умолчанию: 16000)",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Только показать список устройств, без теста",
    )
    
    args = parser.parse_args()
    
    # Загружаем конфигурацию для логирования
    try:
        config = load_config()
        init_logger(config)
    except Exception:
        # Если не удалось загрузить конфиг, продолжаем без логирования
        pass
    
    # Показываем список устройств
    devices, default_input = list_devices()
    
    if args.list_only:
        return
    
    # Если device_index не указан, используем по умолчанию
    device_index = args.device_index
    if device_index is None:
        device_index = default_input
    
    # Тестируем микрофон
    results = test_microphone(
        device_index=device_index,
        duration=args.duration,
        sample_rate=args.sample_rate,
    )
    
    # Анализируем результаты
    analyze_results(results)
    
    # Сохраняем результаты для использования в ассистенте
    if results and results['device_name']:
        print(f"\n💡 Для использования этого микрофона в ассистенте:")
        if device_index is not None:
            print(f"   Установите в .env: MIC_DEVICE_INDEX={device_index}")
        print(f"   Имя устройства: {results['device_name']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Ошибка при диагностике: {e}")
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)

