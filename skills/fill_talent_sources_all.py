"""Fill missing or incomplete avatar talent_materials.sources in memory/game_dict_baike_full.json."""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from playwright.async_api import Page, async_playwright

from build_baike_full_dict import fetch_material_source, find_best_content, scrape_detail

JSON_PATH = Path("memory/game_dict_baike_full.json")
DETAIL_URL = "https://baike.mihoyo.com/ys/obc/content/{cid}/detail?bbs_presentation_style=no_header&visit_device=pc"


def norm_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u3000", " ")
    s = re.sub(r"\*\s*\d+", "", s)
    s = s.replace("“", "").replace("”", "").replace("「", "").replace("」", "")
    s = s.replace("·", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def extract_need_names(ent: Dict[str, Any]) -> List[str]:
    tm = ent.get("talent_materials") or {}
    steps = tm.get("upgrade_steps") or []
    need: Set[str] = set()
    for step in steps:
        mats = step.get("materials") or {}
        for name in mats.keys():
            if name:
                need.add(name)
    return sorted(need)


def is_sources_incomplete(ent: Dict[str, Any]) -> bool:
    tm = ent.get("talent_materials")
    if not tm:
        return False
    need = extract_need_names(ent)
    if not need:
        return False

    sources = tm.get("sources")
    if not isinstance(sources, dict) or not sources:
        return True

    for mat in need:
        info = sources.get(mat)
        if not isinstance(info, dict):
            return True
        lines = info.get("source_lines")
        if not isinstance(lines, list) or len(lines) == 0:
            return True
    return False


def resolve_detail_url_from_ent(ent: Dict[str, Any]) -> Optional[str]:
    baike = ent.get("baike") or {}
    url = baike.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def build_link_map(detail: Dict[str, Any]) -> Dict[str, str]:
    link_map: Dict[str, str] = {}
    for lk in detail.get("links", []):
        text = (lk.get("text") or "").strip()
        href = (lk.get("href") or "").strip()
        if not text or not href:
            continue
        n = norm_text(text)
        if n:
            link_map.setdefault(n, href)
    return link_map


async def resolve_material_href(
    page: Page,
    material: str,
    link_map: Dict[str, str],
    material_href_cache: Dict[str, Optional[str]],
) -> Optional[str]:
    nmat = norm_text(material)
    if material in material_href_cache:
        return material_href_cache[material]

    href: Optional[str] = None

    if nmat in link_map:
        href = link_map[nmat]
    else:
        for ltxt, lhref in link_map.items():
            if nmat in ltxt or ltxt in nmat:
                href = lhref
                break

    if not href:
        best = await find_best_content(page, material, "material")
        if best and best.get("score", 0) >= 20:
            href = DETAIL_URL.format(cid=int(best["id"]))

    material_href_cache[material] = href
    return href


async def rebuild_sources_for_avatar(
    page: Page,
    key: str,
    ent: Dict[str, Any],
    material_href_cache: Dict[str, Optional[str]],
    material_source_cache: Dict[str, Dict[str, Any]],
) -> Tuple[bool, str]:
    name = ent.get("name_zh") or key
    need_names = extract_need_names(ent)
    if not need_names:
        return False, f"{name}: no talent materials"

    detail_url = resolve_detail_url_from_ent(ent)
    if not detail_url:
        best = await find_best_content(page, name, "avatar")
        if not best:
            return False, f"{name}: avatar search failed"
        detail_url = DETAIL_URL.format(cid=int(best["id"]))
        ent.setdefault("baike", {})["url"] = detail_url
        ent["baike"]["content_id"] = int(best["id"])

    detail = await scrape_detail(page, detail_url)
    link_map = build_link_map(detail)

    new_sources: Dict[str, Dict[str, Any]] = {}
    unresolved: List[str] = []

    for mat in need_names:
        if mat == "摩拉":
            new_sources[mat] = {"source_lines": ["通用货币"], "schedule": None}
            continue

        if mat in material_source_cache:
            new_sources[mat] = material_source_cache[mat]
            continue

        href = await resolve_material_href(page, mat, link_map, material_href_cache)
        if not href:
            info = {"source_lines": ["未匹配到材料详情页"], "schedule": None}
            new_sources[mat] = info
            material_source_cache[mat] = info
            unresolved.append(mat)
            continue

        info = await fetch_material_source(page, href)
        lines = info.get("source_lines")
        if not isinstance(lines, list) or len(lines) == 0:
            info = {"source_lines": ["未从材料页解析到来源文本"], "schedule": info.get("schedule")}
            unresolved.append(mat)
        new_sources[mat] = info
        material_source_cache[mat] = info

    ent.setdefault("talent_materials", {})["sources"] = new_sources
    if unresolved:
        return True, f"{name}: unresolved={','.join(unresolved)}"
    return True, f"{name}: ok"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fill missing/incomplete avatar talent material sources")
    parser.add_argument("--input", default=str(JSON_PATH), help="Input JSON path")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890", help="Playwright proxy")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of avatars to process")
    args = parser.parse_args()

    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))
    avatars = data.get("avatars") or {}

    pending: List[Tuple[str, Dict[str, Any]]] = []
    for key, ent in avatars.items():
        if is_sources_incomplete(ent):
            pending.append((key, ent))

    if args.limit > 0:
        pending = pending[: args.limit]

    print(f"pending avatars: {len(pending)}")
    if not pending:
        print("nothing to patch")
        return

    changed = 0
    unresolved_count = 0
    errors: List[str] = []

    material_href_cache: Dict[str, Optional[str]] = {}
    material_source_cache: Dict[str, Dict[str, Any]] = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": args.proxy} if args.proxy else None)
        page = await browser.new_page(viewport={"width": 1600, "height": 2600})

        for idx, (key, ent) in enumerate(pending, 1):
            try:
                ok, msg = await rebuild_sources_for_avatar(page, key, ent, material_href_cache, material_source_cache)
                if ok:
                    changed += 1
                if "unresolved=" in msg:
                    unresolved_count += 1
                print(f"[{idx}/{len(pending)}] {msg}")
            except Exception as exc:  # noqa: BLE001
                err = f"{ent.get('name_zh') or key}: {str(exc)[:160]}"
                errors.append(err)
                print(f"[{idx}/{len(pending)}] ERROR {err}")

        await browser.close()

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print(f"patched avatars: {changed}")
    print(f"avatars with unresolved materials: {unresolved_count}")
    print(f"errors: {len(errors)}")
    if errors:
        for e in errors[:20]:
            print(" -", e)


if __name__ == "__main__":
    asyncio.run(main())
