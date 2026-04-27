import base64
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI, OpenAIError

from .config import RuntimeConfig


class ModelCallError(RuntimeError):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    match = re.search(r"\{.*\}", stripped, flags=re.S)
    if not match:
        raise ValueError("LLM did not return JSON")
    return json.loads(match.group(0))


class LlmClient:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def _client(self) -> OpenAI:
        return OpenAI(
            api_key=self.config.llmApiKey,
            base_url=self.config.llmBaseUrl or None,
            timeout=120,
        )

    def json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self._client().chat.completions.create(
            model=self.config.llmModel,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        return _extract_json(response.choices[0].message.content or "")

    def text(self, prompt: str) -> str:
        response = self._client().chat.completions.create(
            model=self.config.llmModel,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return (response.choices[0].message.content or "").strip()


class ImageClient:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self.client = OpenAI(
            api_key=config.openaiApiKey,
            base_url=config.imageBaseUrl or None,
            timeout=180,
        )

    def generate(self, prompt: str) -> bytes:
        try:
            response = self.client.images.generate(
                model=self.config.imageModel or "gpt-image-1",
                prompt=prompt,
                size="1536x1024",
                quality=self.config.imageQuality or "medium",
            )
            return base64.b64decode(response.data[0].b64_json)
        except OpenAIError as exc:
            raise ModelCallError(f"Image API request failed: {exc}") from exc

    def edit(self, image_path: Path, prompt: str) -> bytes:
        try:
            with image_path.open("rb") as image:
                response = self.client.images.edit(
                    model=self.config.imageModel or "gpt-image-1",
                    image=image,
                    prompt=prompt,
                    size="1536x1024",
                    quality=self.config.imageQuality or "medium",
                )
            return base64.b64decode(response.data[0].b64_json)
        except OpenAIError as exc:
            raise ModelCallError(f"Image API request failed: {exc}") from exc
