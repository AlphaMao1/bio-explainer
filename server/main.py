from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from .cache import CacheStore, ID_PATTERN
from .config import runtime_config
from .generator import PageGenerator
from .models import ModelCallError
from .prompts import DEFAULT_PROMPTS, PromptStore


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
GENERATED_DIR = STATIC_DIR / "generated"

cache = CacheStore(GENERATED_DIR)
prompt_store = PromptStore(ROOT / "server" / "prompts.json")
runtime_config.storage_path = ROOT / "server" / "config.local.json"
runtime_config.load()
page_generator = PageGenerator(cache, runtime_config, GENERATED_DIR)

app = FastAPI(title="Bio Explainer")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def prevent_app_shell_cache(request, call_next):
    response = await call_next(request)
    if request.url.path in {"/", "/static/app.js"}:
        response.headers["Cache-Control"] = "no-store"
    return response


class ConfigPayload(BaseModel):
    llmProvider: Literal["deepseek", "openai", "claude"] = "deepseek"
    llmApiKey: str = ""
    llmBaseUrl: str = ""
    llmModel: str = ""
    openaiApiKey: str = ""
    imageBaseUrl: str = ""
    imageModel: str = ""
    imageResolution: str = ""
    imageQuality: str = ""


class ClickPayload(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PagePayload(BaseModel):
    query: str | None = Field(default=None, min_length=1, max_length=100)
    tab: Literal["morphology", "evolution", "ecology"] | None = None
    lang: Literal["zh", "en"] | None = "zh"
    parentId: str | None = Field(default=None, pattern=ID_PATTERN)
    parentClick: ClickPayload | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "PagePayload":
        is_child = self.parentId is not None or self.parentClick is not None
        if is_child:
            if not self.parentId or not self.parentClick:
                raise ValueError("Child page requires parentId and parentClick")
            return self
        if not self.query or not self.tab or not self.lang:
            raise ValueError("Root page requires query, tab and lang")
        return self


class PromptsPayload(BaseModel):
    prompts: dict[str, str]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
def get_config() -> dict[str, dict[str, str | bool]]:
    return {"config": runtime_config.public_view()}


@app.post("/api/config")
def update_config(payload: ConfigPayload) -> dict[str, dict[str, str | bool]]:
    try:
        runtime_config.update(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"config": runtime_config.public_view()}


@app.get("/api/prompts")
def get_prompts() -> dict[str, dict[str, str]]:
    return {"prompts": prompt_store.get(), "defaults": DEFAULT_PROMPTS}


@app.put("/api/prompts")
def put_prompts(payload: PromptsPayload) -> dict[str, dict[str, str]]:
    return {"prompts": prompt_store.put(payload.prompts), "defaults": DEFAULT_PROMPTS}


@app.get("/api/pages")
def list_pages(query: str, lang: Literal["zh", "en"] = "zh") -> dict[str, dict[str, list[dict]]]:
    return {"pagesByTab": cache.list_pages(query, lang)}


@app.post("/api/page")
async def create_page(payload: PagePayload) -> dict[str, dict]:
    prompts = prompt_store.get()
    try:
        if payload.parentId and payload.parentClick:
            page = await page_generator.create_child(
                payload.parentId,
                payload.parentClick.model_dump(),
                prompts,
            )
        else:
            page = await page_generator.create_root(
                payload.query or "",
                payload.tab or "morphology",
                payload.lang or "zh",
                prompts,
            )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="生成超时，请降低质量或稍后重试") from exc
    except ModelCallError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"page": page}
