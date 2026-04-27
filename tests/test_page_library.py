from pathlib import Path

from fastapi.testclient import TestClient

import server.main as main
from server.cache import CacheStore


def test_list_pages_restores_root_and_children_by_query(tmp_path: Path):
    store = CacheStore(tmp_path)
    root = {
        "id": "1111111111111111",
        "imageUrl": "/static/generated/1111111111111111.png",
        "caption": "root",
        "parentId": None,
        "parentClick": None,
        "initialQuery": "雪豹",
        "tab": "morphology",
        "lang": "zh",
    }
    child = {
        "id": "2222222222222222",
        "imageUrl": "/static/generated/2222222222222222.png",
        "caption": "tail",
        "parentId": "1111111111111111",
        "parentClick": {"x": 0.2, "y": 0.6},
        "initialQuery": "雪豹",
        "tab": "morphology",
        "lang": "zh",
    }
    other = {
        "id": "3333333333333333",
        "imageUrl": "/static/generated/3333333333333333.png",
        "caption": "other",
        "parentId": None,
        "parentClick": None,
        "initialQuery": "帝王蟹",
        "tab": "morphology",
        "lang": "zh",
    }

    store.write_page(root["id"], b"root-png", root)
    store.write_page(child["id"], b"child-png", child)
    store.write_page(other["id"], b"other-png", other)

    pages = store.list_pages(" 雪豹 ", "zh")

    assert [page["id"] for page in pages["morphology"]] == [
        "1111111111111111",
        "2222222222222222",
    ]
    assert pages["evolution"] == []
    assert pages["ecology"] == []


def test_pages_endpoint_reads_cached_group_without_generation(tmp_path: Path, monkeypatch):
    store = CacheStore(tmp_path)
    page = {
        "id": "4444444444444444",
        "imageUrl": "/static/generated/4444444444444444.png",
        "caption": "root",
        "parentId": None,
        "parentClick": None,
        "initialQuery": "雪豹",
        "tab": "ecology",
        "lang": "zh",
    }
    store.write_page(page["id"], b"png", page)
    monkeypatch.setattr(main, "cache", store)

    response = TestClient(main.app).get("/api/pages", params={"query": "雪豹", "lang": "zh"})

    assert response.status_code == 200
    assert response.json()["pagesByTab"]["ecology"][0]["id"] == "4444444444444444"


def test_nearby_child_click_reuses_existing_page(tmp_path: Path):
    store = CacheStore(tmp_path)
    child = {
        "id": "5555555555555555",
        "imageUrl": "/static/generated/5555555555555555.png",
        "caption": "tail",
        "parentId": "1111111111111111",
        "parentClick": {"x": 0.2, "y": 0.6},
        "initialQuery": "snow leopard",
        "tab": "morphology",
        "lang": "en",
    }
    store.write_page(child["id"], b"png", child)

    assert store.find_nearby_child("1111111111111111", 0.23, 0.64)["id"] == child["id"]
    assert store.find_nearby_child("1111111111111111", 0.5, 0.8) is None
