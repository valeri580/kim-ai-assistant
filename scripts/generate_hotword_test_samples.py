"""Скрипт для генерации тестовых аудио-файлов для hotword."""

import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Предупреждение: pyttsx3 не установлен, будут созданы только простые аудио-сигналы")


def generate_silence(duration_seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Генерирует тишину."""
    num_samples = int(duration_seconds * sample_rate)
    return np.zeros(num_samples, dtype=np.float32)


def generate_noise(duration_seconds: float = 1.0, sample_rate: int = 16000, amplitude: float = 0.1) -> np.ndarray:
    """Генерирует белый шум."""
    num_samples = int(duration_seconds * sample_rate)
    return (np.random.randn(num_samples) * amplitude).astype(np.float32)


def generate_tone(frequency: float, duration_seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Генерирует синусоидальный тон."""
    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, num_samples, False)
    return (np.sin(2 * np.pi * frequency * t) * 0.3).astype(np.float32)


def generate_tts_audio(text: str, output_file: Path, sample_rate: int = 16000) -> bool:
    """
    Генерирует аудио через TTS и сохраняет в файл.
    
    Args:
        text: Текст для произнесения
        output_file: Путь к выходному файлу
        sample_rate: Частота дискретизации
        
    Returns:
        bool: True если успешно
    """
    if not TTS_AVAILABLE:
        return False
    
    try:
        engine = pyttsx3.init()
        
        # Настройки голоса (женский, если доступен)
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'female' in voice.name.lower() or 'женский' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        # Сохраняем во временный файл
        temp_file = output_file.with_suffix('.tmp.wav')
        engine.save_to_file(text, str(temp_file))
        engine.runAndWait()
        
        # Читаем и ресемплируем до нужной частоты
        if temp_file.exists():
            data, orig_sr = sf.read(str(temp_file))
            
            # Конвертируем в моно, если стерео
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Ресемплируем, если нужно
            if orig_sr != sample_rate:
                from scipy import signal
                num_samples = int(len(data) * sample_rate / orig_sr)
                data = signal.resample(data, num_samples)
            
            # Нормализуем и сохраняем
            if np.max(np.abs(data)) > 0:
                data = data / np.max(np.abs(data)) * 0.8
            
            sf.write(str(output_file), data, sample_rate)
            temp_file.unlink()  # Удаляем временный файл
            
            return True
    except Exception as e:
        print(f"Ошибка генерации TTS для '{text}': {e}")
        return False
    
    return False


def generate_test_samples(output_dir: Path, sample_rate: int = 16000):
    """Генерирует набор тестовых аудио-файлов."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Генерация тестовых аудио-файлов для hotword...")
    print(f"Выходная директория: {output_dir}")
    print()
    
    # Положительные примеры (должны срабатывать)
    print("Создание положительных примеров...")
    positive_samples = [
        ("positive_kim_1.wav", "Ким"),
        ("positive_kim_2.wav", "Ким, привет"),
        ("kim_activation.wav", "Ким"),
        ("kim_quiet.wav", "Ким"),  # Будет тише
        ("kim_noisy.wav", "Ким"),  # С шумом
    ]
    
    for filename, text in positive_samples:
        filepath = output_dir / filename
        if generate_tts_audio(text, filepath, sample_rate):
            print(f"  ✓ {filename} (TTS: '{text}')")
        else:
            # Fallback: создаём простой сигнал
            audio = generate_tone(440, 0.5, sample_rate)
            sf.write(str(filepath), audio, sample_rate)
            print(f"  ✓ {filename} (синусоида)")
    
    print()
    
    # Отрицательные примеры (не должны срабатывать)
    print("Создание отрицательных примеров...")
    negative_samples = [
        ("negative_no_kim_1.wav", "Привет"),
        ("negative_no_kim_2.wav", "Как дела"),
        ("no_kim_test.wav", "Алиса"),
        ("background_noise.wav", None),  # Только шум
        ("other_commands.wav", "Окей Гугл"),
    ]
    
    for filename, text in negative_samples:
        filepath = output_dir / filename
        
        if text:
            if generate_tts_audio(text, filepath, sample_rate):
                print(f"  ✓ {filename} (TTS: '{text}')")
            else:
                # Fallback: создаём простой сигнал другой частоты
                audio = generate_tone(880, 0.5, sample_rate)
                sf.write(str(filepath), audio, sample_rate)
                print(f"  ✓ {filename} (синусоида)")
        else:
            # Только шум
            audio = generate_noise(1.0, sample_rate, amplitude=0.2)
            sf.write(str(filepath), audio, sample_rate)
            print(f"  ✓ {filename} (шум)")
    
    print()
    print("=" * 60)
    print("Генерация завершена!")
    print("=" * 60)
    print(f"\nСоздано файлов: {len(positive_samples) + len(negative_samples)}")
    print(f"  Положительных: {len(positive_samples)}")
    print(f"  Отрицательных: {len(negative_samples)}")
    print(f"\nДиректория: {output_dir.absolute()}")
    print("\nТеперь можно запустить тестирование:")
    print(f"  python scripts/test_hotword_accuracy.py --samples-dir {output_dir}")
    print("=" * 60)


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генерация тестовых аудио-файлов для hotword")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="test_samples/hotword",
        help="Директория для сохранения файлов (по умолчанию: test_samples/hotword)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Частота дискретизации (по умолчанию: 16000)",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    generate_test_samples(output_dir, args.sample_rate)


if __name__ == "__main__":
    main()

