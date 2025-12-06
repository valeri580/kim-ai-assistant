"""Диагностика системы (CPU, RAM, диск, температура)."""

from kim_desktop.diagnostics.system_info import (
    SystemMetrics,
    Thresholds,
    check_thresholds,
    format_telegram_message,
    format_voice_message,
    generate_recommendations,
    get_metrics,
)

__all__ = [
    "SystemMetrics",
    "Thresholds",
    "get_metrics",
    "check_thresholds",
    "generate_recommendations",
    "format_telegram_message",
    "format_voice_message",
]

