"""Smoke-тест для проверки диагностики системы."""

import sys
import time
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from kim_desktop.diagnostics.system_info import SystemMetrics, get_metrics


def test_diag_cpu() -> bool:
    """
    Проверяет, что диагностика системы может получить метрики CPU/RAM.

    Returns:
        bool: True если диагностика работает корректно
    """
    try:
        # Инициализация логирования
        config = load_config()
        init_logger(config)
        
        logger.info("=" * 60)
        logger.info("Smoke test: System Diagnostics")
        logger.info("=" * 60)
        
        # Проверка получения метрик
        try:
            logger.info("Получение метрик системы...")
            time.sleep(1)
            
            metrics = get_metrics()
            
            if not metrics:
                logger.error("❌ Не удалось получить метрики системы")
                return False
            
            # Проверяем ключевые метрики
            checks = []
            
            if metrics.cpu_percent is not None:
                logger.info(f"✓ CPU: {metrics.cpu_percent:.1f}%")
                checks.append(True)
            else:
                logger.warning("⚠ CPU метрика не доступна")
                checks.append(False)
            
            if metrics.ram_percent is not None:
                logger.info(f"✓ RAM: {metrics.ram_percent:.1f}%")
                checks.append(True)
            else:
                logger.warning("⚠ RAM метрика не доступна")
                checks.append(False)
            
            if metrics.disk_percent is not None:
                logger.info(f"✓ Disk: {metrics.disk_percent:.1f}%")
                checks.append(True)
            else:
                logger.warning("⚠ Disk метрика не доступна")
                checks.append(False)
            
            if metrics.temperature is not None:
                logger.info(f"✓ Temperature: {metrics.temperature:.1f}°C")
            else:
                logger.info("ℹ Temperature: не доступна (нормально для некоторых систем)")
            
            # Должны быть хотя бы CPU и RAM
            if not any(checks[:2]):
                logger.error("❌ Критические метрики (CPU/RAM) не доступны")
                return False
            
            logger.info("✅ System diagnostics test: PASSED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении метрик: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_diag_cpu()
    sys.exit(0 if success else 1)

