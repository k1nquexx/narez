export type NicheId = "reddit" | "scary" | "psychology" | "motivation";
export type LanguageCode = "ru" | "en";
export type VisualMode = "gameplay" | "ai_slideshow";
export type TTSEngine = "edge" | "silero";

export interface HardwareInfo {
  os_name: string;
  python_version: string;
  ffmpeg_path: string | null;
  ffprobe_path: string | null;
  cuda_available: boolean;
  gpu_name: string | null;
  vram_gb: number | null;
  nvenc_available: boolean;
  video_encoder: string;
  whisper_device: string;
  whisper_compute_type: string;
  diffusers_available: boolean;
  torch_available: boolean;
}

export interface SystemInfo {
  hardware: HardwareInfo;
  fonts: string[];
  assets: {
    backgrounds_count: number;
    music_count: number;
    completed_videos_count: number;
  };
  whisper_models: string[];
}

export interface VoiceOption {
  id: string;
  name: string;
  gender: string;
  engine: string;
}

export interface VoicesResponse {
  voices: Record<LanguageCode, VoiceOption[]>;
  niches: Record<
    NicheId,
    {
      ru: string;
      en: string;
      default_tag_ru: string;
      default_tag_en: string;
    }
  >;
  subtitle_colors: Array<{ name: string; hex: string }>;
  silero_available: boolean;
}

export interface AppSettings {
  llm_api_key_set: boolean;
  llm_api_key_masked: string;
  llm_base_url: string;
  llm_model: string;
  whisper_model: string;
  tts_default_rate: string;
  music_volume: number;
  subtitle_highlight_color: string;
  sdxl_model: string;
}

export interface JobItem {
  id: string;
  batch_id: string;
  index_in_batch: number;
  status:
    | "queued"
    | "scripting"
    | "tts"
    | "subtitles"
    | "visuals"
    | "rendering"
    | "completed"
    | "failed"
    | "cancelled";
  progress: number;
  stage_label: string;
  title: string;
  hook: string;
  script_text: string;
  description: string;
  tags: string[];
  image_prompts: string[];
  output_video_path: string;
  output_meta_path: string;
  duration_sec: number;
  file_size_bytes: number;
  encoder_used: string;
  error_message: string;
  created_at: string;
  completed_at: string;
  niche?: NicheId;
  language?: LanguageCode;
  voice?: string;
  visual_mode?: VisualMode;
  subtitle_color?: string;
  file_exists?: boolean;
  stream_url?: string;
  download_url?: string;
  meta_url?: string;
}

export interface BatchItem {
  id: string;
  niche: NicheId;
  language: LanguageCode;
  voice: string;
  tts_engine: TTSEngine;
  tts_rate: string;
  visual_mode: VisualMode;
  subtitle_color: string;
  custom_topic: string;
  total_count: number;
  completed_count: number;
  failed_count: number;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  jobs: JobItem[];
}

export interface AssetFile {
  filename: string;
  size_bytes: number;
  modified_at: number;
}

export interface AssetsResponse {
  backgrounds: AssetFile[];
  music: AssetFile[];
}

export interface CreateBatchPayload {
  niche: NicheId;
  language: LanguageCode;
  voice: string;
  tts_engine: TTSEngine;
  tts_rate: string;
  visual_mode: VisualMode;
  subtitle_color: string;
  custom_topic: string;
  count: number;
}
