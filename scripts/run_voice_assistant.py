"""Скрипт запуска голосового ассистента."""

import sys
from pathlib import Path

# Добавляем src в путь для корректных импортов
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kim_voice.main import main as voice_main


def main() -> None:
    """Запуск голосового ассистента."""
    try:
        voice_main()
    except KeyboardInterrupt:
        print("\nОстановка голосового ассистента...")
    except Exception as e:
        print(f"\n❌ Голосовой ассистент не смог запуститься: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

