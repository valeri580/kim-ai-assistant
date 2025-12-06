"""Общий runner для всех smoke-тестов."""

import asyncio
import sys
import time
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.logging import init_logger, logger
from kim_core.config import load_config


def run_smoke_tests() -> bool:
    """
    Запускает все smoke-тесты и выводит результаты.

    Returns:
        bool: True если все тесты прошли успешно
    """
    # Инициализация логирования
    config = load_config()
    init_logger(config)
    
    print("\n" + "=" * 60)
    print("Запуск smoke-тестов")
    print("=" * 60 + "\n")
    
    # Добавляем scripts в путь для импорта тестов
    scripts_path = project_root / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    tests = [
        ("Voice", "tests_smoke.test_voice_activation", "test_voice_activation"),
        ("TG", "tests_smoke.test_tg_llm", "test_tg_llm"),
        ("Web", "tests_smoke.test_web_search", "test_web_search"),
        ("Calendar", "tests_smoke.test_calendar_trigger", "test_calendar_trigger"),
        ("Diag", "tests_smoke.test_diag_cpu", "test_diag_cpu"),
    ]
    
    results = []
    
    for test_name, module_name, function_name in tests:
        try:
            print(f"Запуск теста: {test_name}...")
            
            # Импортируем модуль
            module = __import__(module_name, fromlist=[function_name])
            test_func = getattr(module, function_name)
            
            # Запускаем тест
            if asyncio.iscoroutinefunction(test_func):
                success = asyncio.run(test_func())
            else:
                success = test_func()
            
            if success:
                print(f"[OK] {test_name}")
                results.append((test_name, True))
            else:
                print(f"[FAIL] {test_name}")
                results.append((test_name, False))
            
            # Небольшая пауза между тестами
            time.sleep(0.5)
            
        except ImportError as e:
            print(f"[ERROR] {test_name}: не удалось импортировать модуль: {e}")
            results.append((test_name, False))
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
            results.append((test_name, False))
    
    # Итоговый отчёт
    print("\n" + "=" * 60)
    print("Результаты smoke-тестов:")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")
    
    print("=" * 60)
    print(f"Пройдено: {passed}/{total}")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)

