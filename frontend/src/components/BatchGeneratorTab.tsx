import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  Clock,
  Flame,
  Gamepad2,
  Ghost,
  Loader2,
  MessageSquareText,
  Play,
  Sparkles,
  Square,
  Wand2,
} from "lucide-react";
import { apiCancelBatch, apiCreateBatch } from "../api";
import type {
  AppSettings,
  BatchItem,
  LanguageCode,
  NicheId,
  SystemInfo,
  TTSEngine,
  VisualMode,
  VoicesResponse,
} from "../types";

interface Props {
  voicesData: VoicesResponse | null;
  systemInfo: SystemInfo | null;
  settings: AppSettings | null;
  batches: BatchItem[];
  onBatchCreated: (batch: BatchItem) => void;
  onBatchUpdated: (batch: BatchItem) => void;
}

const NICHE_CARDS: Array<{
  id: NicheId;
  title: string;
  subtitle: string;
  accent: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  {
    id: "reddit",
    title: "Истории с Reddit",
    subtitle: "Драмы, рабочие байки, r/AskReddit",
    accent: "from-orange-500/20 to-amber-500/5 border-orange-500/40 text-orange-400",
    icon: MessageSquareText,
  },
  {
    id: "scary",
    title: "Страшные истории",
    subtitle: "Мистика, ночные смены, r/nosleep",
    accent: "from-red-500/20 to-rose-500/5 border-red-500/40 text-red-400",
    icon: Ghost,
  },
  {
    id: "psychology",
    title: "Психологические факты",
    subtitle: "Триггеры, харизма, нейронаука",
    accent: "from-violet-500/20 to-purple-500/5 border-violet-500/40 text-violet-400",
    icon: Brain,
  },
  {
    id: "motivation",
    title: "Мотивация",
    subtitle: "Дисциплина, фокус, сильный настрой",
    accent: "from-amber-500/20 to-yellow-500/5 border-amber-500/40 text-amber-400",
    icon: Flame,
  },
];

const STATUS_BADGE: Record<string, string> = {
  queued: "bg-zinc-800 text-zinc-300 border-zinc-700",
  scripting: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  tts: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  subtitles: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  visuals: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  rendering: "bg-orange-500/15 text-orange-300 border-orange-500/30",
  completed: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  failed: "bg-red-500/15 text-red-300 border-red-500/30",
  cancelled: "bg-zinc-800 text-zinc-400 border-zinc-700",
};

