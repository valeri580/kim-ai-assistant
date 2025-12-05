"""Быстрая проверка моделей из конфигурации."""

import os
import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv

load_dotenv()

print("\n" + "=" * 60)
print("Проверка моделей из конфигурации")
print("=" * 60)

model_fast = os.getenv("MODEL_FAST", "openai/gpt-3.5-turbo")
model_smart = os.getenv("MODEL_SMART", "openai/gpt-4-turbo")

print(f"\nMODEL_FAST (из .env): {model_fast}")
print(f"MODEL_SMART (из .env): {model_smart}")

# Проверка на проблемные значения
if "openrouter/fast" in model_fast or "openrouter/smart" in model_smart:
    print("\n⚠️  ВНИМАНИЕ: Обнаружены неправильные ID моделей!")
    print("   Используйте реальные ID моделей, например:")
    print("   - openai/gpt-3.5-turbo")
    print("   - openai/gpt-4-turbo")
    print("   - anthropic/claude-3-haiku")
    print("\n   Полный список моделей: https://openrouter.ai/models")
else:
    print("\n✓ Модели выглядят корректно")

print("\n" + "=" * 60)

