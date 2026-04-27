import asyncio
import tempfile
from pathlib import Path
from typing import Any

from .cache import CacheStore, child_page_id, root_page_id
from .config import RuntimeConfig
from .marker import mark_click
from .models import ImageClient, LlmClient


TAB_PROMPTS = {
    "morphology": "morphology_root",
    "evolution": "evolution_root",
    "ecology": "ecology_root",
}

LANG_NAMES = {"zh": "中文", "en": "English"}
LANG_LABELS = {"zh": "中文", "en": "English"}

CURATED_PROFILES = {
    ("丽齿兽", "zh"): {
        "cn_name": "丽齿兽",
        "en_name": "Gorgonops",
        "subtitle": "二叠纪剑齿猎手",
        "distribution": "二叠纪晚期的南部非洲卡鲁盆地",
        "geologic_period": "二叠纪晚期，约2.6亿至2.52亿年前",
        "taxonomy": "合弓纲-兽孔目-丽齿兽亚目",
        "features": [
            {"title": "剑状犬齿", "desc": "大型犬齿用于撕裂大型草食性合弓纲猎物。"},
            {"title": "宽大颞孔", "desc": "为颌部肌肉提供附着空间，支持快速咬合。"},
            {"title": "半直立四肢", "desc": "比早期匍匐型合弓纲更适于陆地追击与支撑。"},
            {"title": "顶级生态位", "desc": "处在二叠纪陆地食物网高位，不与恐龙同世。"},
        ],
        "evolution_nodes": [
            {"mya": "3.2亿", "event": "早期合弓纲出现", "relative": "早期盘龙类合弓纲"},
            {"mya": "2.72亿", "event": "兽孔目辐射", "relative": "基干兽孔类"},
            {"mya": "2.65亿", "event": "丽齿兽亚目分化", "relative": "早期丽齿兽类"},
            {"mya": "2.60亿", "event": "大型剑齿捕食者出现", "relative": "大型丽齿兽类"},
            {"mya": "2.55亿", "event": "卡鲁盆地顶级捕食者繁盛", "relative": "丽齿兽"},
            {"mya": "2.52亿", "event": "二叠纪末灭绝", "relative": "丽齿兽类消失"},
        ],
        "ecology": {
            "role": "陆地顶级捕食者",
            "predators": [],
            "prey": ["二齿兽类", "锯齿龙类", "中小型兽孔类"],
            "strategy": "伏击或短距离追击大型草食性合弓纲动物，以犬齿制造深切伤口。",
        },
        "predators": [],
        "prey": ["二齿兽类", "锯齿龙类", "中小型兽孔类"],
        "hunting_strategy": "伏击或短距离追击，以剑状犬齿切割猎物。",
        "do_not_include": ["恐龙", "暴龙", "鳄形超目", "现代大型爬行动物捕食丽齿兽"],
        "summary": "二叠纪剑齿顶级猎手",
        "visual_identity": (
            "丽齿兽应表现为二叠纪合弓纲兽孔类：低矮四足步态、厚重头骨、"
            "明显剑状犬齿、无恐龙式双足姿态、无鳄鱼式甲背。"
        ),
        "source_notes": [
            "丽齿兽类为中晚二叠世至二叠纪末的剑齿兽孔类合弓纲动物。",
            "丽齿兽处于其生态系统高位；恐龙和暴龙不属于同一时代。",
        ],
    }
}


def build_root_caption(species: dict[str, Any], lang: str) -> str:
    ecology = species.get("ecology") or {}
    features = species.get("features") or []
    feature = features[0]["desc"] if features else species.get("summary", "")
    prey = "、".join(ecology.get("prey") or species.get("prey") or [])
    role = ecology.get("role") or "生态系统成员"
    period = species.get("geologic_period") or species.get("distribution") or ""
    strategy = ecology.get("strategy") or species.get("hunting_strategy") or ""
    if lang == "en":
        return (
            f"{species.get('en_name') or species.get('cn_name')} was a {role} of {period}. "
            f"{feature} It likely targeted {prey or 'period-appropriate prey'}, "
            f"with a strategy centered on {strategy}."
        )
    return (
        f"{species.get('cn_name')}生活在{period}，属于{species.get('taxonomy')}，"
        f"在当时生态系统中是{role}。其关键适应包括：{feature}"
        f"主要猎物为{prey or '同域的草食性或中小型动物'}；{strategy}"
    )


