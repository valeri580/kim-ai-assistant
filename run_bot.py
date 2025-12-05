"""Скрипт запуска Telegram-бота."""

import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Теперь импортируем и запускаем
if __name__ == "__main__":
    from kim_telegram.main import main
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nОстановка бота...")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise

