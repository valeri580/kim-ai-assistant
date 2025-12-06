"""Тесты для модуля диагностики системы."""

import pytest
from unittest.mock import MagicMock, patch

from kim_desktop.diagnostics.system_info import (
    SystemMetrics,
    Thresholds,
    check_thresholds,
    get_metrics,
)


def test_check_thresholds_no_warnings():
    """Тест: при нормальных значениях предупреждений нет."""
    metrics = SystemMetrics(
        cpu_percent=50.0,
        ram_percent=60.0,
        disk_percent=70.0,
        temperature=None,
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=None,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 0
    assert len(recommendations) == 0


def test_check_thresholds_cpu_warning():
    """Тест: при высоком CPU генерируется предупреждение."""
    metrics = SystemMetrics(
        cpu_percent=90.0,  # Выше порога 85%
        ram_percent=60.0,
        disk_percent=70.0,
        temperature=None,
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=None,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 1
    assert "CPU" in warnings[0]
    assert "90.0%" in warnings[0]
    # CPU > 90%, должна быть рекомендация
    assert len(recommendations) == 1
    assert "Chrome" in recommendations[0] or "VS Code" in recommendations[0]


def test_check_thresholds_ram_warning():
    """Тест: при высоком использовании RAM генерируется предупреждение."""
    metrics = SystemMetrics(
        cpu_percent=50.0,
        ram_percent=95.0,  # Выше порога 90%
        disk_percent=70.0,
        temperature=None,
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=None,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 1
    assert "RAM" in warnings[0] or "память" in warnings[0]
    assert "95.0%" in warnings[0]
    # RAM > 90%, должна быть рекомендация
    assert len(recommendations) == 1
    assert "перезагрузите" in recommendations[0].lower() or "программы" in recommendations[0].lower()


def test_check_thresholds_disk_warning():
    """Тест: при высоком использовании диска генерируется предупреждение."""
    metrics = SystemMetrics(
        cpu_percent=50.0,
        ram_percent=60.0,
        disk_percent=95.0,  # Выше порога 90%
        temperature=None,
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=None,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 1
    assert "диск" in warnings[0].lower() or "disk" in warnings[0].lower()
    assert "95.0%" in warnings[0]
    # Диск > 90%, но нет рекомендации (рекомендации только для CPU > 90%, RAM > 90%, temp > 80°C)
    assert len(recommendations) == 0


def test_check_thresholds_temperature_warning():
    """Тест: при высокой температуре генерируется предупреждение."""
    metrics = SystemMetrics(
        cpu_percent=50.0,
        ram_percent=60.0,
        disk_percent=70.0,
        temperature=85.0,  # Выше порога 80°
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=80.0,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 1
    assert "температура" in warnings[0].lower() or "temperature" in warnings[0].lower()
    assert "85.0" in warnings[0]
    # Температура > 80°C, должна быть рекомендация
    assert len(recommendations) == 1
    assert "кулер" in recommendations[0].lower()


def test_check_thresholds_multiple_warnings():
    """Тест: при превышении нескольких порогов генерируются все предупреждения."""
    metrics = SystemMetrics(
        cpu_percent=90.0,  # Выше порога
        ram_percent=95.0,  # Выше порога
        disk_percent=92.0,  # Выше порога
        temperature=None,
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=None,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 3
    # CPU > 90% и RAM > 90%, должны быть рекомендации
    assert len(recommendations) >= 2


def test_check_thresholds_temperature_ignored_when_not_set():
    """Тест: температура игнорируется, если порог не задан."""
    metrics = SystemMetrics(
        cpu_percent=50.0,
        ram_percent=60.0,
        disk_percent=70.0,
        temperature=100.0,  # Очень высокая, но порог не задан
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=None,  # Порог не задан
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 0
    assert len(recommendations) == 0


def test_check_thresholds_temperature_ignored_when_metrics_none():
    """Тест: температура игнорируется, если метрика не доступна."""
    metrics = SystemMetrics(
        cpu_percent=50.0,
        ram_percent=60.0,
        disk_percent=70.0,
        temperature=None,  # Температура не доступна
    )
    
    thresholds = Thresholds(
        cpu_warn=85.0,
        ram_warn=90.0,
        disk_warn=90.0,
        temp_warn=80.0,
    )
    
    warnings, recommendations = check_thresholds(metrics, thresholds)
    
    assert len(warnings) == 0
    assert len(recommendations) == 0


@patch('kim_desktop.diagnostics.system_info.psutil')
def test_get_metrics_returns_system_metrics(mock_psutil):
    """Тест: get_metrics возвращает объект SystemMetrics."""
    # Настраиваем моки psutil
    mock_psutil.cpu_percent.return_value = 45.5
    mock_psutil.virtual_memory.return_value = MagicMock(percent=65.0, used=8*1024**3, total=16*1024**3)
    mock_psutil.disk_usage.return_value = MagicMock(percent=75.0, used=150*1024**3, total=200*1024**3)
    mock_psutil.sensors_temperatures.return_value = {}
    
    metrics = get_metrics()
    
    assert isinstance(metrics, SystemMetrics)
    assert metrics.cpu_percent == 45.5
    assert metrics.ram_percent == 65.0
    assert metrics.disk_percent == 75.0

