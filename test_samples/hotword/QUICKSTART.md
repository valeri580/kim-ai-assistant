# Быстрый старт: Тестирование точности hotword

## Шаг 1: Генерация тестовых файлов (автоматически)

```bash
python scripts/generate_hotword_test_samples.py
```

Скрипт автоматически создаст 10 тестовых аудио-файлов с использованием TTS.

## Шаг 2: Или добавьте файлы вручную

Если хотите использовать свои аудио-файлы, поместите их в директорию `test_samples/hotword/`:

- **Положительные** (должны срабатывать): имена с `positive` или `kim`
  - Пример: `positive_kim_1.wav`, `kim_activation.wav`

- **Отрицательные** (не должны срабатывать): имена с `negative` или `no_kim`
  - Пример: `negative_no_kim_1.wav`, `no_kim_test.wav`

## Шаг 3: Запуск тестирования

```bash
python scripts/test_hotword_accuracy.py
```

## Шаг 4: Применение результатов

Скрипт выведет рекомендуемые параметры. Добавьте их в `.env`:

```env
HOTWORD_MIN_CONFIDENCE=0.48
HOTWORD_MIN_CHARS=3
```

## Результаты

- Метрики в консоли: Precision, Recall, F1-Score, Accuracy
- Детальный отчёт: `test_hotword_accuracy.log`

## Параметры скрипта

```bash
# Базовое использование
python scripts/test_hotword_accuracy.py

# Без автотюнинга
python scripts/test_hotword_accuracy.py --no-auto-tune

# С заданными параметрами
python scripts/test_hotword_accuracy.py --min-confidence 0.6 --min-chars 3

# Другая директория
python scripts/test_hotword_accuracy.py --samples-dir my_samples/hotword
```

