# ShortsFactory — Progress & Migration Guide

## 1. Статус этапов разработки

| Этап | Описание | Статус |
|---|---|---|
| Stage 0 | Пользовательский тулчейн на Linux (`uv` 0.13.9, Python 3.12.16, Node.js v24.22.3, FFmpeg/FFprobe GPL) | Completed |
| Stage 1 | Каркас проекта, SQLite (`aiosqlite`), кроссплатформенные пути (`pathlib`), детектор GPU/NVENC, кириллические шрифты, `git init` | Completed |
| Stage 2 | Озвучка (`edge-tts` + `silenceremove` + `loudnorm`) и пословные субтитры (`faster-whisper` → `.ass`) | Completed |
| Stage 3 | Генератор карточки-хука (`Pillow`) и рендер FFmpeg (`h264_nvenc` / `libx264`) с auto-ducking музыки | Completed |
| Stage 4 | Сценарист (OpenAI-compatible LLM API + 24 офлайн-истории RU/EN) и AI Slideshow (`SDXL-Turbo` + Ken Burns) | Completed |
| Stage 5 | Последовательная очередь, FastAPI + WebSocket, React/Tailwind дашборд (`frontend/dist/`), `setup_windows.bat`, `start_windows.bat`, `start.sh` | Completed |
| Stage 6 | Сквозной End-to-End тест (2 полных ролика RU + EN), аудит `ffprobe` и визуальная проверка кадров | Completed |

---

## 2. Результаты сквозной проверки (Stage 6)

Полный набор тестов `pytest backend/tests -v -s` завершён со счётом **14/14 PASSED** (`341.03s`):
- Юнит-тесты кроссплатформенного экранирования путей (`PureWindowsPath` и относительные POSIX пути), БД и детектора железа (`5/5`).
- Тесты TTS + `silenceremove` + `faster-whisper` + `.ass` на русском и английском языках (`2/2`).
- Тест Pillow hook card + FFmpeg `libass` со шрифтом `Montserrat` + рендер MP4 (`1/1`).
- Тесты банка из 24 сценариев, парсера LLM и Ken Burns слайд-шоу (`3/3`).
- Тесты REST API (маскировка ключа, загрузка/удаление ассетов) (`2/2`).
- Сквозной E2E-тест против живого сервера `uvicorn` + WebSocket `/ws/progress` (`1/1`):

| Файл | Режим / Язык | `ffprobe` Параметры | Длительность | Размер |
|---|---|---|---|---|
| `output/2026-11-19/video_01.mp4` (+ `.txt`) | `reddit` · RU · `gameplay` (процедурный фон) | `1080×1920`, `60/1` fps, `h264` (`yuv420p`), `aac` `48000 Hz` | `44.00s` | `12,380,413 B` (~11.8 MiB) |
| `output/2026-11-19/video_02.mp4` (+ `.txt`) | `scary` · EN · `ai_slideshow` (CPU арт + Ken Burns) | `1080×1920`, `60/1` fps, `h264` (`yuv420p`), `aac` `48000 Hz` | `40.87s` | `4,269,291 B` (~4.1 MiB) |

---

## 3. Подробная инструкция: перенос с Linux на Windows 10/11 (NVIDIA RTX 3060 12GB)

### Шаг 1. Копирование проекта с Linux на Windows
Скопируйте папку проекта `shorts-factory` на Windows (например, в `D:\Projects\shorts-factory` или через `git clone`).
- **Можно НЕ переносить** (пересоздадутся/не нужны на Windows):
  - `.venv/` (виртуальное окружение Linux не работает на Windows)
  - `frontend/node_modules/` (если есть папка `frontend/dist/`, Node.js на Windows вообще не потребуется!)
  - `temp/` и `data/shorts_factory.db`
- **Обязательно сохранить при переносе:**
  - `assets/fonts/` (`Montserrat-ExtraBold.ttf`, `Montserrat-SemiBold.ttf`)
  - `assets/music/` (`ambient_pulse.mp3` и ваша музыка)
  - `frontend/dist/` (готовая сборка React UI, раздаётся FastAPI)
  - `setup_windows.bat`, `start_windows.bat`, `requirements.txt`, `requirements-gpu.txt`

### Шаг 2. Предварительная установка на Windows 10/11
1. **Python 3.12 (x64)** (или 3.11):
   - Скачайте с [python.org](https://www.python.org/downloads/) и обязательно поставьте галочку **"Add Python to PATH"** и **Python Launcher (`py`)**.
2. **FFmpeg (с поддержкой NVENC и libass):**
   - Откройте PowerShell или CMD и выполните:
     ```bat
     winget install -e --id Gyan.FFmpeg
     ```
   - Перезапустите терминал и проверьте: `ffmpeg -version` и `ffprobe -version`.
3. **Драйвер NVIDIA:**
   - Убедитесь, что установлен актуальный драйвер Game Ready / Studio для RTX 3060 (поддержка CUDA 12.1 / 12.4).

### Шаг 3. Первичная настройка в 1 клик (`setup_windows.bat`)
Откройте папку проекта и запустите двойным кликом **`setup_windows.bat`** (или из CMD внутри папки проекта).
Скрипт автоматически:
1. Создаст `.venv` на базе Python 3.12/3.11.
2. Установит PyTorch + torchvision с поддержкой **CUDA 12.4** (с автоматическим фолбэком на CUDA 12.1).
3. Установит основные зависимости из `requirements.txt` и GPU-зависимости из `requirements-gpu.txt` (`diffusers`, `transformers`, `accelerate`, `safetensors`).
4. Проверит наличие шрифтов в `assets/fonts/` и дефолтной музыки.
5. Запустит `python -m backend.core.hardware` — убедитесь, что в выводе:
   - `"cuda_available": true`
   - `"gpu_name": "NVIDIA GeForce RTX 3060"`
   - `"nvenc_available": true`
   - `"video_encoder": "h264_nvenc"`
   - `"whisper_device": "cuda"` и `"whisper_compute_type": "float16"`

### Шаг 4. Запуск студии (`start_windows.bat`)
1. Запустите **`start_windows.bat`**.
2. Скрипт установит `PYTHONUTF8=1`, поднимет FastAPI + воркер очередей на `http://127.0.0.1:8000` и автоматически откроет веб-интерфейс в браузере (второй терминал для фронтенда не нужен).

### Шаг 5. Рекомендованная настройка после запуска
1. Перейдите во вкладку **«Ассеты и настройки»**:
   - Загрузите свои вертикальные или горизонтальные геймплей-ролики (Minecraft паркур, GTA 5, залипательные видео) в `/assets/backgrounds` (система сама обрежет их в 9:16 и выберет случайный фрагмент).
   - При желании добавьте фоновые треки в `/assets/music` (автоприглушение под голосом уже настроено).
   - Введите API-ключ от **OpenRouter / DeepSeek / OpenAI** (если хотите бесконечную генерацию новых сценариев нейросетью; без ключа работает встроенная база из 24 готовых историй).
2. Во вкладке **«Генератор пачек»**:
   - В режиме **AI Slideshow + Ken Burns** на RTX 3060 12GB автоматически задействуется `stabilityai/sdxl-turbo` (при первом запуске модель скачается с HuggingFace в кэш, а `QueueManager` автоматически выгружает `faster-whisper` из VRAM перед запуском `diffusers`).
   - Готовые ролики и текстовые файлы с описанием/тегами сохраняются в `output\YYYY-MM-DD\video_XX.mp4` и `video_XX.txt`.
