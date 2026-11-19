# Known Issues & Fallbacks

## 1. PyAV (`av>=19`) compatibility with `faster-whisper` (`decode_audio`)
- **Symptom:** `av==19.0.2` removed the `metadata_errors` keyword argument in `av.open()`, causing `TypeError: open() got an unexpected keyword argument 'metadata_errors'` inside `faster_whisper.audio.decode_audio()`.
- **Resolution:**
  1. `backend/services/subtitles.py` now decodes audio directly to 16kHz mono float32 PCM (`np.ndarray`) via FFmpeg (`_decode_audio_16k_f32`), completely bypassing `faster_whisper`'s PyAV call.
  2. `requirements.txt` additionally pins `av>=11.0.0,<17.0.0` for Windows and Linux environments.
