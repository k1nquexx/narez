import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Cpu,
  HardDrive,
  Music,
  Save,
  Trash2,
  Upload,
  Video,
} from "lucide-react";
import { apiDeleteAsset, apiUpdateSettings, apiUploadAsset } from "../api";
import type { AppSettings, AssetsResponse, SystemInfo } from "../types";

interface Props {
  systemInfo: SystemInfo | null;
  settings: AppSettings | null;
  assets: AssetsResponse | null;
  onSettingsUpdated: (s: AppSettings) => void;
  onAssetsChanged: () => void;
}

const LLM_PRESETS = [
  {
    label: "OpenRouter (DeepSeek)",
    baseUrl: "https://openrouter.ai/api/v1",
    model: "deepseek/deepseek-chat",
  },
  {
    label: "DeepSeek Direct",
    baseUrl: "https://api.deepseek.com/v1",
    model: "deepseek-chat",
  },
  {
    label: "OpenAI (GPT-4o mini)",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
  },
  {
    label: "Ollama Local",
    baseUrl: "http://127.0.0.1:11434/v1",
    model: "llama3.1:8b",
  },
];

export const AssetsSettingsTab: React.FC<Props> = ({
  systemInfo,
  settings,
  assets,
  onSettingsUpdated,
  onAssetsChanged,
}) => {
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [clearKey, setClearKey] = useState(false);
  const [baseUrl, setBaseUrl] = useState("https://openrouter.ai/api/v1");
  const [model, setModel] = useState("deepseek/deepseek-chat");
  const [whisperModel, setWhisperModel] = useState("auto");
  const [musicVolume, setMusicVolume] = useState(0.2);
  const [sdxlModel, setSdxlModel] = useState("stabilityai/sdxl-turbo");
  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);
  const [uploadingCat, setUploadingCat] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (settings) {
      setBaseUrl(settings.llm_base_url);
      setModel(settings.llm_model);
      setWhisperModel(settings.whisper_model);
      setMusicVolume(settings.music_volume);
      setSdxlModel(settings.sdxl_model);
    }
  }, [settings]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrorMsg("");
    try {
      const payload: Record<string, unknown> = {
        llm_base_url: baseUrl,
        llm_model: model,
        whisper_model: whisperModel,
        music_volume: musicVolume,
        sdxl_model: sdxlModel,
      };
      if (clearKey) {
        payload.llm_api_key = "";
      } else if (apiKeyInput.trim()) {
        payload.llm_api_key = apiKeyInput.trim();
      }
      const updated = await apiUpdateSettings(payload);
      onSettingsUpdated(updated);
      setApiKeyInput("");
      setClearKey(false);
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 2000);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Ошибка сохранения настроек");
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (
    category: "backgrounds" | "music",
    files: FileList | null
  ) => {
    if (!files || files.length === 0) return;
    setUploadingCat(category);
    setErrorMsg("");
    try {
      for (const file of Array.from(files)) {
        await apiUploadAsset(category, file);
      }
      onAssetsChanged();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Ошибка загрузки файла");
    } finally {
      setUploadingCat("");
    }
  };

  const handleDeleteAsset = async (
    category: "backgrounds" | "music",
    filename: string
  ) => {
    try {
      await apiDeleteAsset(category, filename);
      onAssetsChanged();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Ошибка удаления файла");
    }
  };

  const hw = systemInfo?.hardware;

  return (
    <div className="space-y-6">
      {/* Hardware Diagnostics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-zinc-400">
            <Cpu className="h-4 w-4 text-amber-400" />
            Устройство / GPU
          </div>
          <div className="text-sm font-semibold text-white">
            {hw?.cuda_available
              ? `${hw.gpu_name || "NVIDIA CUDA"} (${hw.vram_gb || "?"} GB)`
              : "CPU Режим (без GPU)"}
          </div>
          <div className="mt-1 text-xs text-zinc-500">{hw?.os_name || "Detecting..."}</div>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-zinc-400">
            <Video className="h-4 w-4 text-sky-400" />
            FFmpeg Энкодер
          </div>
          <div className="text-sm font-semibold text-white">
            {hw?.video_encoder || "libx264"}
          </div>
          <div className="mt-1 text-xs text-zinc-500">
            {hw?.nvenc_available ? "NVENC аппаратный активен" : "libx264 CPU фолбэк"}
          </div>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-zinc-400">
            <HardDrive className="h-4 w-4 text-violet-400" />
            Whisper & Diffusers
          </div>
          <div className="text-sm font-semibold text-white">
            {hw?.whisper_device.toUpperCase()} / {hw?.whisper_compute_type}
          </div>
          <div className="mt-1 text-xs text-zinc-500">
            SDXL Diffusers: {hw?.diffusers_available ? "установлен" : "CPU арт фолбэк"}
          </div>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="mb-1 text-xs font-medium text-zinc-400">Шрифты (/assets/fonts)</div>
          <div className="truncate text-sm font-semibold text-white">
            {systemInfo?.fonts.join(", ") || "Не найдены"}
          </div>
          <div className="mt-1 text-xs text-zinc-500">
            Python {hw?.python_version || "3.12"}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Settings Form */}
        <form
          onSubmit={handleSaveSettings}
          className="space-y-4 rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-6 lg:col-span-6"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Настройки LLM и рендера</h2>
            {savedNotice && (
              <span className="flex items-center gap-1 text-xs font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Сохранено
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {LLM_PRESETS.map((p) => (
              <button
                type="button"
                key={p.label}
                onClick={() => {
                  setBaseUrl(p.baseUrl);
                  setModel(p.model);
                }}
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-300 hover:border-amber-400/60"
              >
                {p.label}
              </button>
            ))}
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between text-xs text-zinc-400">
              <span>API-ключ LLM (OpenRouter / DeepSeek / OpenAI)</span>
              {settings?.llm_api_key_set && (
                <button
                  type="button"
                  onClick={() => setClearKey((v) => !v)}
                  className="text-red-400 hover:underline"
                >
                  {clearKey ? "Отменить очистку" : `Установлен (${settings.llm_api_key_masked}) · Очистить`}
                </button>
              )}
            </div>
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder={
                settings?.llm_api_key_set
                  ? "Оставьте пустым, чтобы сохранить текущий ключ"
                  : "sk-... (если пусто — работает встроенный генератор)"
              }
              className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3.5 py-2 text-sm text-white placeholder-zinc-500 focus:border-amber-400 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-amber-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Модель LLM</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-amber-400 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-zinc-400">Модель Faster-Whisper</label>
              <select
                value={whisperModel}
                onChange={(e) => setWhisperModel(e.target.value)}
                className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-amber-400 focus:outline-none"
              >
                {(systemInfo?.whisper_models || ["auto", "tiny", "base", "small", "medium"]).map(
                  (m) => (
                    <option key={m} value={m}>
                      {m === "auto" ? "auto (small на GPU / base на CPU)" : m}
                    </option>
                  )
                )}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-zinc-400">
                Громкость фоновой музыки ({Math.round(musicVolume * 100)}%)
              </label>
              <input
                type="range"
                min={0}
                max={0.6}
                step={0.02}
                value={musicVolume}
                onChange={(e) => setMusicVolume(Number(e.target.value))}
                className="mt-2.5 w-full accent-amber-400"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-zinc-400">Модель SDXL (для AI Slideshow)</label>
            <input
              type="text"
              value={sdxlModel}
              onChange={(e) => setSdxlModel(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-amber-400 focus:outline-none"
            />
          </div>

          {errorMsg && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={saving}
            className="flex items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-zinc-950 hover:bg-amber-300 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? "Сохранение..." : "Сохранить настройки"}
          </button>
        </form>

        {/* Assets Management */}
        <div className="space-y-4 lg:col-span-6">
          {/* Backgrounds */}
          <div className="rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="flex items-center gap-2 text-base font-semibold text-white">
                  <Video className="h-4 w-4 text-amber-400" />
                  Фоновые видео (/assets/backgrounds)
                </h3>
                <p className="text-xs text-zinc-400">
                  Minecraft паркур, GTA, слаймы (.mp4, .mov, .mkv, .webm)
                </p>
              </div>
              <label className="cursor-pointer rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs font-semibold text-zinc-200 hover:border-amber-400">
                <span className="flex items-center gap-1.5">
                  <Upload className="h-3.5 w-3.5" />
                  {uploadingCat === "backgrounds" ? "Загрузка..." : "Загрузить"}
                </span>
                <input
                  type="file"
                  multiple
                  accept=".mp4,.mov,.mkv,.webm,.avi"
                  className="hidden"
                  onChange={(e) => handleUpload("backgrounds", e.target.files)}
                />
              </label>
            </div>

            {!assets?.backgrounds.length ? (
              <div className="rounded-xl border border-dashed border-zinc-800 py-5 text-center text-xs text-zinc-500">
                Папка пуста — при рендере будет использован плавный процедурный градиент.
              </div>
            ) : (
              <div className="max-h-40 space-y-2 overflow-y-auto">
                {assets.backgrounds.map((item) => (
                  <div
                    key={item.filename}
                    className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs"
                  >
                    <span className="truncate font-medium text-zinc-200">{item.filename}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-zinc-500">
                        {(item.size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteAsset("backgrounds", item.filename)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Music */}
          <div className="rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="flex items-center gap-2 text-base font-semibold text-white">
                  <Music className="h-4 w-4 text-violet-400" />
                  Фоновая музыка (/assets/music)
                </h3>
                <p className="text-xs text-zinc-400">
                  Автоматически приглушается под голосом (auto-ducking)
                </p>
              </div>
              <label className="cursor-pointer rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs font-semibold text-zinc-200 hover:border-violet-400">
                <span className="flex items-center gap-1.5">
                  <Upload className="h-3.5 w-3.5" />
                  {uploadingCat === "music" ? "Загрузка..." : "Загрузить"}
                </span>
                <input
                  type="file"
                  multiple
                  accept=".mp3,.wav,.m4a,.ogg,.aac"
                  className="hidden"
                  onChange={(e) => handleUpload("music", e.target.files)}
                />
              </label>
            </div>

            {!assets?.music.length ? (
              <div className="rounded-xl border border-dashed border-zinc-800 py-5 text-center text-xs text-zinc-500">
                Музыка не загружена — ролики будут рендериться только с озвучкой.
              </div>
            ) : (
              <div className="max-h-40 space-y-2 overflow-y-auto">
                {assets.music.map((item) => (
                  <div
                    key={item.filename}
                    className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs"
                  >
                    <span className="truncate font-medium text-zinc-200">{item.filename}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-zinc-500">
                        {(item.size_bytes / (1024 * 1024)).toFixed(1)} MB
                      </span>
                      <button
                        type="button"
                        onClick={() => handleDeleteAsset("music", item.filename)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
