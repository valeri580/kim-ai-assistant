"""Диагностика системы (CPU, RAM, диск, температура)."""

from kim_desktop.diagnostics.system_info import (
    SystemMetrics,
    Thresholds,
    check_thresholds,
    get_metrics,
)

__all__ = ["SystemMetrics", "Thresholds", "get_metrics", "check_thresholds"]

