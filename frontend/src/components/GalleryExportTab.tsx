import React, { useEffect, useState } from "react";
import {
  Check,
  Copy,
  Download,
  FileText,
  Film,
  Trash2,
} from "lucide-react";
import { apiDeleteVideo } from "../api";
import type { JobItem } from "../types";

interface Props {
  videos: JobItem[];
  onDeleted: (jobId: string) => void;
}

function formatBytes(bytes: number): string {
  if (!bytes) return "0 MB";
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const GalleryExportTab: React.FC<Props> = ({ videos, onDeleted }) => {
  const [selectedId, setSelectedId] = useState<string>("");
  const [copiedKey, setCopiedKey] = useState<string>("");

  useEffect(() => {
    if (videos.length > 0 && !videos.some((v) => v.id === selectedId)) {
      setSelectedId(videos[0].id);
    }
  }, [videos, selectedId]);

  const selected = videos.find((v) => v.id === selectedId) || videos[0] || null;

  const copyText = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(""), 1600);
    } catch {
      // ignore clipboard errors
    }
  };

  const handleDelete = async (jobId: string) => {
    await apiDeleteVideo(jobId);
    onDeleted(jobId);
  };

  if (videos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 py-20 text-center">
        <Film className="mb-3 h-10 w-10 text-zinc-600" />
        <h3 className="text-base font-semibold text-zinc-200">Готовых роликов пока нет</h3>
        <p className="mt-1 max-w-md text-sm text-zinc-500">
          Запустите генерацию во вкладке «Генератор пачек». Готовые MP4-ролики и тексты для
          публикации появятся здесь автоматически.
        </p>
      </div>
    );
  }

  const hashtagsText = (selected?.tags || []).map((t) => `#${t.replace(/^#/, "")}`).join(" ");
  const fullExportText = selected
    ? `${selected.title}\n\n${selected.description}\n\n${hashtagsText}`
    : "";

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left: Video list */}
      <div className="space-y-3 rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-5 lg:col-span-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Готовые видео ({videos.length})</h2>
        </div>
        <div className="max-h-[700px] space-y-2.5 overflow-y-auto pr-1">
          {videos.map((v) => {
            const active = selected?.id === v.id;
            return (
              <button
                type="button"
                key={v.id}
                onClick={() => setSelectedId(v.id)}
                className={`w-full rounded-xl border p-3.5 text-left transition ${
                  active
                    ? "border-amber-400/70 bg-amber-400/10"
                    : "border-zinc-800 bg-zinc-950/70 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="line-clamp-2 text-sm font-semibold text-white">
                    {v.title || "Без названия"}
                  </div>
                  <span className="shrink-0 rounded bg-zinc-800 px-1.5 py-0.5 text-[11px] font-medium text-zinc-300">
                    {v.duration_sec.toFixed(1)}s
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-zinc-400">
                  <span className="rounded bg-zinc-900 px-2 py-0.5">
                    {(v.niche || "shorts").toUpperCase()}
                  </span>
                  <span className="rounded bg-zinc-900 px-2 py-0.5">
                    {(v.language || "ru").toUpperCase()}
                  </span>
                  <span>{formatBytes(v.file_size_bytes)}</span>
                  {v.encoder_used && (
                    <span className="font-mono text-zinc-500">{v.encoder_used}</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right: Player & Export Metadata */}
      {selected && (
        <div className="grid grid-cols-1 gap-6 rounded-2xl border border-zinc-800/90 bg-zinc-900/60 p-6 md:grid-cols-12 lg:col-span-7">
          <div className="flex flex-col items-center md:col-span-5">
            <div className="w-full max-w-[270px] overflow-hidden rounded-2xl border border-zinc-700 bg-black shadow-2xl">
              <video
                key={selected.id}
                src={selected.stream_url || `/api/videos/${selected.id}/stream`}
                controls
                playsInline
                className="aspect-[9/16] w-full object-contain"
              />
            </div>

            <div className="mt-4 flex w-full max-w-[270px] flex-col gap-2">
              <a
                href={selected.download_url || `/api/videos/${selected.id}/download`}
                className="flex items-center justify-center gap-2 rounded-xl bg-amber-400 px-4 py-2.5 text-sm font-bold text-zinc-950 hover:bg-amber-300"
              >
                <Download className="h-4 w-4" />
                Скачать MP4
              </a>
              <div className="grid grid-cols-2 gap-2">
                <a
                  href={selected.meta_url || `/api/videos/${selected.id}/meta`}
                  className="flex items-center justify-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs font-medium text-zinc-200 hover:border-zinc-500"
                >
                  <FileText className="h-3.5 w-3.5" />
                  TXT
                </a>
                <button
                  type="button"
                  onClick={() => handleDelete(selected.id)}
                  className="flex items-center justify-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-300 hover:bg-red-500/20"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Удалить
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-4 md:col-span-7">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-base font-semibold text-white">Метаданные для Shorts / TikTok</h3>
              <button
                type="button"
                onClick={() => copyText("all", fullExportText)}
                className="flex items-center gap-1.5 rounded-lg border border-amber-400/50 bg-amber-400/15 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-400/25"
              >
                {copiedKey === "all" ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    Скопировано!
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    Скопировать всё
                  </>
                )}
              </button>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3.5">
              <div className="mb-1 flex items-center justify-between text-xs text-zinc-400">
                <span>Заголовок</span>
                <button
                  type="button"
                  onClick={() => copyText("title", selected.title)}
                  className="text-amber-400 hover:text-amber-300"
                >
                  {copiedKey === "title" ? "Скопировано" : "Копировать"}
                </button>
              </div>
              <p className="text-sm font-medium text-white">{selected.title}</p>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3.5">
              <div className="mb-1 flex items-center justify-between text-xs text-zinc-400">
                <span>Описание</span>
                <button
                  type="button"
                  onClick={() => copyText("desc", selected.description)}
                  className="text-amber-400 hover:text-amber-300"
                >
                  {copiedKey === "desc" ? "Скопировано" : "Копировать"}
                </button>
              </div>
              <p className="text-sm text-zinc-200">{selected.description}</p>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3.5">
              <div className="mb-1 flex items-center justify-between text-xs text-zinc-400">
                <span>Хештеги</span>
                <button
                  type="button"
                  onClick={() => copyText("tags", hashtagsText)}
                  className="text-amber-400 hover:text-amber-300"
                >
                  {copiedKey === "tags" ? "Скопировано" : "Копировать"}
                </button>
              </div>
              <p className="font-mono text-xs leading-relaxed text-amber-300/90">{hashtagsText}</p>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3.5">
              <div className="mb-1 text-xs text-zinc-400">Полный текст озвучки</div>
              <p className="max-h-40 overflow-y-auto text-xs leading-relaxed text-zinc-300">
                {selected.script_text}
              </p>
            </div>

            <div className="text-[11px] font-mono text-zinc-500">
              Файл: {selected.output_video_path}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
