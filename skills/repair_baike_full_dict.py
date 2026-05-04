"""
基于米游社百科修复现有全量字典中的缺失项。

约束：
- 只使用米游社百科，不读取 yatta 基字典作为数据来源。
- 不改变字典结构，只回填现有 avatar/weapon 条目中的缺失字段或更正错误的 baike 页面。
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page, async_playwright

from build_baike_full_dict import (
    DETAIL_URL,
    parse_ascension_tables,
    parse_talent_upgrade_steps,
    fetch_material_source,
    scrape_detail,
)

SEARCH_URL = "https://baike.mihoyo.com/ys/obc/search?keyword={keyword}"

# 已确认的米游社百科材料页，优先使用这些页面来修复缺失项。
MANUAL_DETAIL_URLS = {
    "哥伦比娅": "https://baike.mihoyo.com/ys/obc/content/507505/detail?bbs_presentation_style=no_header&visit_device=pc",
    "芙宁娜": "https://baike.mihoyo.com/ys/obc/content/500291/detail?bbs_presentation_style=no_header&visit_device=pc",
    "梦见月瑞希": "https://baike.mihoyo.com/ys/obc/content/504440/detail?bbs_presentation_style=no_header&visit_device=pc",
    "狼的末路": "https://baike.mihoyo.com/ys/obc/content/218/detail?bbs_presentation_style=no_header&visit_device=pc",
    "祭礼弓": "https://baike.mihoyo.com/ys/obc/content/177/detail?bbs_presentation_style=no_header&visit_device=pc",
}

# 这些名称在当前字典的错误列表里出现，但并不是有效的角色/武器百科条目。
SKIP_NAMES = {"安柏计划"}


SEARCH_KEYWORDS_AVATAR = [
    "{name}",
    "{name} 材料",
    "{name} 突破材料",
    "{name} 天赋 材料",
    "{name} 养成",
    "{name} 攻略",
]

SEARCH_KEYWORDS_WEAPON = [
    "{name}",
    "{name} 材料",
    "{name} 突破材料",
    "{name} 武器突破",
    "{name} 养成",
    "{name} 攻略",
]


def clean_name(value: str) -> str:
    return " ".join((value or "").split()).strip()


async def search_rows(page: Page, query: str) -> List[Dict[str, Any]]:
    await page.goto(SEARCH_URL.format(keyword=query), wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1200)
    rows = await page.evaluate(
        r"""
        () => {
            const result = [];
            const links = Array.from(document.querySelectorAll('a[href*="/obc/content/"]'));
            for (const a of links) {
                const href = a.href || a.getAttribute('href') || '';
                const m = href.match(/\/obc\/content\/(\d+)/);
                if (!m) continue;
                const id = m[1];
                const title = (a.textContent || '').replace(/\s+/g, ' ').trim();
                const parent = a.closest('li,article,div') || a.parentElement;
                const context = (parent?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 260);
                result.push({ id, href, title, context, query: "" });
            }
            const uniq = [];
            const seen = new Set();
            for (const item of result) {
                if (seen.has(item.id)) continue;
                seen.add(item.id);
                uniq.push(item);
            }
            return uniq;
        }
        """,
        query,
    )
    for row in rows:
        row["query"] = query
    return rows


async def gather_candidates(page: Page, name_zh: str, entity_type: str) -> List[Dict[str, Any]]:
    queries = SEARCH_KEYWORDS_AVATAR if entity_type == "avatar" else SEARCH_KEYWORDS_WEAPON
    all_rows: List[Dict[str, Any]] = []
    for template in queries:
        query = template.format(name=name_zh)
        try:
            all_rows.extend(await search_rows(page, query))
        except Exception:
            continue

    dedup: Dict[str, Dict[str, Any]] = {}
    for row in all_rows:
        dedup.setdefault(row["id"], row)

    rows = list(dedup.values())

    def score(row: Dict[str, Any]) -> int:
        title = clean_name(row.get("title", ""))
        context = clean_name(row.get("context", ""))
        query = clean_name(row.get("query", ""))
        text = f"{title} {context} {query}"
        score_value = 0

        if name_zh and name_zh in title:
            score_value += 140
        if name_zh and name_zh in context:
            score_value += 80
        if title == name_zh:
            score_value += 40

        if any(term in text for term in ["1级属性/突破所需材料", "突破材料", "角色突破", "武器突破"]):
            score_value += 420
        if any(term in text for term in ["材料", "升级材料", "天赋材料", "培养", "突破所需材料"]):
            score_value += 110

        if entity_type == "avatar":
            if any(term in text for term in ["角色牌", "行动牌", "卡牌", "NPC", "商店"]):
                score_value -= 400
            if "角色突破" in text or "1级属性/突破所需材料" in text:
                score_value += 260
            if "角色" in text:
                score_value += 20
            if "天赋" in text:
                score_value += 20
        else:
            if any(term in text for term in ["行动牌", "卡牌", "NPC", "商店"]):
                score_value -= 400
            if "武器突破" in text or "突破材料" in text:
                score_value += 260
            if "武器" in text:
                score_value += 20
            if "精炼" in text:
                score_value += 20

        if "【" in title and entity_type == "avatar":
            score_value -= 30
        if "索引" in text:
            score_value -= 120
        return score_value

    rows.sort(key=score, reverse=True)
    for row in rows:
        row["score"] = score(row)
    return rows


def entity_missing_fields(entity: Dict[str, Any], entity_type: str) -> List[str]:
    missing = []
    for field in ["baike", "ascension_materials_detail", "ascension_total_cost", "ascension_material_sources"]:
        if not entity.get(field):
            missing.append(field)
    if entity_type == "avatar" and not entity.get("talent_materials"):
        missing.append("talent_materials")
    return missing


async def build_source_map(
    page: Page,
    detail: Dict[str, Any],
    need_names: List[str],
    material_cache: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    source_map: Dict[str, Any] = {}
    name_to_link: Dict[str, str] = {}

    for lk in detail.get("links", []):
        n = clean_name(lk.get("text", ""))
        h = lk.get("href") or ""
        if n and h and len(n) > 1 and "*" not in n:
            name_to_link.setdefault(n, h)

    for mat_name in sorted(set(need_names)):
        if mat_name == "摩拉":
            source_map[mat_name] = {"source_lines": ["通用货币"], "schedule": None}
            continue

        if mat_name in material_cache:
            source_map[mat_name] = material_cache[mat_name]
            continue

        link = name_to_link.get(mat_name)
        if not link:
            # 回退：搜索材料名，优先抓材料详情页
            try:
                best_mat = await search_best_candidate(page, mat_name, "material")
                if best_mat:
                    link = DETAIL_URL.format(cid=int(best_mat["id"]))
            except Exception:
                link = None

        if not link:
            source_map[mat_name] = {"source_lines": ["未在百科页面自动匹配到材料详情"], "schedule": None}
            material_cache[mat_name] = source_map[mat_name]
            continue

        source_info = await fetch_material_source(page, link)
        source_map[mat_name] = source_info
        material_cache[mat_name] = source_info

    return source_map


async def search_best_candidate(page: Page, name_zh: str, entity_type: str) -> Optional[Dict[str, Any]]:
    rows = await gather_candidates(page, name_zh, entity_type)
    return rows[0] if rows else None


async def try_repair_entity(
    page: Page,
    entity_key: str,
    entity: Dict[str, Any],
    entity_type: str,
    material_cache: Dict[str, Dict[str, Any]],
) -> bool:
    name_zh = clean_name(entity.get("name_zh") or entity_key)
    missing = entity_missing_fields(entity, entity_type)
    if not missing:
        return False

    manual_url = MANUAL_DETAIL_URLS.get(name_zh)
    if manual_url:
        try:
            detail = await scrape_detail(page, manual_url)
            tiers, total_cost = parse_ascension_tables(detail.get("tables", []))
            talent_steps = parse_talent_upgrade_steps(detail.get("tables", [])) if entity_type == "avatar" else []

            has_any = bool(tiers or total_cost or talent_steps)
            if has_any:
                entity["baike"] = {
                    "content_id": int(re.search(r"/content/(\d+)/", manual_url).group(1)),
                    "url": manual_url,
                    "title": detail.get("title", ""),
                    "search_score": 999,
                }

                if tiers and not entity.get("ascension_materials_detail"):
                    entity["ascension_materials_detail"] = {
                        "description": "米游社百科突破分段材料",
                        "tiers": tiers,
                    }
                if total_cost and not entity.get("ascension_total_cost"):
                    entity["ascension_total_cost"] = {
                        "description": "米游社百科突破总材料",
                        "materials": total_cost,
                    }
                if entity_type == "avatar" and talent_steps and not entity.get("talent_materials"):
                    entity["talent_materials"] = {
                        "description": "米游社百科天赋倍率表升级材料（单天赋）",
                        "upgrade_steps": talent_steps,
                    }

                need_names: List[str] = []
                if total_cost:
                    need_names.extend(total_cost.keys())
                if entity_type == "avatar" and talent_steps:
                    for step in talent_steps:
                        need_names.extend(step.get("materials", {}).keys())

                if need_names:
                    source_map = await build_source_map(page, detail, need_names, material_cache)
                    entity["ascension_material_sources"] = source_map
                    if entity_type == "avatar" and talent_steps:
                        entity["talent_materials"]["sources"] = {
                            k: source_map.get(k, {"source_lines": ["未匹配到来源"], "schedule": None})
                            for step in talent_steps
                            for k in step.get("materials", {}).keys()
                        }

                return True
        except Exception:
            pass

    candidates = await gather_candidates(page, name_zh, entity_type)
    if not candidates:
        return False

    # 依次尝试候选页面，直到解析出至少一个缺失字段
    for candidate in candidates[:8]:
        try:
            detail_url = DETAIL_URL.format(cid=int(candidate["id"]))
            detail = await scrape_detail(page, detail_url)
            tiers, total_cost = parse_ascension_tables(detail.get("tables", []))
            talent_steps = parse_talent_upgrade_steps(detail.get("tables", [])) if entity_type == "avatar" else []

            has_any = bool(tiers or total_cost or talent_steps)
            if not has_any:
                continue

            # 只在解析到内容时，更新 baike 元信息和缺失字段
            entity["baike"] = {
                "content_id": int(candidate["id"]),
                "url": detail_url,
                "title": detail.get("title", ""),
                "search_score": candidate.get("score", 0),
            }

            if tiers and not entity.get("ascension_materials_detail"):
                entity["ascension_materials_detail"] = {
                    "description": "米游社百科突破分段材料",
                    "tiers": tiers,
                }
            if total_cost and not entity.get("ascension_total_cost"):
                entity["ascension_total_cost"] = {
                    "description": "米游社百科突破总材料",
                    "materials": total_cost,
                }
            if entity_type == "avatar" and talent_steps and not entity.get("talent_materials"):
                entity["talent_materials"] = {
                    "description": "米游社百科天赋倍率表升级材料（单天赋）",
                    "upgrade_steps": talent_steps,
                }

            # 只要有总材料或天赋材料，就补来源；如果都没有，也保留现有来源不动。
            need_names: List[str] = []
            if total_cost:
                need_names.extend(total_cost.keys())
            if entity_type == "avatar" and talent_steps:
                for step in talent_steps:
                    need_names.extend(step.get("materials", {}).keys())

            if need_names:
                source_map = await build_source_map(page, detail, need_names, material_cache)
                entity["ascension_material_sources"] = source_map
                if entity_type == "avatar" and talent_steps:
                    entity["talent_materials"]["sources"] = {
                        k: source_map.get(k, {"source_lines": ["未匹配到来源"], "schedule": None})
                        for step in talent_steps
                        for k in step.get("materials", {}).keys()
                    }

            return True

        except Exception:
            continue

    return False


async def repair_missing_dict(input_path: str, output_path: str, proxy_url: Optional[str], limit: int) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        game_dict = json.load(f)

    avatars = game_dict.get("avatars", {})
    weapons = game_dict.get("weapons", {})
    stats = game_dict.get("_baike_enhance_meta", {}).get("stats", {})
    error_names = []
    for e in stats.get("errors", []):
        if e.startswith(("avatar:", "weapon:")):
            typ, rest = e.split(":", 1)
            name, _ = rest.split(":", 1)
            if name.strip() in SKIP_NAMES:
                continue
            error_names.append((typ, name.strip()))

    async with async_playwright() as p:
        launch_kwargs: Dict[str, Any] = {"headless": True}
        if proxy_url:
            launch_kwargs["proxy"] = {"server": proxy_url}
        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page(viewport={"width": 1600, "height": 2600})

        material_cache: Dict[str, Dict[str, Any]] = {}
        repaired = 0

        # 先修错误清单，再补充所有缺失字段仍未完成的项
        targets: List[Tuple[str, str, Dict[str, Any]]] = []
        seen = set()
        for typ, name in error_names:
            group = avatars if typ == "avatar" else weapons
            for key, entity in group.items():
                if clean_name(entity.get("name_zh")) == name:
                    if (typ, key) not in seen:
                        targets.append((typ, key, entity))
                        seen.add((typ, key))
                    break

        for key, entity in avatars.items():
            if entity_missing_fields(entity, "avatar"):
                if ("avatar", key) not in seen:
                    targets.append(("avatar", key, entity))
                    seen.add(("avatar", key))
        for key, entity in weapons.items():
            if entity_missing_fields(entity, "weapon"):
                if ("weapon", key) not in seen:
                    targets.append(("weapon", key, entity))
                    seen.add(("weapon", key))

        if limit > 0:
            targets = targets[:limit]

        for idx, (typ, key, entity) in enumerate(targets, 1):
            name_zh = clean_name(entity.get("name_zh") or key)
            ok = await try_repair_entity(page, key, entity, typ, material_cache)
            if ok:
                repaired += 1
                print(f"[repair] {idx}/{len(targets)} {typ}:{name_zh} 完成")
            else:
                print(f"[repair] {idx}/{len(targets)} {typ}:{name_zh} 仍未修复")

        await browser.close()

    # 重新统计当前字典状态，避免保留旧的失败日志
    remaining_errors: List[str] = []
    avatar_matched = 0
    weapon_matched = 0
    for key, entity in avatars.items():
        if entity.get("baike"):
            avatar_matched += 1
        for field in entity_missing_fields(entity, "avatar"):
            remaining_errors.append(f"avatar:{clean_name(entity.get('name_zh') or key)}: 未解析到突破材料" if field != "baike" else f"avatar:{clean_name(entity.get('name_zh') or key)}: 搜索匹配不足")
            break
    for key, entity in weapons.items():
        if entity.get("baike"):
            weapon_matched += 1
        for field in entity_missing_fields(entity, "weapon"):
            remaining_errors.append(f"weapon:{clean_name(entity.get('name_zh') or key)}: 未解析到突破材料" if field != "baike" else f"weapon:{clean_name(entity.get('name_zh') or key)}: 搜索匹配不足")
            break

    # 只保留真正还缺失的项目，并过滤明确跳过的无效名称
    filtered_errors = []
    for err in remaining_errors:
        if any(skip_name in err for skip_name in SKIP_NAMES):
            continue
        filtered_errors.append(err)

    meta = game_dict.setdefault("_baike_enhance_meta", {})
    meta_stats = meta.setdefault("stats", {})
    meta_stats["avatar_matched"] = avatar_matched
    meta_stats["weapon_matched"] = weapon_matched
    meta_stats["avatar_done"] = len(avatars)
    meta_stats["weapon_done"] = len(weapons)
    meta_stats["errors"] = filtered_errors

    # 写回同结构，不新增顶层字段
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(game_dict, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("修复完成")
    print(f"输出: {output_path}")
    print(f"修复成功条数: {repaired}/{len(targets)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="修复米游社百科增强字典中的缺失项")
    parser.add_argument("--input", default="memory/game_dict_baike_full.json", help="输入字典路径")
    parser.add_argument("--output", default="memory/game_dict_baike_full.json", help="输出字典路径")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890", help="代理地址")
    parser.add_argument("--limit", type=int, default=0, help="仅修复前 N 个条目，0 表示全部")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        repair_missing_dict(
            input_path=args.input,
            output_path=args.output,
            proxy_url=args.proxy,
            limit=args.limit,
        )
    )
