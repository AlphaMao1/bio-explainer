from pathlib import Path
from types import SimpleNamespace

from openai import APIConnectionError
import pytest

from server.config import RuntimeConfig
from server.generator import PageGenerator, build_root_caption
from server.models import ImageClient, ModelCallError


class FakeImages:
    def __init__(self) -> None:
        self.generate_calls = []
        self.edit_calls = []

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(b64_json="aW1hZ2UtYnl0ZXM=")])

    def edit(self, **kwargs):
        self.edit_calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(b64_json="ZWRpdC1ieXRlcw==")])


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.images = FakeImages()


def test_image_generation_uses_configured_openai_compatible_client():
    config = RuntimeConfig(
        llmApiKey="test-llm",
        openaiApiKey="test-image",
        imageBaseUrl="https://image-api.example/v1",
        imageModel="gpt-image-1",
        imageQuality="medium",
    )
    image = ImageClient(config)
    fake_client = FakeOpenAIClient()
    image.client = fake_client  # type: ignore[assignment]

    result = image.generate("prompt")

    assert result == b"image-bytes"
    assert fake_client.images.generate_calls == [
        {
            "model": "gpt-image-1",
            "prompt": "prompt",
            "size": "1536x1024",
            "quality": "medium",
        }
    ]


def test_image_edit_sends_reference_image_to_configured_client(tmp_path: Path):
    image_path = tmp_path / "marked.png"
    image_path.write_bytes(b"png")
    config = RuntimeConfig(
        llmApiKey="test-llm",
        openaiApiKey="test-image",
        imageModel="gpt-image-1",
    )
    image = ImageClient(config)
    fake_client = FakeOpenAIClient()
    image.client = fake_client  # type: ignore[assignment]

    result = image.edit(image_path, "drill")

    assert result == b"edit-bytes"
    call = fake_client.images.edit_calls[0]
    assert call["model"] == "gpt-image-1"
    assert call["prompt"] == "drill"
    assert call["size"] == "1536x1024"
    assert call["quality"] == "medium"


def test_openai_image_errors_are_wrapped_as_model_errors():
    class BrokenImages:
        def generate(self, **kwargs):
            raise APIConnectionError(request=None)

    config = RuntimeConfig(llmApiKey="test-llm", openaiApiKey="test-image")
    image = ImageClient(config)
    image.client = SimpleNamespace(images=BrokenImages())  # type: ignore[assignment]

    with pytest.raises(ModelCallError, match="Image API request failed"):
        image.generate("prompt")


def test_root_caption_uses_same_species_profile_as_image():
    profile = {
        "cn_name": "Demo animal",
        "geologic_period": "modern high mountains",
        "taxonomy": "Mammalia / Carnivora",
        "features": [{"title": "tail", "desc": "A long tail helps balance on cliffs. "}],
        "ecology": {
            "role": "apex predator",
            "predators": [],
            "prey": ["mountain ungulates", "hares"],
            "strategy": "stalking prey from rocky cover",
        },
        "summary": "mountain predator",
    }

    caption = build_root_caption(profile, "en")

    assert "apex predator" in caption
    assert "mountain ungulates" in caption
    assert "dinosaur" not in caption


def test_root_prompt_contains_visual_identity_and_forbidden_species(tmp_path):
    generator = PageGenerator(cache=None, config=None, generated_dir=tmp_path)  # type: ignore[arg-type]
    prompts = {
        "style_description": "style {lang_name}",
        "ecology_root": "{visual_identity}\nForbidden: {do_not_include}\nPrey: {prey}\nPredators: {predators}",
    }
    profile = {
        "cn_name": "Demo animal",
        "en_name": "Demo animal",
        "visual_identity": "low four-legged posture, not a dinosaur",
        "do_not_include": ["dinosaur", "dragon"],
        "ecology": {"predators": [], "prey": ["mountain ungulates"]},
        "features": [],
    }

    prompt = generator._root_prompt("ecology", prompts, profile, "en")

    assert "low four-legged" in prompt
    assert "dinosaur" in prompt
    assert "mountain ungulates" in prompt
    assert "Predators:" in prompt