class PageGenerator:
    def __init__(
        self,
        cache: CacheStore,
        config: RuntimeConfig,
        generated_dir: Path,
    ) -> None:
        self.cache = cache
        self.config = config
        self.generated_dir = generated_dir
        self.lock = asyncio.Lock()

    async def create_root(
        self,
        query: str,
        tab: str,
        lang: str,
        prompts: dict[str, str],
    ) -> dict[str, Any]:
        page_id = root_page_id(query, tab, lang)
        cached = self.cache.read_page(page_id)
        if cached:
            return cached

        async with self.lock:
            cached = self.cache.read_page(page_id)
            if cached:
                return cached
            return await asyncio.wait_for(
                asyncio.to_thread(self._create_root_sync, page_id, query, tab, lang, prompts),
                timeout=210,
            )

    async def create_child(
        self,
        parent_id: str,
        click: dict[str, float],
        prompts: dict[str, str],
    ) -> dict[str, Any]:
        nearby = self.cache.find_nearby_child(parent_id, click["x"], click["y"])
        if nearby:
            return nearby
        page_id = child_page_id(parent_id, click["x"], click["y"])
        cached = self.cache.read_page(page_id)
        if cached:
            return cached

        async with self.lock:
            nearby = self.cache.find_nearby_child(parent_id, click["x"], click["y"])
            if nearby:
                return nearby
            cached = self.cache.read_page(page_id)
            if cached:
                return cached
            return await asyncio.wait_for(
                asyncio.to_thread(self._create_child_sync, page_id, parent_id, click, prompts),
                timeout=210,
            )

    def _create_root_sync(
        self,
        page_id: str,
        query: str,
        tab: str,
        lang: str,
        prompts: dict[str, str],
    ) -> dict[str, Any]:
        self._ensure_ready()
        llm = LlmClient(self.config)
        image_client = ImageClient(self.config)
        species = self._species_info(llm, prompts, query, lang)
        image_prompt = self._root_prompt(tab, prompts, species, lang)
        image_bytes = image_client.generate(image_prompt)
        caption = build_root_caption(species, lang)
        page = {
            "id": page_id,
            "imageUrl": f"/static/generated/{page_id}.png",
            "caption": caption,
            "parentId": None,
            "parentClick": None,
            "initialQuery": query,
            "tab": tab,
            "lang": lang,
            "speciesProfile": species,
        }
        self.cache.write_page(page_id, image_bytes, page)
        return page

    def _create_child_sync(
        self,
        page_id: str,
        parent_id: str,
        click: dict[str, float],
        prompts: dict[str, str],
    ) -> dict[str, Any]:
        self._ensure_ready()
        parent = self.cache.read_page(parent_id)
        if not parent:
            raise ValueError("Parent page not found")

        image_client = ImageClient(self.config)
        llm = LlmClient(self.config)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as marked:
            marked_path = Path(marked.name)
        try:
            mark_click(self.cache.image_path(parent_id), marked_path, click["x"], click["y"])
            style = prompts["style_description"].format(lang_name=LANG_NAMES[parent["lang"]])
            image_prompt = prompts["drill_down"].format(STYLE_DESCRIPTION=style)
            image_bytes = image_client.edit(marked_path, image_prompt)
        finally:
            marked_path.unlink(missing_ok=True)

        caption = llm.text(
            prompts["caption_drill"].format(
                lang_label=LANG_LABELS[parent["lang"]],
                parent_caption=parent.get("caption", ""),
                tab=parent.get("tab", ""),
            )
        )
        page = {
            "id": page_id,
            "imageUrl": f"/static/generated/{page_id}.png",
            "caption": caption,
            "parentId": parent_id,
            "parentClick": {"x": round(click["x"], 4), "y": round(click["y"], 4)},
            "initialQuery": parent["initialQuery"],
            "tab": parent["tab"],
            "lang": parent["lang"],
        }
        self.cache.write_page(page_id, image_bytes, page)
        return page

    def _ensure_ready(self) -> None:
        if not self.config.ready():
            raise PermissionError("API keys are not configured")

    def _species_info(
        self, llm: LlmClient, prompts: dict[str, str], query: str, lang: str
    ) -> dict[str, Any]:
        curated = CURATED_PROFILES.get((query.strip(), lang))
        if curated:
            self.cache.write_species_profile(query, lang, curated)
            return curated
        cached = self.cache.read_species_profile(query, lang)
        if cached:
            return cached
        profile = llm.json(
            "Return valid JSON only.",
            f"{prompts['species_info']}\n\n物种：{query}\n语言：{LANG_LABELS[lang]}",
        )
        self.cache.write_species_profile(query, lang, profile)
        return profile

    def _root_prompt(
        self, tab: str, prompts: dict[str, str], species: dict[str, Any], lang: str
    ) -> str:
        style = prompts["style_description"].format(lang_name=LANG_NAMES[lang])
        features = self._features(species)
        nodes = species.get("evolution_nodes") or []
        node_lines = "\n".join(
            f"- {node.get('mya', '')}年前：{node.get('event', '')} → {node.get('relative', '')}"
            for node in nodes
        )
        values = {
            "STYLE_DESCRIPTION": style,
            "cn_name": species.get("cn_name", ""),
            "en_name": species.get("en_name", ""),
            "subtitle": species.get("subtitle", ""),
            "distribution": species.get("distribution", ""),
            "summary": species.get("summary", ""),
            "visual_identity": species.get(
                "visual_identity",
                (
                    f"Accurately depict {species.get('cn_name', '')} / {species.get('en_name', '')}; "
                    "avoid generic dinosaur, crocodile, mammal, or fantasy-monster substitutions."
                ),
            ),
            "predators": "、".join((species.get("ecology") or {}).get("predators") or species.get("predators") or ["无明确天敌"]),
            "prey": "、".join((species.get("ecology") or {}).get("prey") or species.get("prey") or []),
            "hunting_strategy": (species.get("ecology") or {}).get("strategy") or species.get("hunting_strategy", ""),
            "N": len(nodes),
            "evolution_nodes_formatted": node_lines,
            "geologic_period": species.get("geologic_period", ""),
            "do_not_include": "、".join(species.get("do_not_include") or []),
        }
        for index, feature in enumerate(features, start=1):
            values[f"feat{index}_title"] = feature["title"]
            values[f"feat{index}_desc"] = feature["desc"]
        return prompts[TAB_PROMPTS[tab]].format(**values)

    def _features(self, species: dict[str, Any]) -> list[dict[str, str]]:
        features = list(species.get("features") or [])[:4]
        while len(features) < 4:
            features.append({"title": "关键特征", "desc": "具有清晰的适应性意义。"})
        return [{"title": str(item.get("title", "")), "desc": str(item.get("desc", ""))} for item in features]
