# План улучшений качества распознавания речи

## Файлы для изменения

### 1. `/src/kim_voice/stt/speech_to_text.py`
- ✅ Фильтры по длине и уверенности уже есть
- ➕ Добавить опциональный WebRTC VAD (OptionalVAD класс)
- ➕ Добавить поля use_vad и vad_aggressiveness в STTConfig
- ➕ Интегрировать VAD в listen_once()
- ➕ Изменить возвращаемое значение listen_once() для возврата (text, avg_conf) или пары

### 2. `/src/kim_voice/hotword/kim_hotword.py`
- ➕ Добавить поля в HotwordConfig:
  - adaptive_threshold: bool = True
  - noise_floor_window: int = 100
  - min_confidence_floor: float = 0.5
  - max_confidence_floor: float = 0.9
- ➕ Добавить буфер шума в __init__:
  - self._noise_amplitudes: list[float] = []
  - self._dynamic_conf_threshold: float = ...
- ➕ Реализовать адаптивный порог в listen()
- ➕ Добавить опциональный VAD для hotword

### 3. `/src/kim_voice/main.py`
- ➕ Изменить логику подтверждения:
  - CONFIRMATION_CONF_THRESHOLD = 0.75
  - CONFIRMATION_LENGTH_THRESHOLD = 25
  - Условное подтверждение только при низкой уверенности или длинной фразе
  - Возврат avg_conf из STT для проверки

### 4. `/src/kim_core/config/settings.py`
- ➕ Добавить поля в AppConfig:
  - mic_device_index: Optional[int] = None
  - mic_sample_rate: int = 16000
  - mic_chunk_size: int = 4000
- ➕ Загрузить из переменных окружения в load_config()

### 5. `.env.example`
- ➕ Добавить переменные:
  - MIC_DEVICE_INDEX=
  - MIC_SAMPLE_RATE=16000
  - MIC_CHUNK_SIZE=4000
  - STT_USE_VAD=0
  - STT_VAD_AGGRESSIVENESS=2
  - HOTWORD_ADAPTIVE_THRESHOLD=1

### 6. `requirements.txt`
- ➕ Добавить: webrtcvad  # опционально, для улучшения качества распознавания

### 7. `README.md`
- ➕ Добавить раздел "Настройка качества распознавания речи"

