from pathlib import Path

from server.cache import CacheStore, child_page_id, root_page_id


def test_root_page_id_includes_tab_and_lang():
    zh_morphology = root_page_id(" 蓝环章鱼 ", "morphology", "zh")
    zh_evolution = root_page_id("蓝环章鱼", "evolution", "zh")
    en_morphology = root_page_id("蓝环章鱼", "morphology", "en")

    assert root_page_id("蓝环 章鱼", "morphology", "zh") == root_page_id(
        "蓝环   章鱼", "morphology", "zh"
    )
    assert zh_morphology != zh_evolution
    assert zh_morphology != en_morphology
    assert len(zh_morphology) == 16


def test_child_page_id_rounds_coordinates():
    parent_id = "abc123def4567890"

    assert child_page_id(parent_id, 0.354, 0.624) == child_page_id(parent_id, 0.35, 0.62)
    assert child_page_id(parent_id, 0.356, 0.624) != child_page_id(parent_id, 0.35, 0.62)


def test_cache_hit_requires_non_empty_png_and_json(tmp_path: Path):
    store = CacheStore(tmp_path)
    page = {
        "id": "0123456789abcdef",
        "imageUrl": "/static/generated/0123456789abcdef.png",
        "caption": "caption",
        "parentId": None,
        "parentClick": None,
        "initialQuery": "蓝环章鱼",
        "tab": "morphology",
        "lang": "zh",
    }

    store.write_page(page["id"], b"png-bytes", page)

    assert store.read_page(page["id"]) == page
    (tmp_path / f"{page['id']}.png").write_bytes(b"")
    assert store.read_page(page["id"]) is None


def test_species_profile_cache_round_trip(tmp_path: Path):
    store = CacheStore(tmp_path)
    profile = {"cn_name": "丽齿兽", "ecology": {"predators": [], "prey": ["二齿兽"]}}

    store.write_species_profile("丽齿兽", "zh", profile)

    assert store.read_species_profile(" 丽齿兽 ", "zh") == profile
    assert store.read_species_profile("丽齿兽", "en") is None
