import hashlib
import json
import math
from pathlib import Path
from typing import Any


VERSION = "v1"
ID_PATTERN = r"^[a-f0-9]{16}$"


def _make_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def root_page_id(query: str, tab: str, lang: str) -> str:
    return _make_id(f"root|{VERSION}|{normalize_query(query)}|{tab}|{lang}")


def child_page_id(parent_id: str, x: float, y: float) -> str:
    return _make_id(f"child|{VERSION}|{parent_id}|{round(x, 2)}|{round(y, 2)}")


def species_profile_id(query: str, lang: str) -> str:
    return _make_id(f"species|{VERSION}|{normalize_query(query)}|{lang}")


class CacheStore:
    def __init__(self, generated_dir: Path) -> None:
        self.generated_dir = generated_dir
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def image_path(self, page_id: str) -> Path:
        return self.generated_dir / f"{page_id}.png"

    def meta_path(self, page_id: str) -> Path:
        return self.generated_dir / f"{page_id}.json"

    def species_dir(self) -> Path:
        path = self.generated_dir.parent / "species"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def species_path(self, query: str, lang: str) -> Path:
        return self.species_dir() / f"{species_profile_id(query, lang)}.json"

    def read_page(self, page_id: str) -> dict[str, Any] | None:
        image_path = self.image_path(page_id)
        meta_path = self.meta_path(page_id)
        if not image_path.exists() or image_path.stat().st_size == 0:
            return None
        if not meta_path.exists() or meta_path.stat().st_size == 0:
            return None
        with meta_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def list_pages(self, query: str, lang: str) -> dict[str, list[dict[str, Any]]]:
        tabs = {"morphology": [], "evolution": [], "ecology": []}
        normalized_query = normalize_query(query)
        pages_with_mtime: list[tuple[float, dict[str, Any]]] = []
        for meta_path in self.generated_dir.glob("*.json"):
            page_id = meta_path.stem
            page = self.read_page(page_id)
            if not page:
                continue
            if normalize_query(str(page.get("initialQuery", ""))) != normalized_query:
                continue
            if page.get("lang") != lang:
                continue
            tab = page.get("tab")
            if tab not in tabs:
                continue
            pages_with_mtime.append((meta_path.stat().st_mtime, page))

        root_ids = {page["id"] for _, page in pages_with_mtime if not page.get("parentId")}

        def sort_key(item: tuple[float, dict[str, Any]]) -> tuple[int, int, float, str]:
            mtime, page = item
            parent_id = page.get("parentId")
            if not parent_id:
                rank = 0
            elif parent_id in root_ids:
                rank = 1
            else:
                rank = 2
            return rank, 0 if not parent_id else 1, mtime, page.get("id", "")

        for _, page in sorted(pages_with_mtime, key=sort_key):
            tabs[page["tab"]].append(page)
        return tabs

    def find_nearby_child(
        self, parent_id: str, x: float, y: float, radius: float = 0.08
    ) -> dict[str, Any] | None:
        best: tuple[float, dict[str, Any]] | None = None
        for meta_path in self.generated_dir.glob("*.json"):
            page = self.read_page(meta_path.stem)
            if not page or page.get("parentId") != parent_id:
                continue
            click = page.get("parentClick") or {}
            try:
                distance = math.hypot(float(click["x"]) - x, float(click["y"]) - y)
            except (KeyError, TypeError, ValueError):
                continue
            if distance <= radius and (best is None or distance < best[0]):
                best = (distance, page)
        return best[1] if best else None

    def write_page(self, page_id: str, image_bytes: bytes, page: dict[str, Any]) -> None:
        image_path = self.image_path(page_id)
        meta_path = self.meta_path(page_id)
        image_path.write_bytes(image_bytes)
        with meta_path.open("w", encoding="utf-8") as file:
            json.dump(page, file, ensure_ascii=False, indent=2)

    def read_species_profile(self, query: str, lang: str) -> dict[str, Any] | None:
        path = self.species_path(query, lang)
        if not path.exists() or path.stat().st_size == 0:
            return None
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write_species_profile(self, query: str, lang: str, profile: dict[str, Any]) -> None:
        path = self.species_path(query, lang)
        with path.open("w", encoding="utf-8") as file:
            json.dump(profile, file, ensure_ascii=False, indent=2)
