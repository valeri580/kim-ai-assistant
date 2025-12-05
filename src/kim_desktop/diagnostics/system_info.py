"""Модуль диагностики системы: сбор метрик и проверка порогов."""

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import psutil

from kim_core.logging import logger


@dataclass
class SystemMetrics:
    """Метрики системы."""

    cpu_percent: float
    ram_percent: float
    disk_percent: float
    temperature: Optional[float] = None


@dataclass
class Thresholds:
    """Пороги для предупреждений."""

    cpu_warn: float = 85.0
    ram_warn: float = 90.0
    disk_warn: float = 90.0
    temp_warn: Optional[float] = None  # например, 80.0, если поддерживается


def get_metrics(disk_path: str = "/") -> SystemMetrics:
    """
    Собирает метрики системы.

    Args:
        disk_path: Путь к диску для проверки (по умолчанию корень системы)

    Returns:
        SystemMetrics: Собранные метрики
    """
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    logger.debug(f"CPU загрузка: {cpu_percent:.1f}%")

    # RAM
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    logger.debug(f"RAM использование: {ram_percent:.1f}% ({ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB)")

    # Диск
    try:
        # На Windows используем диск C: если указан корень
        if disk_path == "/" or disk_path == "\\":
            # Определяем системный диск автоматически
            if platform.system() == "Windows":
                disk_path = "C:"
            else:
                # Для Linux/macOS используем корневой диск
                disk_path = "/"

        disk = psutil.disk_usage(disk_path)
        disk_percent = disk.percent
        logger.debug(
            f"Диск {disk_path} использование: {disk_percent:.1f}% "
            f"({disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB)"
        )
    except Exception as e:
        logger.warning(f"Ошибка получения информации о диске {disk_path}: {e}")
        disk_percent = 0.0

    # Температура
    temperature = None
    try:
        sensors = psutil.sensors_temperatures()
        if sensors:
            # Берём первую доступную температуру
            for sensor_name, entries in sensors.items():
                if entries:
                    # Берём максимальную температуру среди всех значений этого сенсора
                    temps = [entry.current for entry in entries if entry.current is not None]
                    if temps:
                        temperature = max(temps)
                        logger.debug(f"Температура ({sensor_name}): {temperature:.1f}°C")
                        break
    except (AttributeError, Exception) as e:
        # psutil.sensors_temperatures() может быть недоступен на некоторых платформах
        logger.debug(f"Температура недоступна: {e}")
        temperature = None

    metrics = SystemMetrics(
        cpu_percent=cpu_percent,
        ram_percent=ram_percent,
        disk_percent=disk_percent,
        temperature=temperature,
    )

    logger.info(
        f"Метрики: CPU={metrics.cpu_percent:.1f}%, "
        f"RAM={metrics.ram_percent:.1f}%, "
        f"Диск={metrics.disk_percent:.1f}%"
        + (f", Температура={metrics.temperature:.1f}°C" if metrics.temperature is not None else "")
    )

    return metrics


def check_thresholds(metrics: SystemMetrics, thresholds: Thresholds) -> list[str]:
    """
    Проверяет метрики на превышение порогов.

    Args:
        metrics: Метрики системы
        thresholds: Пороги для проверки

    Returns:
        list[str]: Список текстовых предупреждений (пустой, если всё в норме)
    """
    warnings = []

    # Проверка CPU
    if metrics.cpu_percent >= thresholds.cpu_warn:
        warnings.append(f"Высокая загрузка CPU: {metrics.cpu_percent:.1f}% (порог: {thresholds.cpu_warn}%)")

    # Проверка RAM
    if metrics.ram_percent >= thresholds.ram_warn:
        warnings.append(
            f"Мало свободной оперативной памяти: {metrics.ram_percent:.1f}% используется "
            f"(порог: {thresholds.ram_warn}%)"
        )

    # Проверка диска
    if metrics.disk_percent >= thresholds.disk_warn:
        warnings.append(
            f"Мало свободного места на диске: {metrics.disk_percent:.1f}% используется "
            f"(порог: {thresholds.disk_warn}%)"
        )

    # Проверка температуры
    if thresholds.temp_warn is not None and metrics.temperature is not None:
        if metrics.temperature >= thresholds.temp_warn:
            warnings.append(
                f"Высокая температура: {metrics.temperature:.1f}°C (порог: {thresholds.temp_warn}°C)"
            )

    return warnings