export const BatchGeneratorTab: React.FC<Props> = ({
  voicesData,
  systemInfo,
  settings,
  batches,
  onBatchCreated,
  onBatchUpdated,
}) => {
  const [niche, setNiche] = useState<NicheId>("reddit");
  const [language, setLanguage] = useState<LanguageCode>("ru");
  const [voice, setVoice] = useState<string>("ru-RU-DmitryNeural");
  const [ttsEngine, setTtsEngine] = useState<TTSEngine>("edge");
  const [ratePercent, setRatePercent] = useState<number>(15);
  const [visualMode, setVisualMode] = useState<VisualMode>("gameplay");
  const [subtitleColor, setSubtitleColor] = useState<string>("#FFE600");
  const [customTopic, setCustomTopic] = useState<string>("");
  const [count, setCount] = useState<number>(3);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    if (settings) {
      if (settings.subtitle_highlight_color) {
        setSubtitleColor(settings.subtitle_highlight_color);
      }
      const parsed = parseInt(settings.tts_default_rate.replace(/[^-\d]/g, ""), 10);
      if (!Number.isNaN(parsed)) {
        setRatePercent(Math.max(0, Math.min(25, parsed)));
      }
    }
  }, [settings]);

  useEffect(() => {
    const list = voicesData?.voices[language];
    if (list && list.length > 0 && !list.some((v) => v.id === voice)) {
      setVoice(list[0].id);
    }
  }, [language, voicesData, voice]);

  const currentVoices = voicesData?.voices[language] || [];
  const colorPresets = voicesData?.subtitle_colors || [
    { name: "Viral Yellow", hex: "#FFE600" },
    { name: "Neon Green", hex: "#39FF50" },
    { name: "Electric Cyan", hex: "#00E5FF" },
    { name: "Crimson Red", hex: "#FF3B30" },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setSubmitting(true);
    try {
      const rateStr = ratePercent >= 0 ? `+${ratePercent}%` : `${ratePercent}%`;
      const created = await apiCreateBatch({
        niche,
        language,
        voice,
        tts_engine: ttsEngine,
        tts_rate: rateStr,
        visual_mode: visualMode,
        subtitle_color: subtitleColor,
        custom_topic: customTopic.trim(),
        count,
      });
      onBatchCreated(created);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Ошибка создания пачки");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (batchId: string) => {
    try {
      const updated = await apiCancelBatch(batchId);
      onBatchUpdated(updated);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Не удалось отменить пачку");
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left: Configuration Form */}
      <form
        onSubmit={handleSubmit}
        className="space-y-6 rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-6 lg:col-span-7"
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Параметры генерации пачки</h2>
            <p className="text-sm text-zinc-400">
              {settings?.llm_api_key_set
                ? `LLM активен: ${settings.llm_model}`
                : "API-ключ LLM не задан — используется встроенный банк сценариев"}
            </p>
          </div>
          <span className="rounded-lg border border-zinc-700/80 bg-zinc-800/70 px-2.5 py-1 text-xs font-medium text-zinc-300">
            1080×1920 · 60fps
          </span>
        </div>

        {/* Niche Grid */}
        <div>
          <label className="mb-2.5 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
            1. Ниша и стиль подачи
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {NICHE_CARDS.map((card) => {
              const Icon = card.icon;
              const selected = niche === card.id;
              return (
                <button
                  type="button"
                  key={card.id}
                  onClick={() => setNiche(card.id)}
                  className={`flex items-start gap-3 rounded-xl border p-3.5 text-left transition ${
                    selected
                      ? `bg-gradient-to-br ${card.accent} ring-1 ring-white/15`
                      : "border-zinc-800 bg-zinc-950/60 hover:border-zinc-700"
                  }`}
                >
                  <div className="mt-0.5 rounded-lg bg-zinc-900/80 p-2">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{card.title}</div>
                    <div className="text-xs text-zinc-400">{card.subtitle}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Custom Topic */}
        <div>
          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
            2. Тема / Уточнение (опционально)
          </label>
          <input
            type="text"
            value={customTopic}
            onChange={(e) => setCustomTopic(e.target.value)}
            placeholder="Например: странный случай в ночной смене, эффект ореола, утренняя дисциплина..."
            className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3.5 py-2.5 text-sm text-white placeholder-zinc-500 focus:border-amber-400 focus:outline-none"
          />
        </div>

        {/* Language & Voice & Speed */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
              3. Язык и голос
            </label>
            <div className="mb-2.5 grid grid-cols-2 gap-1.5 rounded-xl border border-zinc-800 bg-zinc-950 p-1">
              {(["ru", "en"] as LanguageCode[]).map((code) => (
                <button
                  type="button"
                  key={code}
                  onClick={() => setLanguage(code)}
                  className={`rounded-lg py-1.5 text-xs font-semibold transition ${
                    language === code
                      ? "bg-amber-400 text-zinc-950"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {code === "ru" ? "Русский (RU)" : "English (EN)"}
                </button>
              ))}
            </div>
            <select
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-white focus:border-amber-400 focus:outline-none"
            >
              {currentVoices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
              TTS Движок и темп речи ({ratePercent >= 0 ? `+${ratePercent}%` : `${ratePercent}%`})
            </label>
            <select
              value={ttsEngine}
              onChange={(e) => setTtsEngine(e.target.value as TTSEngine)}
              className="mb-3 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-white focus:border-amber-400 focus:outline-none"
            >
              <option value="edge">Edge TTS (быстрый, бесплатный)</option>
              <option value="silero">
                Silero TTS {voicesData?.silero_available ? "(локально PyTorch)" : "(нет PyTorch — автофолбэк на Edge)"}
              </option>
            </select>
            <input
              type="range"
              min={0}
              max={25}
              step={1}
              value={ratePercent}
              onChange={(e) => setRatePercent(Number(e.target.value))}
              className="w-full accent-amber-400"
            />
            <div className="mt-1 flex justify-between text-[11px] text-zinc-500">
              <span>+0% (обычный)</span>
              <span>+15% (оптимально)</span>
              <span>+25% (быстрый)</span>
            </div>
          </div>
        </div>

        {/* Visual Mode */}
        <div>
          <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
            4. Визуальный ряд
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setVisualMode("gameplay")}
              className={`flex items-start gap-3 rounded-xl border p-3.5 text-left transition ${
                visualMode === "gameplay"
                  ? "border-amber-400/60 bg-amber-400/10"
                  : "border-zinc-800 bg-zinc-950/60 hover:border-zinc-700"
              }`}
            >
              <Gamepad2 className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
              <div>
                <div className="text-sm font-semibold text-white">Gameplay Background</div>
                <div className="text-xs text-zinc-400">
                  {systemInfo && systemInfo.assets.backgrounds_count > 0
                    ? `Случайный кусок из ${systemInfo.assets.backgrounds_count} видео + карточка`
                    : "Плавный анимированный градиент (пока папка фонов пуста)"}
                </div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setVisualMode("ai_slideshow")}
              className={`flex items-start gap-3 rounded-xl border p-3.5 text-left transition ${
                visualMode === "ai_slideshow"
                  ? "border-violet-400/60 bg-violet-400/10"
                  : "border-zinc-800 bg-zinc-950/60 hover:border-zinc-700"
              }`}
            >
              <Wand2 className="mt-0.5 h-5 w-5 shrink-0 text-violet-400" />
              <div>
                <div className="text-sm font-semibold text-white">AI Slideshow + Ken Burns</div>
                <div className="text-xs text-zinc-400">
                  {systemInfo?.hardware.cuda_available && systemInfo.hardware.diffusers_available
                    ? "5 сцен через SDXL-Turbo на CUDA GPU"
                    : "5 сцен с Ken Burns (процедурный арт на CPU без GPU)"}
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Subtitle Color & Count */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
              5. Цвет подсветки активного слова
            </label>
            <div className="flex flex-wrap items-center gap-2">
              {colorPresets.map((preset) => (
                <button
                  type="button"
                  key={preset.hex}
                  onClick={() => setSubtitleColor(preset.hex)}
                  title={preset.name}
                  className={`h-8 w-8 rounded-lg border transition ${
                    subtitleColor.toUpperCase() === preset.hex.toUpperCase()
                      ? "scale-110 border-white ring-2 ring-white/40"
                      : "border-zinc-700 opacity-80 hover:opacity-100"
                  }`}
                  style={{ backgroundColor: preset.hex }}
                />
              ))}
              <input
                type="color"
                value={subtitleColor}
                onChange={(e) => setSubtitleColor(e.target.value.toUpperCase())}
                className="h-8 w-10 cursor-pointer rounded-lg border border-zinc-700 bg-zinc-950 p-0.5"
                title="Свой цвет"
              />
              <span className="font-mono text-xs text-zinc-400">{subtitleColor}</span>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-zinc-400">
              6. Количество роликов в пачке ({count})
            </label>
            <div className="flex items-center gap-2">
              {[1, 3, 5, 10].map((presetCount) => (
                <button
                  type="button"
                  key={presetCount}
                  onClick={() => setCount(presetCount)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                    count === presetCount
                      ? "border-amber-400 bg-amber-400 text-zinc-950"
                      : "border-zinc-800 bg-zinc-950 text-zinc-300 hover:border-zinc-700"
                  }`}
                >
                  {presetCount}
                </button>
              ))}
              <input
                type="number"
                min={1}
                max={20}
                value={count}
                onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
                className="w-16 rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 py-1.5 text-center text-sm text-white focus:border-amber-400 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-3.5 py-2.5 text-sm text-red-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 py-3.5 text-sm font-bold text-zinc-950 shadow-lg shadow-amber-400/10 transition hover:bg-amber-300 disabled:opacity-50"
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Запуск очереди...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-current" />
              Запустить пачку ({count} шт.)
            </>
          )}
        </button>
      </form>

      {/* Right: Live Queue & Batch Monitor */}
      <div className="space-y-4 rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-6 lg:col-span-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Очередь генерации</h2>
          <span className="text-xs text-zinc-400">Всего пачек: {batches.length}</span>
        </div>

        {batches.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 py-14 text-center">
            <Sparkles className="mb-3 h-8 w-8 text-zinc-600" />
            <p className="text-sm font-medium text-zinc-300">Очередь пока пуста</p>
            <p className="mt-1 max-w-xs text-xs text-zinc-500">
              Выберите параметры слева и нажмите «Запустить пачку» для автономной сборки роликов.
            </p>
          </div>
        ) : (
          <div className="max-h-[680px] space-y-4 overflow-y-auto pr-1">
            {batches.map((batch) => {
              const isRunning = batch.status === "queued" || batch.status === "running";
              return (
                <div
                  key={batch.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4"
                >
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">
                          {batch.niche.toUpperCase()} · {batch.language.toUpperCase()}
                        </span>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                            STATUS_BADGE[batch.status] || STATUS_BADGE.queued
                          }`}
                        >
                          {batch.completed_count}/{batch.total_count}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs text-zinc-500">
                        {batch.visual_mode === "ai_slideshow" ? "AI Slideshow" : "Gameplay"} · {batch.voice}
                      </div>
                    </div>
                    {isRunning && (
                      <button
                        type="button"
                        onClick={() => handleCancel(batch.id)}
                        className="flex items-center gap-1 rounded-lg border border-red-500/40 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-300 hover:bg-red-500/20"
                      >
                        <Square className="h-3 w-3 fill-current" />
                        Стоп
                      </button>
                    )}
                  </div>

                  <div className="space-y-2.5">
                    {batch.jobs.map((job) => (
                      <div
                        key={job.id}
                        className="rounded-lg border border-zinc-800/80 bg-zinc-900/60 p-2.5"
                      >
                        <div className="mb-1.5 flex items-center justify-between gap-2 text-xs">
                          <span className="truncate font-medium text-zinc-200">
                            #{job.index_in_batch}{" "}
                            {job.title ? job.title : `Ролик ${job.index_in_batch}`}
                          </span>
                          <span className="flex shrink-0 items-center gap-1 text-zinc-400">
                            {job.status === "completed" && (
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                            )}
                            {job.status === "failed" && (
                              <AlertCircle className="h-3.5 w-3.5 text-red-400" />
                            )}
                            {job.status === "queued" && (
                              <Clock className="h-3.5 w-3.5 text-zinc-500" />
                            )}
                            {!["completed", "failed", "queued", "cancelled"].includes(job.status) && (
                              <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
                            )}
                            <span>{job.stage_label}</span>
                          </span>
                        </div>

                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                          <div
                            className={`h-full transition-all duration-300 ${
                              job.status === "failed"
                                ? "bg-red-500"
                                : job.status === "completed"
                                  ? "bg-emerald-400"
                                  : "bg-amber-400"
                            }`}
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>

                        {job.error_message && (
                          <div className="mt-1.5 rounded bg-red-950/60 p-1.5 text-[11px] text-red-300">
                            {job.error_message}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
