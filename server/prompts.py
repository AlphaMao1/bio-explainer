import json
from pathlib import Path


DEFAULT_PROMPTS: dict[str, str] = {
    "style_description": """Visual style (must remain consistent across every page):
- Pure white or very light gray-white gradient background with generous whitespace
- Clean, premium, Apple keynote aesthetic — minimal, modern, high-end science poster
- Subject rendered in ultra-HD with strong 3D feel, realistic textures, soft studio lighting
- Textures must be convincing: fur, scales, carapace, skin folds, feathers, markings
- Clean modern typography with breathing room
- All text in the image must be in {lang_name}

Strict exclusions:
- No decorative borders, parchment aging, ornate fonts, vintage texture
- No neon, dark themes, UI cards, watermarks, tiny labels
- No cartoon, children's book, or low-end exhibition board style
- No deformed limbs, incorrect anatomy, blurry subjects, plastic look""",
    "species_info": """你是专业进化生物学科普编辑。给定物种名，输出 JSON：
{
  "cn_name": "中文名",
  "en_name": "English Name",
  "subtitle": "一句定位（15字内）",
  "distribution": "分布区域",
  "taxonomy": "纲-目-科",
  "features": [
    { "title": "特征标题", "desc": "1-2句，含进化意义" }
  ],
  "evolution_nodes": [
    { "mya": "5.4亿", "event": "寒武纪动物辐射", "relative": "早期双侧对称动物" }
  ],
  "predators": ["天敌1", "天敌2"],
  "prey": ["猎物1", "猎物2"],
  "ecology": {
    "role": "生态位，例如顶级捕食者/底栖清道夫/草食动物",
    "predators": ["真实同域同年代天敌；若无明确天敌则空数组"],
    "prey": ["真实同域同年代猎物/食物；必须避免跨时代物种"],
    "strategy": "一句话捕食/取食策略"
  },
  "geologic_period": "生存时代，现代物种写现生",
  "do_not_include": ["明确禁止画入或写入的错误对象，例如跨时代天敌"],
  "source_notes": ["事实依据摘要，列出2-4条关键约束"],
  "visual_identity": "给生图模型的形态约束：体态、牙齿/肢体/外壳等关键外观，以及不能像什么",
  "hunting_strategy": "一句话捕食策略",
  "summary": "总结句（20字内）"
}
features 必须 4 个；evolution_nodes 必须 5-7 个，从远到近排列，最后一个是目标物种自身。
严禁把不同地质时代无法相遇的物种放进同一生态图；化石物种必须写清同域同年代关系，不确定就留空并说明不确定。只输出 JSON。""",
    "morphology_root": """{STYLE_DESCRIPTION}

Generate a single 16:9 premium science poster about: {cn_name}（{en_name}）
Subject identity constraints:
- {visual_identity}
- Geologic/ecological constraint: {geologic_period}
- Strictly do not depict: {do_not_include}

Layout:
- Top-left: large bold title "{cn_name}", gray subtitle "{subtitle}",
  thin line, small gray "{en_name}" and "分布：{distribution}"
- Center: ultra-HD hero shot of {cn_name}, 50-70% of visual area,
  display-worthy pose, white background, realistic shadow.
  Around the subject, 3-4 thin annotation lines pointing from key body features to short labels.
- Bottom: four minimal info columns separated by thin gray lines.
  "{feat1_title}: {feat1_desc}" | "{feat2_title}: {feat2_desc}" | "{feat3_title}: {feat3_desc}" | "{feat4_title}: {feat4_desc}"
- Very bottom center: small gray "{summary}"

Output a single PNG image, 16:9.""",
    "evolution_root": """{STYLE_DESCRIPTION}

Generate a single 16:9 premium evolutionary timeline poster for: {cn_name}（{en_name}）
Subject identity constraints:
- {visual_identity}
- Geologic/ecological constraint: {geologic_period}
- Strictly do not depict: {do_not_include}

Layout — a vertical timeline running from top (ancient) to bottom (present):
- Title at top: "{cn_name}的进化之路"
- The timeline shows {N} key divergence nodes with a geological time label, event, and relative species mini-illustration.
- Nodes from ancient to recent:
{evolution_nodes_formatted}
- The final node (the target species) should be highlighted and larger.
- Connect all nodes with a clean vertical line, branch lines going right to each relative species silhouette.
- Keep white background, clean typography, thin lines, subtle color accents.

Each silhouette and time label should be visually distinct and clickable-looking.
Output a single PNG image, 16:9.""",
    "ecology_root": """{STYLE_DESCRIPTION}

Generate a single 16:9 premium ecological relationship poster for: {cn_name}（{en_name}）
Subject identity constraints:
- {visual_identity}

Layout — a food web centered on the target species:
- Title at top: "{cn_name}的生态位"
- Center: a medium-sized realistic illustration of {cn_name}
- Above: realistic illustrations of predators ({predators}), with downward arrows labeled "捕食" pointing to {cn_name}
- Below: realistic illustrations of prey ({prey}), with downward arrows from {cn_name} labeled "捕食"
- Brief hunting strategy note near {cn_name}: "{hunting_strategy}"
- Each predator and prey species should be clearly illustrated with its Chinese name labeled, sized proportionally.
- Geologic/ecological constraint: {geologic_period}
- Strictly do not include: {do_not_include}
- If predators are "无明确天敌", show no predator animals above; label the top as "无明确天敌 / 顶级捕食者".

Output a single PNG image, 16:9.""",
    "drill_down": """{STYLE_DESCRIPTION}

You are continuing a premium illustrated evolutionary biology book.
The provided image is the previous page. A red circle marks where the reader pointed.

Generate the next page (16:9) that drills deeper into the red circle area.
Choose the most appropriate visualization:

- Body part → anatomical cross-section, exploded view, or micro-structure
- Species silhouette on timeline → that species' morphology poster
- Geological era label → panorama of life during that period
- Food chain species → that predator/prey's detailed profile
- Divergence line → comparative anatomy at that branching event
- Anything else → use best scientific judgment

Page must have a bold title at top describing what it reveals.
Match the visual style exactly. Do NOT include the red circle.
Output a single PNG image, 16:9.""",
    "caption_root": """你是芳斯塔芙风格的进化生物学科普作者。用一段话（80-120字）介绍{query}，
须涵盖：进化地位、最独特的适应性特征、在生态系统中的角色。
语言克制、信息密度高、有叙事节奏感。使用{lang_label}。""",
    "caption_drill": """你是进化生物学科普作者。用户在上一页图片中点击了红圈标记的区域。
上一页所属 Tab：{tab}
上一页说明：{parent_caption}
请用一段话（60-100字）解释新页面主题的生物学意义。不要凭空把点击区域解释成未在上一页或新页面出现的器官。
可以涵盖：解剖结构、进化来源、生态功能、与近缘物种的对比。
语言克制、有信息密度。使用{lang_label}。""",
}


class PromptStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self) -> dict[str, str]:
        if not self.path.exists():
            return DEFAULT_PROMPTS.copy()
        with self.path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        return DEFAULT_PROMPTS | {key: str(value) for key, value in loaded.items()}

    def put(self, prompts: dict[str, str]) -> dict[str, str]:
        cleaned = DEFAULT_PROMPTS.copy()
        for key in DEFAULT_PROMPTS:
            if key in prompts:
                cleaned[key] = str(prompts[key])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(cleaned, file, ensure_ascii=False, indent=2)
        return cleaned
