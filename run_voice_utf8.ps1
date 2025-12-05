# Скрипт запуска голосового ассистента с правильной кодировкой UTF-8 для Windows PowerShell

# Устанавливаем кодировку UTF-8 для PowerShell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# Запускаем ассистента
python run_voice.py

