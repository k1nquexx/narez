# ShortsFactory

Автономная локальная студия пакетной генерации вертикальных роликов **9:16 (1080×1920, 60fps)** для YouTube Shorts и TikTok в жанрах:
- Истории с Reddit (`reddit`)
- Страшные истории (`scary`)
- Психологические факты (`psychology`)
- Мотивация (`motivation`)

## Возможности
- **Генератор сценариев:** OpenAI-compatible клиент (OpenRouter / DeepSeek / OpenAI / Ollama) + встроенный офлайн-банк из 24 готовых историй (RU и EN) для работы без API-ключа.
- **Озвучка и темп речи:** `edge-tts` (бесплатно, RU/EN голоса, ускорение `+15%`) + опциональный локальный `Silero TTS` (PyTorch) + автоматическое удаление пауз (`silenceremove`) и нормализация громкости (`loudnorm`).
- **Субтитры с пословной анимацией:** `faster-whisper` (CUDA `float16` на GPU или `int8` на CPU) → динамический `.ass` с пословной подсветкой и кириллическим шрифтом `Montserrat-ExtraBold.ttf` из `/assets/fonts`.
- **2 режима визуала:**
  1. **Gameplay Background:** нарезка случайных видео из `/assets/backgrounds` (либо плавный процедурный градиент, если папка пуста) + стартовая карточка-хук от Pillow.
  2. **AI Slideshow + Ken Burns:** генерация 5 вертикальных сцен через `SDXL-Turbo` на CUDA GPU (с процедурным фолбэком на CPU) + плавный зум/панорамирование в FFmpeg.
- **Финальный рендер:** автоопределение `h264_nvenc` (NVIDIA RTX) или `libx264`, auto-ducking фоновой музыки (`sidechaincompress`), сохранение в `/output/YYYY-MM-DD/video_XX.mp4` + `video_XX.txt`.
- **Web UI (React + Tailwind):** единый локальный дашборд раздаётся прямо через FastAPI с WebSocket прогресс-баром, встроенным плеером, копированием метаданных и загрузчиком ассетов.

## Быстрый старт на Linux
```bash
chmod +x start.sh
./start.sh
```
Откройте `http://127.0.0.1:8000`.

## Перенос и запуск на Windows 10/11 (NVIDIA RTX 3060 12GB)
1. Скопируйте папку проекта (`.venv/` и `frontend/node_modules/` переносить не нужно; достаточно `frontend/dist/` или Node.js).
2. Установите Python 3.12 (x64) и FFmpeg (`winget install -e --id Gyan.FFmpeg`).
3. Запустите **`setup_windows.bat`** — скрипт создаст `.venv`, установит PyTorch с CUDA 12.4, зависимости и проверит GPU/NVENC.
4. Запустите **`start_windows.bat`** — откроется браузер и сервер на `http://127.0.0.1:8000`.
5. Подробная инструкция находится в [PROGRESS.md](PROGRESS.md).
