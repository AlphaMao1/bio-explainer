from fastapi.testclient import TestClient

from server.main import app, page_generator, prompt_store, runtime_config
from server.models import ModelCallError
from server.prompts import DEFAULT_PROMPTS


client = TestClient(app)


def test_config_round_trip_does_not_return_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_config, "storage_path", tmp_path / "config.json")
    response = client.post(
        "/api/config",
        json={
            "llmProvider": "deepseek",
            "llmApiKey": "test-llm-key",
            "llmBaseUrl": "https://api.deepseek.com/v1",
            "llmModel": "deepseek-chat",
            "openaiApiKey": "test-image-key",
            "imageBaseUrl": "https://image-api.example/v1",
            "imageModel": "gpt-image-1",
            "imageResolution": "2k",
            "imageQuality": "medium",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "config": {
            "llmProvider": "deepseek",
            "llmBaseUrl": "https://api.deepseek.com/v1",
            "llmModel": "deepseek-chat",
            "hasLlmApiKey": True,
            "hasOpenaiApiKey": True,
            "imageBaseUrl": "https://image-api.example/v1",
            "imageModel": "gpt-image-1",
            "imageResolution": "2k",
            "imageQuality": "medium",
        }
    }


def test_config_is_persisted_and_reloaded(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(runtime_config, "storage_path", config_path)

    response = client.post(
        "/api/config",
        json={
            "llmProvider": "deepseek",
            "llmApiKey": "test-llm-persist",
            "openaiApiKey": "test-image-persist",
            "imageBaseUrl": "https://image-api.example/v1",
            "imageModel": "gpt-image-1",
        },
    )

    assert response.status_code == 200
    assert "test-llm-persist" in config_path.read_text(encoding="utf-8")
    runtime_config.llmApiKey = ""
    runtime_config.openaiApiKey = ""
    runtime_config.load()
    assert runtime_config.ready()


def test_page_rejects_invalid_root_payload():
    response = client.post("/api/page", json={"query": "", "tab": "bad", "lang": "fr"})

    assert response.status_code == 422


def test_page_returns_json_error_for_model_failures(monkeypatch):
    async def fail_create_root(*args, **kwargs):
        raise ModelCallError("Image API request failed")

    monkeypatch.setattr(page_generator, "create_root", fail_create_root)

    response = client.post(
        "/api/page",
        json={"query": "蓝环章鱼", "tab": "morphology", "lang": "zh"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Image API request failed"}


def test_prompts_can_be_read_and_updated(tmp_path, monkeypatch):
    monkeypatch.setattr(prompt_store, "path", tmp_path / "prompts.json")
    prompts = client.get("/api/prompts").json()["prompts"]
    prompts["caption_root"] = "updated {query} {lang_label}"

    try:
        response = client.put("/api/prompts", json={"prompts": prompts})

        assert response.status_code == 200
        assert (
            client.get("/api/prompts").json()["prompts"]["caption_root"]
            == "updated {query} {lang_label}"
        )
    finally:
        client.put("/api/prompts", json={"prompts": DEFAULT_PROMPTS})
