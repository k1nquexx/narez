from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


def test_settings_masking_and_update() -> None:
    with TestClient(app) as client:
        # Save key and verify masking
        res = client.put(
            "/api/settings",
            json={
                "llm_api_key": "sk-test-secret-987654",
                "llm_model": "deepseek/deepseek-chat",
                "music_volume": 0.25,
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["llm_api_key_set"] is True
        assert "987654" not in body["llm_api_key_masked"]
        assert body["llm_api_key_masked"].endswith("7654")
        assert body["music_volume"] == 0.25

        # Updating other settings with omitted llm_api_key must preserve existing key
        res2 = client.put("/api/settings", json={"music_volume": 0.20})
        assert res2.status_code == 200
        assert res2.json()["llm_api_key_set"] is True

        # Clear key so E2E offline mode remains active
        res3 = client.put("/api/settings", json={"llm_api_key": ""})
        assert res3.status_code == 200
        assert res3.json()["llm_api_key_set"] is False


def test_asset_upload_and_delete_roundtrip(tmp_path: Path) -> None:
    with TestClient(app) as client:
        # Invalid extension rejected
        bad = client.post(
            "/api/assets/music",
            files={"file": ("bad.exe", b"123", "application/octet-stream")},
        )
        assert bad.status_code == 400

        # Valid mp3 upload + list + delete
        good = client.post(
            "/api/assets/music",
            files={"file": ("unit_test_track.mp3", b"ID3dummy", "audio/mpeg")},
        )
        assert good.status_code == 201
        listed = client.get("/api/assets").json()["music"]
        assert any(item["filename"] == "unit_test_track.mp3" for item in listed)

        deleted = client.delete("/api/assets/music/unit_test_track.mp3")
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
