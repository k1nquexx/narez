import type {
  AppSettings,
  AssetFile,
  AssetsResponse,
  BatchItem,
  CreateBatchPayload,
  JobItem,
  SystemInfo,
  VoicesResponse,
} from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // ignore json parse error
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const apiGetSystemInfo = () => requestJson<SystemInfo>("/api/system/info");
export const apiGetVoices = () => requestJson<VoicesResponse>("/api/voices");
export const apiGetSettings = () => requestJson<AppSettings>("/api/settings");

export const apiUpdateSettings = (payload: Record<string, unknown>) =>
  requestJson<AppSettings>("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const apiCreateBatch = (payload: CreateBatchPayload) =>
  requestJson<BatchItem>("/api/batches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const apiGetBatches = () => requestJson<BatchItem[]>("/api/batches");

export const apiCancelBatch = (batchId: string) =>
  requestJson<BatchItem>(`/api/batches/${batchId}/cancel`, { method: "POST" });

export const apiGetVideos = () => requestJson<JobItem[]>("/api/videos");

export const apiDeleteVideo = (jobId: string) =>
  requestJson<{ deleted: boolean; id: string }>(`/api/videos/${jobId}`, {
    method: "DELETE",
  });

export const apiGetAssets = () => requestJson<AssetsResponse>("/api/assets");

export async function apiUploadAsset(
  category: "backgrounds" | "music",
  file: File
): Promise<AssetFile> {
  const form = new FormData();
  form.append("file", file);
  return requestJson<AssetFile>(`/api/assets/${category}`, {
    method: "POST",
    body: form,
  });
}

export const apiDeleteAsset = (category: "backgrounds" | "music", filename: string) =>
  requestJson<{ deleted: boolean; filename: string }>(
    `/api/assets/${category}/${encodeURIComponent(filename)}`,
    { method: "DELETE" }
  );
