import { useCallback, useEffect, useState } from "react";
import { Clapperboard, Cpu, Film, Layers, Settings } from "lucide-react";
import {
  apiGetAssets,
  apiGetBatches,
  apiGetSettings,
  apiGetSystemInfo,
  apiGetVideos,
  apiGetVoices,
} from "./api";
import { AssetsSettingsTab } from "./components/AssetsSettingsTab";
import { BatchGeneratorTab } from "./components/BatchGeneratorTab";
import { GalleryExportTab } from "./components/GalleryExportTab";
import type {
  AppSettings,
  AssetsResponse,
  BatchItem,
  JobItem,
  SystemInfo,
  VoicesResponse,
} from "./types";

type ActiveTab = "generator" | "gallery" | "settings";

export default function App() {
  const [tab, setTab] = useState<ActiveTab>("generator");
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [voicesData, setVoicesData] = useState<VoicesResponse | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [videos, setVideos] = useState<JobItem[]>([]);
  const [assets, setAssets] = useState<AssetsResponse | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const refreshAll = useCallback(async () => {
    try {
      const [sys, voi, set, bat, vid, ast] = await Promise.all([
        apiGetSystemInfo(),
        apiGetVoices(),
        apiGetSettings(),
        apiGetBatches(),
        apiGetVideos(),
        apiGetAssets(),
      ]);
      setSystemInfo(sys);
      setVoicesData(voi);
      setSettings(set);
      setBatches(bat);
      setVideos(vid);
      setAssets(ast);
    } catch {
      // ignore startup race
    }
  }, []);

  const refreshAssetsAndSystem = useCallback(async () => {
    const [sys, ast] = await Promise.all([apiGetSystemInfo(), apiGetAssets()]);
    setSystemInfo(sys);
    setAssets(ast);
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let closedByUnmount = false;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${proto}//${window.location.host}/ws/progress`);

      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => {
        setWsConnected(false);
        if (!closedByUnmount) {
          reconnectTimer = window.setTimeout(connect, 2000);
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "snapshot" && msg.data?.batches) {
            setBatches(msg.data.batches);
          } else if (msg.type === "batch_updated" && msg.data) {
            const incoming: BatchItem = msg.data;
            setBatches((prev) => {
              const exists = prev.some((b) => b.id === incoming.id);
              if (exists) {
                return prev.map((b) => (b.id === incoming.id ? incoming : b));
              }
              return [incoming, ...prev];
            });
          } else if (msg.type === "job_updated" && msg.data) {
            const job: JobItem = msg.data;
            setBatches((prev) =>
              prev.map((b) =>
                b.id === job.batch_id
                  ? {
                      ...b,
                      jobs: b.jobs.map((j) => (j.id === job.id ? job : j)),
                    }
                  : b
              )
            );
            if (job.status === "completed") {
              apiGetVideos().then(setVideos).catch(() => {});
              apiGetSystemInfo().then(setSystemInfo).catch(() => {});
            }
          }
        } catch {
          // ignore malformed event
        }
      };
    };

    connect();
    return () => {
      closedByUnmount = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);

  const hw = systemInfo?.hardware;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Top Navbar */}
      <header className="sticky top-0 z-20 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-400 text-zinc-950 shadow-lg shadow-amber-400/20">
              <Clapperboard className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-white">ShortsFactory</h1>
                <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
                  9:16 Studio
                </span>
              </div>
              <p className="text-xs text-zinc-400">Автономная пакетная генерация Shorts & TikTok</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 rounded-xl border border-zinc-800 bg-zinc-900/70 p-1">
            <button
              type="button"
              onClick={() => setTab("generator")}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                tab === "generator"
                  ? "bg-amber-400 text-zinc-950"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              Генератор пачек
            </button>
            <button
              type="button"
              onClick={() => setTab("gallery")}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                tab === "gallery"
                  ? "bg-amber-400 text-zinc-950"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Film className="h-3.5 w-3.5" />
              Галерея и экспорт
              {videos.length > 0 && (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[10px] ${
                    tab === "gallery" ? "bg-zinc-950 text-amber-300" : "bg-zinc-800 text-zinc-300"
                  }`}
                >
                  {videos.length}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setTab("settings")}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                tab === "settings"
                  ? "bg-amber-400 text-zinc-950"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Settings className="h-3.5 w-3.5" />
              Ассеты и настройки
            </button>
          </nav>

          {/* Hardware & Live Status */}
          <div className="flex items-center gap-2.5 text-xs">
            <div className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1.5">
              <Cpu className={`h-3.5 w-3.5 ${hw?.cuda_available ? "text-emerald-400" : "text-sky-400"}`} />
              <span className="font-medium text-zinc-200">
                {hw?.cuda_available ? "CUDA" : "CPU"} · {hw?.video_encoder || "libx264"}
              </span>
            </div>
            <div
              className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1.5"
              title="WebSocket статус"
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  wsConnected ? "bg-emerald-400" : "bg-amber-400 animate-pulse"
                }`}
              />
              <span className="text-zinc-400">{wsConnected ? "Live" : "Sync"}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {tab === "generator" && (
          <BatchGeneratorTab
            voicesData={voicesData}
            systemInfo={systemInfo}
            settings={settings}
            batches={batches}
            onBatchCreated={(created) =>
              setBatches((prev) => [created, ...prev.filter((b) => b.id !== created.id)])
            }
            onBatchUpdated={(updated) =>
              setBatches((prev) => prev.map((b) => (b.id === updated.id ? updated : b)))
            }
          />
        )}

        {tab === "gallery" && (
          <GalleryExportTab
            videos={videos}
            onDeleted={(deletedId) => {
              setVideos((prev) => prev.filter((v) => v.id !== deletedId));
              refreshAssetsAndSystem().catch(() => {});
            }}
          />
        )}

        {tab === "settings" && (
          <AssetsSettingsTab
            systemInfo={systemInfo}
            settings={settings}
            assets={assets}
            onSettingsUpdated={setSettings}
            onAssetsChanged={() => refreshAssetsAndSystem().catch(() => {})}
          />
        )}
      </main>
    </div>
  );
}
