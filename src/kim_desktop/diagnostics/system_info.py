"""Модуль диагностики системы: сбор метрик и проверка порогов."""

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import psutil

from kim_core.logging import logger


def format_telegram_message(warnings: list[str], recommendations: list[str]) -> str:
    """
    Форматирует сообщение для Telegram с Markdown.

    Args:
        warnings: Список предупреждений
        recommendations: Список рекомендаций

    Returns:
        Отформатированное сообщение в Markdown
    """
    if not warnings:
        return "✅ Все метрики в норме."

    message_parts = ["⚠️ *Диагностика ПК: обнаружены проблемы*\n"]

    # Предупреждения
    for warning in warnings:
        message_parts.append(f"• {warning}")

    # Рекомендации
    if recommendations:
        message_parts.append("\n💡 *Рекомендации:*")
        for recommendation in recommendations:
            message_parts.append(f"• {recommendation}")

    return "\n".join(message_parts)


def format_voice_message(warnings: list[str], recommendations: list[str]) -> str:
    """
    Форматирует краткое сообщение для голосового вывода.

    Args:
        warnings: Список предупреждений
        recommendations: Список рекомендаций

    Returns:
        Краткое сообщение для голосового вывода
    """
    if not warnings:
        return "Все метрики в норме."

    # Формируем краткие фразы
    voice_parts = []

    # Краткие предупреждения (убираем дубликаты)
    has_cpu = any("CPU" in w for w in warnings)
    has_ram = any("RAM" in w or "память" in w for w in warnings)
    has_disk = any("диск" in w.lower() for w in warnings)
    has_temp = any("температура" in w.lower() for w in warnings)

    if has_cpu:
        voice_parts.append("высокая загрузка процессора")
    if has_ram:
        voice_parts.append("мало памяти")
    if has_disk:
        voice_parts.append("мало места на диске")
    if has_temp:
        voice_parts.append("высокая температура")

    # Формируем сообщение
    if voice_parts:
        message = "Обнаружены проблемы: " + ", ".join(voice_parts) + "."
    else:
        message = "Обнаружены проблемы с системой."

    # Добавляем рекомендации, если есть
    if recommendations:
        message += " " + ". ".join(recommendations) + "."
    
    # Ограничиваем длину для голосового вывода
    if len(message) > 250:
        message = message[:247] + "..."

    return message


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


def generate_recommendations(metrics: SystemMetrics) -> list[str]:
    """
    Генерирует рекомендации на основе метрик системы.

    Args:
        metrics: Метрики системы

    Returns:
        list[str]: Список рекомендаций
    """
    recommendations = []

    # Рекомендация для CPU > 90%
    if metrics.cpu_percent > 90.0:
        recommendations.append("Закройте тяжёлые приложения: Chrome, VS Code")

    # Рекомендация для RAM > 90%
    if metrics.ram_percent > 90.0:
        recommendations.append("Перезагрузите 1-2 тяжёлые программы")

    # Рекомендация для температуры > 80°C
    if metrics.temperature is not None and metrics.temperature > 80.0:
        recommendations.append("Нужно почистить кулер")

    return recommendations


def check_thresholds(metrics: SystemMetrics, thresholds: Thresholds) -> tuple[list[str], list[str]]:
    """
    Проверяет метрики на превышение порогов и генерирует рекомендации.

    Args:
        metrics: Метрики системы
        thresholds: Пороги для проверки

    Returns:
        tuple[list[str], list[str]]: (предупреждения, рекомендации)
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

    # Генерируем рекомендации
    recommendations = generate_recommendations(metrics)

    return warnings, recommendations

