from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal


Provider = Literal["deepseek", "openai", "claude"]


DEFAULT_BASE_URLS: dict[Provider, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "claude": "",
}

DEFAULT_MODELS: dict[Provider, str] = {
    "deepseek": "deepseek-chat",
    "openai": "gpt-4.1-mini",
    "claude": "claude-3-5-sonnet-latest",
}


@dataclass
class RuntimeConfig:
    storage_path: Path | None = None
    llmProvider: Provider = "deepseek"
    llmApiKey: str = ""
    llmBaseUrl: str = DEFAULT_BASE_URLS["deepseek"]
    llmModel: str = DEFAULT_MODELS["deepseek"]
    openaiApiKey: str = ""
    imageBaseUrl: str = ""
    imageModel: str = "gpt-image-1"
    imageResolution: str = "2k"
    imageQuality: str = "medium"

    def update(self, payload: dict[str, str]) -> None:
        provider = payload.get("llmProvider") or self.llmProvider
        if provider not in DEFAULT_MODELS:
            raise ValueError("Unsupported llmProvider")
        self.llmProvider = provider  # type: ignore[assignment]
        self.llmApiKey = payload.get("llmApiKey", self.llmApiKey).strip()
        self.llmBaseUrl = (
            payload.get("llmBaseUrl")
            or DEFAULT_BASE_URLS[self.llmProvider]
            or self.llmBaseUrl
        ).strip()
        self.llmModel = (payload.get("llmModel") or DEFAULT_MODELS[self.llmProvider]).strip()
        self.openaiApiKey = payload.get("openaiApiKey", self.openaiApiKey).strip()
        self.imageBaseUrl = (payload.get("imageBaseUrl") or self.imageBaseUrl).strip().rstrip("/")
        self.imageModel = (payload.get("imageModel") or self.imageModel or "gpt-image-1").strip()
        self.imageResolution = (
            payload.get("imageResolution") or self.imageResolution or "2k"
        ).strip()
        self.imageQuality = (payload.get("imageQuality") or self.imageQuality or "medium").strip()
        if self.llmProvider == "openai" and not self.openaiApiKey:
            self.openaiApiKey = self.llmApiKey
        self.save()

    def public_view(self) -> dict[str, str | bool]:
        return {
            "llmProvider": self.llmProvider,
            "llmBaseUrl": self.llmBaseUrl,
            "llmModel": self.llmModel,
            "hasLlmApiKey": bool(self.llmApiKey),
            "hasOpenaiApiKey": bool(self.openaiApiKey),
            "imageBaseUrl": self.imageBaseUrl,
            "imageModel": self.imageModel,
            "imageResolution": self.imageResolution,
            "imageQuality": self.imageQuality,
        }

    def ready(self) -> bool:
        return bool(self.llmApiKey and self.openaiApiKey)

    def save(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "llmProvider": self.llmProvider,
                    "llmApiKey": self.llmApiKey,
                    "llmBaseUrl": self.llmBaseUrl,
                    "llmModel": self.llmModel,
                    "openaiApiKey": self.openaiApiKey,
                    "imageBaseUrl": self.imageBaseUrl,
                    "imageModel": self.imageModel,
                    "imageResolution": self.imageResolution,
                    "imageQuality": self.imageQuality,
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

    def load(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return
        with self.storage_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        self.llmProvider = payload.get("llmProvider", self.llmProvider)
        self.llmApiKey = payload.get("llmApiKey", self.llmApiKey)
        self.llmBaseUrl = payload.get("llmBaseUrl", self.llmBaseUrl)
        self.llmModel = payload.get("llmModel", self.llmModel)
        self.openaiApiKey = payload.get("openaiApiKey", self.openaiApiKey)
        self.imageBaseUrl = payload.get("imageBaseUrl", self.imageBaseUrl)
        self.imageModel = payload.get("imageModel", self.imageModel)
        self.imageResolution = payload.get("imageResolution", self.imageResolution)
        self.imageQuality = payload.get("imageQuality", self.imageQuality)


runtime_config = RuntimeConfig()
