"""Скрипт для тестирования точности детекции hotword «Ким»."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import vosk

# Добавляем корень проекта и src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

from kim_core.logging import init_logger, logger
from kim_core.config import load_config
from kim_voice.hotword.kim_hotword import HotwordConfig


class HotwordAccuracyTester:
    """Тестер точности детекции hotword."""
    
    def __init__(self, model_path: str, test_samples_dir: Path):
        """
        Инициализирует тестер.
        
        Args:
            model_path: Путь к модели Vosk
            test_samples_dir: Директория с тестовыми аудио-файлами
        """
        self.model_path = model_path
        self.test_samples_dir = test_samples_dir
        self.model = None
        self.rec = None
        
    def _load_model(self):
        """Загружает модель Vosk."""
        if self.model is None:
            logger.info(f"Загрузка модели Vosk из {self.model_path}...")
            self.model = vosk.Model(self.model_path)
            self.rec = vosk.KaldiRecognizer(self.model, 16000)
            self.rec.SetWords(True)
            logger.info("Модель Vosk загружена")
    
    def _test_audio_file(
        self,
        audio_file: Path,
        expected_trigger: bool,
        config: HotwordConfig,
    ) -> tuple[bool, Optional[str], float]:
        """
        Тестирует один аудио-файл.
        
        Args:
            audio_file: Путь к аудио-файлу
            expected_trigger: Ожидается ли срабатывание hotword
            config: Конфигурация hotword
            
        Returns:
            tuple[bool, Optional[str], float]: (сработало ли, распознанный текст, уверенность)
        """
        self._load_model()
        
        try:
            # Читаем аудио-файл
            data, sample_rate = sf.read(str(audio_file))
            
            # Конвертируем в моно, если стерео
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Ресемплируем до 16000 Hz, если нужно
            if sample_rate != 16000:
                from scipy import signal
                num_samples = int(len(data) * 16000 / sample_rate)
                data = signal.resample(data, num_samples)
                sample_rate = 16000
            
            # Конвертируем в int16
            data_int16 = (data * 32767).astype(np.int16)
            audio_bytes = data_int16.tobytes()
            
            # Сбрасываем распознаватель
            self.rec = vosk.KaldiRecognizer(self.model, 16000)
            self.rec.SetWords(True)
            
            # Обрабатываем аудио чанками
            chunk_size = 4000
            triggered = False
            recognized_text = None
            confidence = 0.0
            
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    # Дополняем последний чанк нулями
                    chunk = chunk + b'\x00' * (chunk_size - len(chunk))
                
                result_ready = self.rec.AcceptWaveform(chunk)
                
                if result_ready:
                    result_str = self.rec.Result()
                    try:
                        result = json.loads(result_str)
                        text = result.get("text", "").strip()
                        
                        if text:
                            # Вычисляем confidence
                            conf = 1.0
                            if "confidence" in result:
                                conf = float(result["confidence"])
                            elif "result" in result and isinstance(result["result"], list):
                                confidences = [
                                    r.get("conf", 1.0)
                                    for r in result["result"]
                                    if isinstance(r, dict) and "conf" in r
                                ]
                                if confidences:
                                    conf = sum(confidences) / len(confidences)
                            
                            # Проверяем фильтры
                            if len(text) >= config.min_chars_in_utterance:
                                if conf >= config.min_hotword_confidence:
                                    # Проверяем, является ли это hotword
                                    normalized = text.lower().strip()
                                    import string
                                    for punct in string.punctuation:
                                        normalized = normalized.replace(punct, " ")
                                    words = [w for w in normalized.split() if w]
                                    
                                    is_hotword = False
                                    if config.require_strict_word_match:
                                        is_hotword = any(word == "ким" for word in words)
                                    else:
                                        is_hotword = any("ким" in word for word in words) or normalized == "ким"
                                    
                                    if is_hotword:
                                        triggered = True
                                        recognized_text = text
                                        confidence = conf
                                        break
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            # Проверяем финальный результат
            if not triggered:
                final_str = self.rec.FinalResult()
                if final_str:
                    try:
                        result = json.loads(final_str)
                        text = result.get("text", "").strip()
                        if text:
                            conf = 1.0
                            if "confidence" in result:
                                conf = float(result["confidence"])
                            elif "result" in result and isinstance(result["result"], list):
                                confidences = [
                                    r.get("conf", 1.0)
                                    for r in result["result"]
                                    if isinstance(r, dict) and "conf" in r
                                ]
                                if confidences:
                                    conf = sum(confidences) / len(confidences)
                            
                            if len(text) >= config.min_chars_in_utterance:
                                if conf >= config.min_hotword_confidence:
                                    normalized = text.lower().strip()
                                    import string
                                    for punct in string.punctuation:
                                        normalized = normalized.replace(punct, " ")
                                    words = [w for w in normalized.split() if w]
                                    
                                    is_hotword = False
                                    if config.require_strict_word_match:
                                        is_hotword = any(word == "ким" for word in words)
                                    else:
                                        is_hotword = any("ким" in word for word in words) or normalized == "ким"
                                    
                                    if is_hotword:
                                        triggered = True
                                        recognized_text = text
                                        confidence = conf
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            return triggered, recognized_text, confidence
            
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {audio_file}: {e}")
            return False, None, 0.0
    
    def _determine_expected_trigger(self, audio_file: Path) -> bool:
        """
        Определяет, должно ли срабатывать hotword для файла.
        
        Логика:
        - Сначала проверяем отрицательные маркеры (приоритет)
        - Затем проверяем положительные маркеры
        - По умолчанию: не ожидается срабатывание
        
        Args:
            audio_file: Путь к аудио-файлу
            
        Returns:
            bool: Ожидается ли срабатывание
        """
        filename_lower = audio_file.name.lower()
        
        # Сначала проверяем отрицательные маркеры (приоритет выше)
        if "negative" in filename_lower:
            return False
        if "no_kim" in filename_lower or "no-kim" in filename_lower:
            return False
        if "background" in filename_lower and "noise" in filename_lower:
            return False
        if "other" in filename_lower and "command" in filename_lower:
            return False
        
        # Затем проверяем положительные маркеры
        if "positive" in filename_lower:
            return True
        # Проверяем "kim" только если это не часть "no_kim" или "no_kim_test"
        # Важно: проверяем, что "no" стоит перед "kim" или является частью "no_kim"
        if "kim" in filename_lower:
            # Если есть "no" перед "kim" или "no_kim" - это отрицательный
            if "no_kim" in filename_lower or "no-kim" in filename_lower:
                return False
            # Если просто "kim" без "no" перед ним - положительный
            return True
        # Проверяем кириллицу
        if "ким" in filename_lower:
            return True
        
        # По умолчанию считаем, что не должно срабатывать
        return False
    
    def run_tests(
        self,
        config: HotwordConfig,
        auto_tune: bool = True,
        max_iterations: int = 10,
    ) -> dict:
        """
        Запускает тесты на всех аудио-файлах.
        
        Args:
            config: Конфигурация hotword
            auto_tune: Включить автотюнинг
            max_iterations: Максимальное количество итераций автотюнинга
            
        Returns:
            dict: Результаты тестирования
        """
        if not self.test_samples_dir.exists():
            logger.error(f"Директория с тестовыми образцами не найдена: {self.test_samples_dir}")
            return {}
        
        # Находим все аудио-файлы
        audio_extensions = [".wav", ".mp3", ".flac", ".ogg", ".m4a"]
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(self.test_samples_dir.glob(f"*{ext}"))
            audio_files.extend(self.test_samples_dir.glob(f"*{ext.upper()}"))
        
        if not audio_files:
            logger.error(f"Не найдено аудио-файлов в {self.test_samples_dir}")
            return {
                "final_config": {
                    "min_hotword_confidence": config.min_hotword_confidence,
                    "min_chars_in_utterance": config.min_chars_in_utterance,
                },
                "metrics": {
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "accuracy": 0.0,
                },
                "counts": {
                    "tp": 0,
                    "fp": 0,
                    "fn": 0,
                    "tn": 0,
                },
                "results": [],
                "iterations": 0,
            }
        
        logger.info(f"Найдено {len(audio_files)} аудио-файлов для тестирования")
        
        current_config = config
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Итерация {iteration}")
            logger.info(f"Конфигурация: min_hotword_confidence={current_config.min_hotword_confidence:.2f}, "
                       f"min_chars_in_utterance={current_config.min_chars_in_utterance}")
            logger.info(f"{'='*60}\n")
            
            # Результаты тестирования
            results = []
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            true_negatives = 0
            
            for audio_file in sorted(audio_files):
                expected = self._determine_expected_trigger(audio_file)
                triggered, text, confidence = self._test_audio_file(audio_file, expected, current_config)
                
                # Классифицируем результат
                if expected and triggered:
                    true_positives += 1
                    status = "✓ TP"
                elif expected and not triggered:
                    false_negatives += 1
                    status = "✗ FN"
                elif not expected and triggered:
                    false_positives += 1
                    status = "✗ FP"
                else:
                    true_negatives += 1
                    status = "✓ TN"
                
                results.append({
                    "file": audio_file.name,
                    "expected": expected,
                    "triggered": triggered,
                    "text": text,
                    "confidence": confidence,
                    "status": status,
                })
                
                logger.info(
                    f"{status} | {audio_file.name:30s} | "
                    f"expected={expected}, triggered={triggered}, "
                    f"text='{text}', conf={confidence:.2f}"
                )
            
            # Вычисляем метрики
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            accuracy = (true_positives + true_negatives) / len(audio_files) if audio_files else 0.0
            
            logger.info(f"\n{'='*60}")
            logger.info("Результаты тестирования:")
            logger.info(f"  True Positives (TP):  {true_positives}")
            logger.info(f"  False Positives (FP): {false_positives}")
            logger.info(f"  False Negatives (FN): {false_negatives}")
            logger.info(f"  True Negatives (TN):  {true_negatives}")
            logger.info(f"  Precision: {precision:.3f}")
            logger.info(f"  Recall:    {recall:.3f}")
            logger.info(f"  F1-Score:  {f1:.3f}")
            logger.info(f"  Accuracy:  {accuracy:.3f}")
            logger.info(f"{'='*60}\n")
            
            # Автотюнинг
            if auto_tune and precision < 0.9:
                logger.info(f"Precision ({precision:.3f}) < 0.9, запускаю автотюнинг...")
                
                # Уменьшаем min_hotword_confidence
                new_confidence = current_config.min_hotword_confidence - 0.02
                if new_confidence < 0.1:
                    new_confidence = 0.1
                
                # Если много ложных срабатываний, увеличиваем min_chars_in_utterance
                if false_positives > true_positives:
                    new_min_chars = current_config.min_chars_in_utterance + 1
                    if new_min_chars > 20:
                        new_min_chars = 20
                    logger.info(f"Много ложных срабатываний, увеличиваю min_chars_in_utterance до {new_min_chars}")
                    current_config = HotwordConfig(
                        **{**current_config.__dict__, "min_hotword_confidence": new_confidence, "min_chars_in_utterance": new_min_chars}
                    )
                else:
                    current_config = HotwordConfig(
                        **{**current_config.__dict__, "min_hotword_confidence": new_confidence}
                    )
                
                logger.info(f"Новая конфигурация: min_hotword_confidence={current_config.min_hotword_confidence:.2f}, "
                           f"min_chars_in_utterance={current_config.min_chars_in_utterance}")
            else:
                # Достигли нужной точности или отключен автотюнинг
                break
        
        return {
            "final_config": {
                "min_hotword_confidence": current_config.min_hotword_confidence,
                "min_chars_in_utterance": current_config.min_chars_in_utterance,
            },
            "metrics": {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "accuracy": accuracy,
            },
            "counts": {
                "tp": true_positives,
                "fp": false_positives,
                "fn": false_negatives,
                "tn": true_negatives,
            },
            "results": results,
            "iterations": iteration,
        }


def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование точности детекции hotword «Ким»")
    parser.add_argument(
        "--samples-dir",
        type=str,
        default="test_samples/hotword",
        help="Директория с тестовыми аудио-файлами (по умолчанию: test_samples/hotword)",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Путь к модели Vosk (по умолчанию: из VOSK_MODEL_PATH или models/vosk-ru)",
    )
    parser.add_argument(
        "--no-auto-tune",
        action="store_true",
        help="Отключить автотюнинг",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Начальное значение min_hotword_confidence (по умолчанию: 0.5)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=None,
        help="Начальное значение min_chars_in_utterance (по умолчанию: 2)",
    )
    
    args = parser.parse_args()
    
    # Загружаем конфигурацию
    config = load_config()
    init_logger(config)
    
    # Определяем путь к модели
    if args.model_path:
        model_path = args.model_path
    else:
        model_path = os.getenv("VOSK_MODEL_PATH", "models/vosk-ru")
    
    if not os.path.exists(model_path):
        logger.error(f"Модель Vosk не найдена: {model_path}")
        sys.exit(1)
    
    # Определяем директорию с тестовыми образцами
    samples_dir = Path(args.samples_dir)
    if not samples_dir.exists():
        logger.error(f"Директория с тестовыми образцами не найдена: {samples_dir}")
        logger.info("Создайте директорию и добавьте аудио-файлы:")
        logger.info("  - Файлы с 'positive' или 'kim' в имени — должны срабатывать")
        logger.info("  - Файлы с 'negative' или 'no_kim' в имени — не должны срабатывать")
        sys.exit(1)
    
    # Создаём конфигурацию hotword
    hotword_config = HotwordConfig(
        model_path=model_path,
        sample_rate=16000,
        chunk_size=4000,
        confidence_threshold=0.7,
        debounce_seconds=1.2,
        min_hotword_confidence=args.min_confidence if args.min_confidence is not None else 0.5,
        min_chars_in_utterance=args.min_chars if args.min_chars is not None else 2,
        require_strict_word_match=True,
        adaptive_threshold=False,  # Отключаем для тестирования
    )
    
    # Создаём тестер
    tester = HotwordAccuracyTester(model_path, samples_dir)
    
    # Запускаем тесты
    logger.info("Начинаю тестирование точности hotword...")
    results = tester.run_tests(hotword_config, auto_tune=not args.no_auto_tune)
    
    # Сохраняем отчёт
    report_file = Path("test_hotword_accuracy.log")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("Отчёт о тестировании точности hotword «Ким»\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Модель: {model_path}\n")
        f.write(f"Тестовые образцы: {samples_dir}\n")
        f.write(f"Итераций: {results['iterations']}\n\n")
        f.write("Финальная конфигурация:\n")
        f.write(f"  min_hotword_confidence: {results['final_config']['min_hotword_confidence']:.2f}\n")
        f.write(f"  min_chars_in_utterance: {results['final_config']['min_chars_in_utterance']}\n\n")
        f.write("Метрики:\n")
        f.write(f"  Precision: {results['metrics']['precision']:.3f}\n")
        f.write(f"  Recall:    {results['metrics']['recall']:.3f}\n")
        f.write(f"  F1-Score:  {results['metrics']['f1']:.3f}\n")
        f.write(f"  Accuracy:  {results['metrics']['accuracy']:.3f}\n\n")
        f.write("Счётчики:\n")
        f.write(f"  TP: {results['counts']['tp']}\n")
        f.write(f"  FP: {results['counts']['fp']}\n")
        f.write(f"  FN: {results['counts']['fn']}\n")
        f.write(f"  TN: {results['counts']['tn']}\n\n")
        f.write("Детальные результаты:\n")
        for r in results['results']:
            f.write(f"  {r['status']} | {r['file']:30s} | "
                   f"expected={r['expected']}, triggered={r['triggered']}, "
                   f"text='{r['text']}', conf={r['confidence']:.2f}\n")
    
    logger.info(f"\nОтчёт сохранён в {report_file}")
    logger.info(f"\nРекомендуемые параметры для .env:")
    logger.info(f"  HOTWORD_MIN_CONFIDENCE={results['final_config']['min_hotword_confidence']:.2f}")
    logger.info(f"  HOTWORD_MIN_CHARS={results['final_config']['min_chars_in_utterance']}")


if __name__ == "__main__":
    main()

