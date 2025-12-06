"""Скрипт для сохранения секретов в keyring."""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kim_core.secret_store import set_secret, get_secret


def main():
    """Интерактивный скрипт для сохранения секретов."""
    print("=" * 60)
    print("Сохранение секретов для Ким-ассистента")
    print("=" * 60)
    print()

    # Проверяем текущие значения
    current_api_key = get_secret("openrouter_api_key")
    current_bot_token = get_secret("telegram_bot_token")

    if current_api_key:
        print(f"✓ OpenRouter API Key уже сохранён (первые 10 символов: {current_api_key[:10]}...)")
        overwrite = input("Перезаписать? (y/N): ").strip().lower()
        if overwrite != "y":
            print("Пропускаем OpenRouter API Key")
        else:
            api_key = input("Введите OpenRouter API Key: ").strip()
            if api_key:
                try:
                    set_secret("openrouter_api_key", api_key)
                    print("✓ OpenRouter API Key сохранён")
                except Exception as e:
                    print(f"✗ Ошибка сохранения: {e}")
                    return
    else:
        api_key = input("Введите OpenRouter API Key (или Enter для пропуска): ").strip()
        if api_key:
            try:
                set_secret("openrouter_api_key", api_key)
                print("✓ OpenRouter API Key сохранён")
            except Exception as e:
                print(f"✗ Ошибка сохранения: {e}")
                return

    print()

    if current_bot_token:
        print(f"✓ Telegram Bot Token уже сохранён (первые 10 символов: {current_bot_token[:10]}...)")
        overwrite = input("Перезаписать? (y/N): ").strip().lower()
        if overwrite != "y":
            print("Пропускаем Telegram Bot Token")
        else:
            bot_token = input("Введите Telegram Bot Token: ").strip()
            if bot_token:
                try:
                    set_secret("telegram_bot_token", bot_token)
                    print("✓ Telegram Bot Token сохранён")
                except Exception as e:
                    print(f"✗ Ошибка сохранения: {e}")
                    return
    else:
        bot_token = input("Введите Telegram Bot Token (или Enter для пропуска): ").strip()
        if bot_token:
            try:
                set_secret("telegram_bot_token", bot_token)
                print("✓ Telegram Bot Token сохранён")
            except Exception as e:
                print(f"✗ Ошибка сохранения: {e}")
                return

    print()
    print("=" * 60)
    print("Готово! Секреты сохранены в Windows Credential Manager.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        sys.exit(1)

