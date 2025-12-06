"""Вспомогательный скрипт для подготовки тестовых образцов hotword."""

from pathlib import Path


def main():
    """Создаёт структуру директорий и инструкции для тестовых образцов."""
    samples_dir = Path("test_samples/hotword")
    
    # Создаём директорию
    samples_dir.mkdir(parents=True, exist_ok=True)
    print(f"Директория создана: {samples_dir}")
    
    # Создаём .gitkeep, чтобы директория попала в git
    gitkeep = samples_dir / ".gitkeep"
    gitkeep.touch()
    print(f"Создан файл: {gitkeep}")
    
    # Создаём примеры имён файлов
    example_names = {
        "positive": [
            "positive_kim_1.wav",
            "positive_kim_2.wav",
            "kim_activation.wav",
            "kim_quiet.wav",
            "kim_noisy.wav",
        ],
        "negative": [
            "negative_no_kim_1.wav",
            "negative_no_kim_2.wav",
            "no_kim_test.wav",
            "background_noise.wav",
            "other_commands.wav",
        ],
    }
    
    # Создаём текстовый файл с примерами имён
    examples_file = samples_dir / "example_filenames.txt"
    with open(examples_file, "w", encoding="utf-8") as f:
        f.write("Примеры имён файлов для тестовых образцов\n")
        f.write("=" * 60 + "\n\n")
        f.write("ПОЛОЖИТЕЛЬНЫЕ ПРИМЕРЫ (должны срабатывать hotword):\n")
        f.write("-" * 60 + "\n")
        for name in example_names["positive"]:
            f.write(f"  {name}\n")
        f.write("\n")
        f.write("ОТРИЦАТЕЛЬНЫЕ ПРИМЕРЫ (не должны срабатывать hotword):\n")
        f.write("-" * 60 + "\n")
        for name in example_names["negative"]:
            f.write(f"  {name}\n")
        f.write("\n")
        f.write("ИНСТРУКЦИИ:\n")
        f.write("-" * 60 + "\n")
        f.write("1. Запишите или скачайте аудио-файлы\n")
        f.write("2. Переименуйте их согласно примерам выше\n")
        f.write("3. Поместите файлы в эту директорию\n")
        f.write("4. Запустите: python scripts/test_hotword_accuracy.py\n")
    
    print(f"Создан файл с примерами: {examples_file}")
    
    print("\n" + "=" * 60)
    print("Директория для тестовых образцов подготовлена!")
    print("=" * 60)
    print(f"\nДиректория: {samples_dir.absolute()}")
    print("\nСледующие шаги:")
    print("1. Добавьте аудио-файлы в директорию")
    print("2. Используйте имена с 'positive' или 'kim' для файлов, которые должны срабатывать")
    print("3. Используйте имена с 'negative' или 'no_kim' для файлов, которые не должны срабатывать")
    print("4. Запустите тестирование: python scripts/test_hotword_accuracy.py")
    print("\nПодробные инструкции см. в test_samples/hotword/README.md")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

