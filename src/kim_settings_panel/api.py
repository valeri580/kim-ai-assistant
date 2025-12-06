"""FastAPI приложение для панели настроек."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from kim_core.logging import logger

from kim_settings_panel.models import PROFILES, SCENARIOS, RuntimeSettingsUpdate
from kim_settings_panel.store import SettingsStore

# Инициализация приложения
app = FastAPI(title="Kim Settings Panel", version="1.0.0")

# Путь к файлу настроек
SETTINGS_PATH = os.getenv("RUNTIME_SETTINGS_PATH", "data/runtime_settings.json")

# Создаём хранилище
store = SettingsStore(SETTINGS_PATH)


@app.get("/api/settings", response_model=dict)
async def get_settings() -> dict:
    """
    Возвращает текущие runtime-настройки.

    Returns:
        dict: Текущие настройки в формате JSON
    """
    try:
        settings = store.load()
        try:
            return settings.model_dump(exclude_none=True)
        except AttributeError:
            # Fallback для Pydantic v1
            return settings.dict(exclude_none=True)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/settings", response_model=dict)
async def update_settings(patch: RuntimeSettingsUpdate) -> dict:
    """
    Обновляет runtime-настройки.

    Если в patch указан profile, сначала применяется профиль,
    затем накладываются остальные поля.

    Args:
        patch: Частичное обновление настроек

    Returns:
        dict: Обновлённые настройки
    """
    try:
        updated = store.update(patch)
        try:
            return updated.model_dump(exclude_none=True)
        except AttributeError:
            # Fallback для Pydantic v1
            return updated.dict(exclude_none=True)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/profiles", response_model=list)
async def get_profiles() -> list:
    """
    Возвращает список доступных профилей.

    Returns:
        list: Список профилей с описаниями
    """
    return [
        {"id": "quality", "label": "Максимальное качество", "description": "Максимум качества, более 'умные' модели, выше лимиты"},
        {"id": "balanced", "label": "Сбалансированный", "description": "Компромисс между качеством и производительностью"},
        {"id": "performance", "label": "Максимальная производительность", "description": "Упор на минимальный расход токенов и скорость"},
    ]


@app.get("/api/scenarios", response_model=list)
async def get_scenarios() -> list:
    """
    Возвращает список доступных сценариев.

    Returns:
        list: Список сценариев с описаниями
    """
    return [
        {
            "id": scenario_id,
            "label": scenario_data["label"],
            "description": scenario_data["description"],
        }
        for scenario_id, scenario_data in SCENARIOS.items()
    ]


@app.post("/api/scenarios/{scenario_id}", response_model=dict)
async def apply_scenario(scenario_id: str) -> dict:
    """
    Применяет готовый сценарий.

    Args:
        scenario_id: Идентификатор сценария

    Returns:
        dict: Обновлённые настройки

    Raises:
        HTTPException: Если сценарий не найден или произошла ошибка
    """
    try:
        updated = store.apply_scenario(scenario_id)
        try:
            return updated.model_dump(exclude_none=True)
        except AttributeError:
            # Fallback для Pydantic v1
            return updated.dict(exclude_none=True)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error applying scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/", response_class=HTMLResponse)
async def settings_panel() -> str:
    """Возвращает HTML-страницу панели настроек."""
    html_content = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройки ассистента Ким</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .form-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #555;
        }
        select, input[type="text"], input[type="number"], input[type="checkbox"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        input[type="checkbox"] {
            width: auto;
        }
        button {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background: #45a049;
        }
        .scenario-button {
            background: #2196F3;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin: 5px;
            width: calc(100% - 10px);
            text-align: left;
        }
        .scenario-button:hover {
            background: #1976D2;
        }
        .scenario-description {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.9);
            margin-top: 4px;
        }
        .status {
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <h1>⚙️ Настройки ассистента Ким</h1>

    <div class="section">
        <h2>Готовые сценарии</h2>
        <p style="font-size: 14px; color: #666; margin-bottom: 15px;">
            Выберите готовый сценарий для быстрой настройки. После выбора сценария все параметры можно дополнительно настроить вручную.
        </p>
        <div id="scenarios-container"></div>
    </div>

    <div class="section">
        <h2>Профиль настроек</h2>
        <div class="form-group">
            <label for="profile">Профиль:</label>
            <select id="profile">
                <option value="">Custom (без профиля)</option>
            </select>
            <p style="font-size: 12px; color: #666; margin-top: 5px;">
                При выборе профиля некоторые параметры автоматически изменятся.
                После выбора профиля их можно дополнительно настроить вручную.
            </p>
        </div>
    </div>

    <div class="section">
        <h2>Основные настройки</h2>
        <div class="form-group">
            <label for="mode">Режим работы:</label>
            <select id="mode">
                <option value="">Custom (без режима)</option>
                <option value="voice_assistant">Голосовой ассистент</option>
                <option value="telegram_only">Только Telegram</option>
                <option value="offline">Офлайн</option>
            </select>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" id="local_only">
                Режим только локально (без LLM)
            </label>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" id="enable_voice_assistant">
                Включить голосовой ассистент
            </label>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" id="enable_web_search">
                Включить веб-поиск
            </label>
        </div>
    </div>

    <div class="section">
        <h2>Настройки голоса (TTS)</h2>
        <div class="form-group">
            <label for="tts_rate">Скорость речи (-10 до 10):</label>
            <input type="number" id="tts_rate" min="-10" max="10" step="1">
        </div>
        <div class="form-group">
            <label for="tts_volume">Громкость (0-100):</label>
            <input type="number" id="tts_volume" min="0" max="100" step="1">
        </div>
    </div>

    <div class="section">
        <h2>Настройки LLM</h2>
        <div class="form-group">
            <label for="model_fast">Быстрая модель:</label>
            <input type="text" id="model_fast" placeholder="например: openai/gpt-3.5-turbo">
        </div>
        <div class="form-group">
            <label for="model_smart">Умная модель:</label>
            <input type="text" id="model_smart" placeholder="например: openai/gpt-4-turbo">
        </div>
        <div class="form-group">
            <label for="token_budget_daily">Дневной лимит токенов:</label>
            <input type="number" id="token_budget_daily" min="0" step="1000">
        </div>
    </div>

    <div class="section">
        <h2>Настройки Telegram</h2>
        <div class="form-group">
            <label for="voice_telegram_chat_id">Chat ID для голосовых отправок:</label>
            <input type="number" id="voice_telegram_chat_id" placeholder="например: 123456789">
        </div>
    </div>

    <div class="section">
        <h2>Пороги диагностики ПК</h2>
        <p style="font-size: 14px; color: #666; margin-bottom: 15px;">
            Настройте пороги для уведомлений о проблемах с ресурсами системы. 
            При превышении порога будет отправлено уведомление в Telegram.
        </p>
        <div class="form-group">
            <label for="cpu_warn">Порог загрузки CPU (%):</label>
            <input type="number" id="cpu_warn" min="0" max="100" step="0.1" placeholder="например: 85.0">
            <p style="font-size: 12px; color: #666; margin-top: 5px;">
                Предупреждение при загрузке CPU выше указанного значения
            </p>
        </div>
        <div class="form-group">
            <label for="ram_warn">Порог использования RAM (%):</label>
            <input type="number" id="ram_warn" min="0" max="100" step="0.1" placeholder="например: 90.0">
            <p style="font-size: 12px; color: #666; margin-top: 5px;">
                Предупреждение при использовании RAM выше указанного значения
            </p>
        </div>
        <div class="form-group">
            <label for="disk_warn">Порог использования диска (%):</label>
            <input type="number" id="disk_warn" min="0" max="100" step="0.1" placeholder="например: 90.0">
            <p style="font-size: 12px; color: #666; margin-top: 5px;">
                Предупреждение при использовании диска выше указанного значения
            </p>
        </div>
        <div class="form-group">
            <label for="temp_warn">Порог температуры (°C):</label>
            <input type="number" id="temp_warn" min="0" step="0.1" placeholder="например: 80.0 (необязательно)">
            <p style="font-size: 12px; color: #666; margin-top: 5px;">
                Предупреждение при температуре выше указанного значения. Оставьте пустым, чтобы отключить проверку температуры.
            </p>
        </div>
    </div>

    <button onclick="saveSettings()">💾 Сохранить настройки</button>

    <div id="status" class="status"></div>

    <script>
        let profiles = [];

        // Загружаем список профилей
        async function loadProfiles() {
            try {
                const response = await fetch('/api/profiles');
                profiles = await response.json();
                
                const select = document.getElementById('profile');
                profiles.forEach(profile => {
                    const option = document.createElement('option');
                    option.value = profile.id;
                    option.textContent = profile.label;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading profiles:', error);
            }
        }

        // Загружаем текущие настройки
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                const settings = await response.json();

                // Заполняем форму
                if (settings.mode) {
                    document.getElementById('mode').value = settings.mode;
                }
                if (settings.profile) {
                    document.getElementById('profile').value = settings.profile;
                }
                document.getElementById('local_only').checked = settings.local_only === true;
                if (settings.enable_voice_assistant !== undefined) {
                    document.getElementById('enable_voice_assistant').checked = settings.enable_voice_assistant === true;
                }
                if (settings.enable_web_search !== undefined) {
                    document.getElementById('enable_web_search').checked = settings.enable_web_search === true;
                }
                if (settings.tts_rate !== undefined) {
                    document.getElementById('tts_rate').value = settings.tts_rate;
                }
                if (settings.tts_volume !== undefined) {
                    document.getElementById('tts_volume').value = settings.tts_volume;
                }
                if (settings.model_fast) {
                    document.getElementById('model_fast').value = settings.model_fast;
                }
                if (settings.model_smart) {
                    document.getElementById('model_smart').value = settings.model_smart;
                }
                if (settings.token_budget_daily !== undefined) {
                    document.getElementById('token_budget_daily').value = settings.token_budget_daily;
                }
                if (settings.voice_telegram_chat_id !== undefined) {
                    document.getElementById('voice_telegram_chat_id').value = settings.voice_telegram_chat_id;
                }
                if (settings.cpu_warn !== undefined) {
                    document.getElementById('cpu_warn').value = settings.cpu_warn;
                }
                if (settings.ram_warn !== undefined) {
                    document.getElementById('ram_warn').value = settings.ram_warn;
                }
                if (settings.disk_warn !== undefined) {
                    document.getElementById('disk_warn').value = settings.disk_warn;
                }
                if (settings.temp_warn !== undefined) {
                    document.getElementById('temp_warn').value = settings.temp_warn;
                }
            } catch (error) {
                showStatus('Ошибка загрузки настроек: ' + error.message, 'error');
            }
        }

        // Обработчик смены профиля
        document.getElementById('profile').addEventListener('change', async function() {
            const profile = this.value;
            if (profile) {
                try {
                    const response = await fetch('/api/settings', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({profile: profile})
                    });
                    const updated = await response.json();
                    
                    // Обновляем поля формы
                    document.getElementById('local_only').checked = updated.local_only === true;
                    if (updated.tts_rate !== undefined) {
                        document.getElementById('tts_rate').value = updated.tts_rate;
                    }
                    if (updated.tts_volume !== undefined) {
                        document.getElementById('tts_volume').value = updated.tts_volume;
                    }
                    if (updated.model_fast) {
                        document.getElementById('model_fast').value = updated.model_fast;
                    }
                    if (updated.model_smart) {
                        document.getElementById('model_smart').value = updated.model_smart;
                    }
                    if (updated.token_budget_daily !== undefined) {
                        document.getElementById('token_budget_daily').value = updated.token_budget_daily;
                    }
                    
                    showStatus('Профиль применён', 'success');
                } catch (error) {
                    showStatus('Ошибка применения профиля: ' + error.message, 'error');
                }
            }
        });

        // Сохранение настроек
        async function saveSettings() {
            const patch = {
                local_only: document.getElementById('local_only').checked,
            };

            const mode = document.getElementById('mode').value;
            if (mode) {
                patch.mode = mode;
            }

            patch.enable_voice_assistant = document.getElementById('enable_voice_assistant').checked;
            patch.enable_web_search = document.getElementById('enable_web_search').checked;

            const ttsRate = document.getElementById('tts_rate').value;
            if (ttsRate) {
                patch.tts_rate = parseInt(ttsRate);
            }

            const ttsVolume = document.getElementById('tts_volume').value;
            if (ttsVolume) {
                patch.tts_volume = parseInt(ttsVolume);
            }

            const modelFast = document.getElementById('model_fast').value.trim();
            if (modelFast) {
                patch.model_fast = modelFast;
            }

            const modelSmart = document.getElementById('model_smart').value.trim();
            if (modelSmart) {
                patch.model_smart = modelSmart;
            }

            const tokenBudget = document.getElementById('token_budget_daily').value;
            if (tokenBudget) {
                patch.token_budget_daily = parseInt(tokenBudget);
            }

            const chatId = document.getElementById('voice_telegram_chat_id').value;
            if (chatId) {
                patch.voice_telegram_chat_id = parseInt(chatId);
            }

            const cpuWarn = document.getElementById('cpu_warn').value;
            if (cpuWarn) {
                patch.cpu_warn = parseFloat(cpuWarn);
            }

            const ramWarn = document.getElementById('ram_warn').value;
            if (ramWarn) {
                patch.ram_warn = parseFloat(ramWarn);
            }

            const diskWarn = document.getElementById('disk_warn').value;
            if (diskWarn) {
                patch.disk_warn = parseFloat(diskWarn);
            }

            const tempWarn = document.getElementById('temp_warn').value;
            if (tempWarn) {
                patch.temp_warn = parseFloat(tempWarn);
            }

            const profile = document.getElementById('profile').value;
            if (profile) {
                patch.profile = profile;
            }

            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(patch)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка сохранения');
                }

                showStatus('Настройки сохранены успешно', 'success');
            } catch (error) {
                showStatus('Ошибка сохранения: ' + error.message, 'error');
            }
        }

        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
            setTimeout(() => {
                status.style.display = 'none';
            }, 3000);
        }

        // Загружаем список сценариев
        async function loadScenarios() {
            try {
                const response = await fetch('/api/scenarios');
                const scenarios = await response.json();
                
                const container = document.getElementById('scenarios-container');
                scenarios.forEach(scenario => {
                    const button = document.createElement('button');
                    button.className = 'scenario-button';
                    button.innerHTML = `
                        <strong>${scenario.label}</strong>
                        <div class="scenario-description">${scenario.description}</div>
                    `;
                    button.onclick = () => applyScenario(scenario.id, scenario.label);
                    container.appendChild(button);
                });
            } catch (error) {
                console.error('Error loading scenarios:', error);
            }
        }

        // Применение сценария
        async function applyScenario(scenarioId, scenarioLabel) {
            try {
                const response = await fetch(`/api/scenarios/${scenarioId}`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка применения сценария');
                }

                const updated = await response.json();
                
                // Обновляем все поля формы моментально
                // Режим и профиль
                const modeSelect = document.getElementById('mode');
                if (modeSelect && updated.mode) {
                    modeSelect.value = updated.mode;
                }
                if (updated.profile) {
                    document.getElementById('profile').value = updated.profile;
                }
                
                // Основные настройки режима
                const localOnlyCheckbox = document.getElementById('local_only');
                if (localOnlyCheckbox && updated.local_only !== undefined) {
                    localOnlyCheckbox.checked = updated.local_only === true;
                }
                
                const voiceCheckbox = document.getElementById('enable_voice_assistant');
                if (voiceCheckbox && updated.enable_voice_assistant !== undefined) {
                    voiceCheckbox.checked = updated.enable_voice_assistant === true;
                }
                
                const webSearchCheckbox = document.getElementById('enable_web_search');
                if (webSearchCheckbox && updated.enable_web_search !== undefined) {
                    webSearchCheckbox.checked = updated.enable_web_search === true;
                }
                
                // Настройки TTS
                if (updated.tts_rate !== undefined) {
                    document.getElementById('tts_rate').value = updated.tts_rate;
                }
                if (updated.tts_volume !== undefined) {
                    document.getElementById('tts_volume').value = updated.tts_volume;
                }
                
                // Модели LLM (могут быть очищены для offline режима)
                const modelFastInput = document.getElementById('model_fast');
                if (modelFastInput) {
                    modelFastInput.value = updated.model_fast || '';
                }
                const modelSmartInput = document.getElementById('model_smart');
                if (modelSmartInput) {
                    modelSmartInput.value = updated.model_smart || '';
                }
                
                // Лимит токенов (может быть очищен для offline режима)
                const tokenBudgetInput = document.getElementById('token_budget_daily');
                if (tokenBudgetInput) {
                    tokenBudgetInput.value = updated.token_budget_daily !== undefined ? updated.token_budget_daily : '';
                }
                
                // Остальные поля
                if (updated.voice_telegram_chat_id !== undefined) {
                    document.getElementById('voice_telegram_chat_id').value = updated.voice_telegram_chat_id || '';
                }
                if (updated.cpu_warn !== undefined) {
                    document.getElementById('cpu_warn').value = updated.cpu_warn;
                }
                if (updated.ram_warn !== undefined) {
                    document.getElementById('ram_warn').value = updated.ram_warn;
                }
                if (updated.disk_warn !== undefined) {
                    document.getElementById('disk_warn').value = updated.disk_warn;
                }
                if (updated.temp_warn !== undefined) {
                    document.getElementById('temp_warn').value = updated.temp_warn || '';
                }
                
                showStatus(`Сценарий '${scenarioLabel}' применён`, 'success');
            } catch (error) {
                showStatus('Ошибка применения сценария: ' + error.message, 'error');
            }
        }

        // Инициализация при загрузке страницы
        window.addEventListener('DOMContentLoaded', async () => {
            await loadScenarios();
            await loadProfiles();
            await loadSettings();
        });
    </script>
</body>
</html>
    """
    return html_content


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SETTINGS_PANEL_PORT", "8000"))
    logger.info(f"Starting settings panel on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

