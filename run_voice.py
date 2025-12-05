"""Скрипт запуска голосового ассистента."""

import sys
import os
from pathlib import Path

# Настройка кодировки для Windows ПЕРЕД любыми импортами
if sys.platform == "win32":
    # Устанавливаем переменную окружения для UTF-8
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # Устанавливаем кодировку консоли на UTF-8
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass
    
    # Переопределяем stdout и stderr с UTF-8 кодировкой
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# Добавляем src в путь
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Теперь импортируем и запускаем
if __name__ == "__main__":
    from kim_voice.main import main
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nОстановка голосового ассистента...")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise

