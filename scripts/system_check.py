"""Комплексная проверка работы системы «ИИ-ассистент Ким»."""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from kim_core.config import load_config
from kim_core.logging import init_logger, logger
from aiogram import Bot


async def check_config() -> bool:
    """Проверка конфигурации."""
    print("\n" + "=" * 60)
    print("1. ПРОВЕРКА КОНФИГУРАЦИИ")
    print("=" * 60)
    
    try:
        config = load_config()
        print("✓ Конфигурация загружена успешно")
        
        print(f"\n📋 Основные настройки:")
        print(f"   MODE: {config.mode}")
        print(f"   LOG_LEVEL: {config.log_level}")
        print(f"   TOKEN_BUDGET_DAILY: {config.token_budget_daily}")
        print(f"   LOCAL_ONLY: {config.local_only}")
        
        print(f"\n🔑 API ключи:")
        print(f"   OPENROUTER_API_KEY: {'✓ установлен' if config.openrouter_api_key else '✗ не установлен'}")
        print(f"   BOT_TOKEN: {'✓ установлен' if config.telegram_bot_token else '✗ не установлен'}")
        
        print(f"\n🤖 Модели LLM:")
        print(f"   MODEL_FAST: {config.model_fast}")
        print(f"   MODEL_SMART: {config.model_smart}")
        
        print(f"\n📊 Диагностика:")
        print(f"   CPU_WARN: {config.cpu_warn}%")
        print(f"   RAM_WARN: {config.ram_warn}%")
        print(f"   DISK_WARN: {config.disk_warn}%")
        print(f"   TEMP_WARN: {config.temp_warn if config.temp_warn else 'не задан'}")
        print(f"   ALERTS_CHAT_ID: {config.alerts_chat_id if config.alerts_chat_id else '✗ не задан'}")
        print(f"   DIAGNOSTICS_INTERVAL: {config.diagnostics_interval_seconds}с")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка загрузки конфигурации: {e}")
        return False


async def check_telegram_bot() -> bool:
    """Проверка Telegram бота."""
    print("\n" + "=" * 60)
    print("2. ПРОВЕРКА TELEGRAM БОТА")
    print("=" * 60)
    
    try:
        config = load_config()
        
        if not config.telegram_bot_token:
            print("⚠️  BOT_TOKEN не установлен - проверка пропущена")
            return False
        
        print("Подключение к Telegram API...")
        bot = Bot(token=config.telegram_bot_token)
        
        try:
            bot_info = await bot.get_me()
            print(f"✓ Бот подключён: @{bot_info.username} ({bot_info.first_name})")
            print(f"   ID бота: {bot_info.id}")
            
            # Проверяем, запущен ли бот
            print("\n🔍 Проверка запущенного процесса бота...")
            import psutil
            bot_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'run_bot.py' in cmdline or 'kim_telegram' in cmdline:
                        print(f"✓ Бот запущен (PID: {proc.info['pid']})")
                        bot_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if not bot_running:
                print("⚠️  Процесс бота не найден (бот может быть не запущен)")
            
            return True
        finally:
            await bot.session.close()
            
    except Exception as e:
        print(f"✗ Ошибка проверки бота: {e}")
        return False


async def check_openrouter() -> bool:
    """Проверка подключения к OpenRouter."""
    print("\n" + "=" * 60)
    print("3. ПРОВЕРКА OPENROUTER API")
    print("=" * 60)
    
    try:
        config = load_config()
        
        if not config.openrouter_api_key:
            print("⚠️  OPENROUTER_API_KEY не установлен - проверка пропущена")
            return False
        
        print(f"API ключ: {config.openrouter_api_key[:20]}...")
        print(f"Быстрая модель: {config.model_fast}")
        print(f"Умная модель: {config.model_smart}")
        
        # Можно добавить реальный тестовый запрос, но пока просто проверяем настройки
        print("✓ Настройки OpenRouter корректны")
        print("  (Для полной проверки запустите: python scripts/test_openrouter.py)")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка проверки OpenRouter: {e}")
        return False


def check_diagnostics() -> bool:
    """Проверка модуля диагностики."""
    print("\n" + "=" * 60)
    print("4. ПРОВЕРКА ДИАГНОСТИКИ СИСТЕМЫ")
    print("=" * 60)
    
    try:
        from kim_desktop.diagnostics.system_info import get_metrics, Thresholds, check_thresholds
        
        print("Сбор метрик системы...")
        metrics = get_metrics()
        
        print(f"✓ Метрики собраны:")
        print(f"   CPU: {metrics.cpu_percent:.1f}%")
        print(f"   RAM: {metrics.ram_percent:.1f}%")
        print(f"   Диск: {metrics.disk_percent:.1f}%")
        if metrics.temperature:
            print(f"   Температура: {metrics.temperature:.1f}°C")
        else:
            print(f"   Температура: недоступна")
        
        # Проверка порогов
        config = load_config()
        thresholds = Thresholds(
            cpu_warn=config.cpu_warn,
            ram_warn=config.ram_warn,
            disk_warn=config.disk_warn,
            temp_warn=config.temp_warn,
        )
        
        warnings = check_thresholds(metrics, thresholds)
        if warnings:
            print(f"\n⚠️  Обнаружены проблемы ({len(warnings)}):")
            for warning in warnings:
                print(f"   • {warning}")
        else:
            print("\n✓ Все метрики в пределах нормы")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка проверки диагностики: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies() -> bool:
    """Проверка установленных зависимостей."""
    print("\n" + "=" * 60)
    print("5. ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    print("=" * 60)
    
    required_modules = [
        ("aiogram", "Telegram Bot"),
        ("loguru", "Логирование"),
        ("psutil", "Диагностика системы"),
        ("dotenv", "Конфигурация"),
        ("httpx", "HTTP клиент"),
        ("vosk", "Распознавание речи"),
        ("pyttsx3", "Синтез речи"),
        ("sounddevice", "Работа с микрофоном"),
    ]
    
    all_ok = True
    for module_name, description in required_modules:
        try:
            __import__(module_name)
            print(f"✓ {description} ({module_name})")
        except ImportError:
            print(f"✗ {description} ({module_name}) - не установлен")
            all_ok = False
    
    return all_ok


def check_chat_id() -> bool:
    """Проверка настройки Chat ID."""
    print("\n" + "=" * 60)
    print("6. ПРОВЕРКА НАСТРОЙКИ ALERTS_CHAT_ID")
    print("=" * 60)
    
    try:
        config = load_config()
        
        if config.alerts_chat_id:
            print(f"✓ ALERTS_CHAT_ID установлен: {config.alerts_chat_id}")
            print("\n💡 Для проверки команды /myid:")
            print("   1. Отправьте боту команду /myid в Telegram")
            print("   2. Бот вернёт ваш Chat ID")
            print("   3. Убедитесь, что ID совпадает с настройкой")
            return True
        else:
            print("⚠️  ALERTS_CHAT_ID не установлен")
            print("\n💡 Как получить Chat ID:")
            print("   1. Запустите бота: python run_bot.py")
            print("   2. Отправьте боту команду: /myid")
            print("   3. Скопируйте полученный ID")
            print("   4. Добавьте в .env: ALERTS_CHAT_ID=ваш_id")
            return False
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False


async def main() -> None:
    """Главная функция проверки."""
    print("\n" + "=" * 60)
    print("🔍 КОМПЛЕКСНАЯ ПРОВЕРКА СИСТЕМЫ «ИИ-АССИСТЕНТ КИМ»")
    print("=" * 60)
    
    init_logger(load_config())
    
    results = {}
    
    # Проверки
    results["config"] = await check_config()
    results["dependencies"] = check_dependencies()
    results["telegram"] = await check_telegram_bot()
    results["openrouter"] = await check_openrouter()
    results["diagnostics"] = check_diagnostics()
    results["chat_id"] = check_chat_id()
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ПРОВЕРКИ")
    print("=" * 60)
    
    for check_name, result in results.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name.upper()}: {'OK' if result else 'ОШИБКА'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 Все проверки пройдены! Система готова к работе.")
    else:
        print("\n⚠️  Некоторые проверки не пройдены. Исправьте ошибки перед продолжением.")
    
    print("\n" + "=" * 60)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nПроверка прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

