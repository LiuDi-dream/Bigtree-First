"""
全量米游社百科增强脚本：为所有角色与武器补全分段升级材料与材料获取方式。

输入：memory/game_dict_yatta.json
输出：memory/game_dict_baike_full.json（默认）

说明：
- 不覆盖原始 yatta 字典。
- 角色：补全突破分段、突破总耗材、天赋升级分段与材料来源。
- 武器：补全突破分段、突破总耗材与材料来源。
- 数据来源：米游社百科（搜索页 + 详情页 + 材料详情页）。
"""

import argparse
import asyncio
import copy
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page, async_playwright

SEARCH_URL = "https://baike.mihoyo.com/ys/obc/search?keyword={keyword}"
DETAIL_URL = "https://baike.mihoyo.com/ys/obc/content/{cid}/detail?bbs_presentation_style=no_header&visit_device=pc"


def parse_material_pairs(text: str) -> List[Tuple[str, int]]:
    """解析形如“材料名 *数字”的序列，返回有序 pair 列表。"""
    if not text:
        return []
    normalized = " ".join(text.replace("\u3000", " ").split())
    pattern = re.compile(r"([^*\d\n]+?)\s*\*\s*(\d+)")
    pairs: List[Tuple[str, int]] = []
    for name, qty in pattern.findall(normalized):
        n = name.strip()
        if not n:
            continue
        if n in {"突破材料", "升级材料", "天赋材料", "详细属性"}:
            continue
        pairs.append((n, int(qty)))
    return pairs


def pairs_to_dict(pairs: List[Tuple[str, int]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for n, q in pairs:
        out[n] = out.get(n, 0) + q
    return out


def level_to_range(level: int) -> str:
    mapping = {
        20: "1-20",
        40: "20-40",
        50: "40-50",
        60: "50-60",
        70: "60-70",
        80: "70-80",
        90: "80-90",
    }
    return mapping.get(level, f"<= {level}")


def extract_lines_for_source(text: str, max_lines: int = 12) -> List[str]:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    keys = ("获得方式", "获取方式", "来源", "掉落", "兑换", "秘境", "周", "合成")
    hit = [ln for ln in lines if any(k in ln for k in keys)]
    uniq: List[str] = []
    seen = set()
    for ln in hit:
        if ln in seen:
            continue
        uniq.append(ln)
        seen.add(ln)
        if len(uniq) >= max_lines:
            break
    return uniq


async def find_best_content(page: Page, keyword: str, entity_type: str) -> Optional[Dict[str, Any]]:
    """通过百科搜索页按名称匹配最优 content。"""
    await page.goto(SEARCH_URL.format(keyword=keyword), wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1200)

    rows = await page.evaluate(
        r"""
        (name) => {
            const result = [];
            const links = Array.from(document.querySelectorAll('a[href*="/obc/content/"]'));
            for (const a of links) {
                const href = a.href || a.getAttribute('href') || '';
                const m = href.match(/\/obc\/content\/(\d+)/);
                if (!m) continue;
                const id = m[1];
                const title = (a.textContent || '').trim();
                const parent = a.closest('li,article,div') || a.parentElement;
                const context = (parent?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 260);
                result.push({ id, href, title, context });
            }
            const uniq = [];
            const seen = new Set();
            for (const r of result) {
                if (seen.has(r.id)) continue;
                seen.add(r.id);
                uniq.push(r);
            }
            return uniq;
        }
        """,
        keyword,
    )

    if not rows:
        return None

    def score(row: Dict[str, Any]) -> int:
        s = 0
        title = row.get("title", "")
        context = row.get("context", "")
        if title == keyword:
            s += 500
        if keyword in title:
            s += 240
        if keyword in context:
            s += 40
        if "索引" in title:
            s -= 280
        if "索引" in context:
            s -= 80
        if entity_type == "avatar":
            if "角色" in context:
                s += 20
        elif entity_type == "weapon":
            if "武器" in context:
                s += 20
        # 降低“攻略/活动”等噪声
        for noise in ("活动", "任务", "逸闻", "攻略", "视频", "成就"):
            if noise in context:
                s -= 10
        return s

    ranked = sorted(rows, key=score, reverse=True)
    best = ranked[0]
    best["score"] = score(best)
    return best


async def scrape_detail(page: Page, url: str) -> Dict[str, Any]:
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(1600)

    # 轻量滚动，触发懒加载
    for _ in range(8):
        await page.mouse.wheel(0, 1200)
        await page.wait_for_timeout(120)

    return await page.evaluate(
        r"""
        () => {
            const title = document.querySelector('h1')?.textContent?.trim() || document.title || '';

            const tables = [];
            document.querySelectorAll('table').forEach((table, idx) => {
                const rows = [];
                table.querySelectorAll('tr').forEach((tr) => {
                    const cells = Array.from(tr.querySelectorAll('th,td')).map(c => (c.textContent || '').replace(/\s+/g, ' ').trim());
                    if (cells.length) rows.push(cells);
                });
                const text = (table.textContent || '').replace(/\s+/g, ' ').trim();
                if (rows.length > 0) {
                    tables.push({ index: idx, rows, text: text.slice(0, 10000) });
                }
            });

            const links = [];
            document.querySelectorAll('a[href*="/obc/content/"]').forEach((a) => {
                const text = (a.textContent || '').replace(/\s+/g, ' ').trim();
                const href = a.href || a.getAttribute('href') || '';
                if (text && href) {
                    links.push({ text, href });
                }
            });
            const dedup = [];
            const seen = new Set();
            for (const x of links) {
                const k = `${x.text}@@${x.href}`;
                if (seen.has(k)) continue;
                seen.add(k);
                dedup.push(x);
            }

            return { title, tables, links: dedup };
        }
        """
    )


def parse_ascension_tables(tables: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """解析突破分段和总消耗。"""
    asc_tables = [t for t in tables if "突破材料" in t.get("text", "")]
    if not asc_tables:
        return [], {}

    # 对每个“突破材料”表提取材料段
    asc_segments: List[Dict[str, int]] = []
    for t in asc_tables:
        text = t.get("text", "")
        seg_match = re.search(
            r"突破材料\s*(.*?)(?:新天赋解锁|突破前|突破后|攻击方式|暴击率|治疗加成|元素充能|生命值|防御力|攻击力|$)",
            text,
            flags=re.S,
        )
        seg = seg_match.group(1) if seg_match else text
        pairs = parse_material_pairs(seg)
        if pairs:
            asc_segments.append(pairs_to_dict(pairs))

    if not asc_segments:
        return [], {}

    # 总材料：一般是材料种类最多且包含摩拉的那张
    total_cost = max(asc_segments, key=lambda d: len(d) + (20 if "摩拉" in d else 0))

    # 分段：去掉总材料和命座材料（无主的命星），按页面顺序保留前 6~7 段
    tiers: List[Dict[str, Any]] = []
    used = set()
    for mats in asc_segments:
        key = tuple(sorted(mats.items()))
        if key in used:
            continue
        used.add(key)

        if mats == total_cost:
            continue
        if len(mats) < 2:
            continue
        if any("无主的命星" in name for name in mats.keys()):
            continue

        tiers.append({"materials": mats})

    tiers = tiers[:7]
    for i, t in enumerate(tiers):
        lvl = [20, 40, 50, 60, 70, 80, 90][i] if i < 7 else 0
        t["level"] = lvl
        t["level_range"] = level_to_range(lvl)

    return tiers, total_cost


def parse_talent_upgrade_steps(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从天赋倍率表中的“升级材料”提取单天赋 1->10 分段。"""
    level_labels = [
        "1->2", "2->3", "3->4", "4->5", "5->6", "6->7", "7->8", "8->9", "9->10"
    ]

    for t in tables:
        text = t.get("text", "")
        if "升级材料" not in text:
            continue

        # 仅处理“升级材料”后面的内容
        idx = text.find("升级材料")
        seg = text[idx:] if idx >= 0 else text
        pairs = parse_material_pairs(seg)
        if not pairs:
            continue

        # 以天赋书（教导/指引/哲学）作为分组起点
        groups: List[List[Tuple[str, int]]] = []
        current: List[Tuple[str, int]] = []

        def is_book(name: str) -> bool:
            return ("教导" in name) or ("指引" in name) or ("哲学" in name)

        for name, qty in pairs:
            if is_book(name):
                if current:
                    groups.append(current)
                current = [(name, qty)]
            else:
                if current:
                    current.append((name, qty))
        if current:
            groups.append(current)

        if len(groups) >= 9:
            steps = []
            for i in range(9):
                steps.append({
                    "level": level_labels[i],
                    "materials": pairs_to_dict(groups[i]),
                })
            return steps

    return []


async def fetch_material_source(page: Page, url: str) -> Dict[str, Any]:
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(900)
    text = await page.evaluate("() => document.body.innerText || ''")
    lines = extract_lines_for_source(text)

    schedule = None
    for ln in lines:
        if "周" in ln:
            schedule = ln
            break

    return {
        "source_lines": lines,
        "schedule": schedule,
    }


async def build_full_baike_dict(
    input_path: str,
    output_path: str,
    proxy_url: str,
    limit_avatars: int,
    limit_weapons: int,
) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        src = json.load(f)

    out = copy.deepcopy(src)
    avatars: Dict[str, Dict[str, Any]] = out.get("avatars", {})
    weapons: Dict[str, Dict[str, Any]] = out.get("weapons", {})

    # 统计信息
    stat = {
        "avatar_total": len(avatars),
        "weapon_total": len(weapons),
        "avatar_done": 0,
        "weapon_done": 0,
        "avatar_matched": 0,
        "weapon_matched": 0,
        "errors": [],
    }

    material_source_cache: Dict[str, Dict[str, Any]] = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": proxy_url} if proxy_url else None)
        page = await browser.new_page(viewport={"width": 1600, "height": 2600})

        async def enrich_one(entity_key: str, entity: Dict[str, Any], entity_type: str) -> None:
            zh_name = entity.get("name_zh") or entity_key
            try:
                best = await find_best_content(page, zh_name, entity_type)
                if not best or best.get("score", 0) < 30:
                    stat["errors"].append(f"{entity_type}:{zh_name}: 搜索匹配不足")
                    return

                cid = int(best["id"])
                detail_url = DETAIL_URL.format(cid=cid)
                detail = await scrape_detail(page, detail_url)

                tiers, total_cost = parse_ascension_tables(detail.get("tables", []))
                if not tiers and not total_cost:
                    stat["errors"].append(f"{entity_type}:{zh_name}: 未解析到突破材料")

                # 基本百科元信息
                entity["baike"] = {
                    "content_id": cid,
                    "url": detail_url,
                    "title": detail.get("title", ""),
                    "search_score": best.get("score", 0),
                }

                if tiers:
                    entity["ascension_materials_detail"] = {
                        "description": "米游社百科突破分段材料",
                        "tiers": tiers,
                    }
                if total_cost:
                    entity["ascension_total_cost"] = {
                        "description": "米游社百科突破总材料",
                        "materials": total_cost,
                    }

                if entity_type == "avatar":
                    talent_steps = parse_talent_upgrade_steps(detail.get("tables", []))
                    if talent_steps:
                        entity["talent_materials"] = {
                            "description": "米游社百科天赋倍率表升级材料（单天赋）",
                            "upgrade_steps": talent_steps,
                        }

                # 材料来源：优先使用页面内材料链接
                source_map: Dict[str, Any] = {}
                name_to_link: Dict[str, str] = {}
                for lk in detail.get("links", []):
                    n = (lk.get("text") or "").strip()
                    h = lk.get("href") or ""
                    if not n or not h:
                        continue
                    # 只保留可能的材料名称
                    if len(n) > 1 and ("*" not in n):
                        name_to_link.setdefault(n, h)

                # 需要补来源的材料集合
                need_names = set()
                if total_cost:
                    need_names.update(total_cost.keys())
                if entity_type == "avatar" and "talent_materials" in entity:
                    for step in entity["talent_materials"]["upgrade_steps"]:
                        need_names.update(step.get("materials", {}).keys())

                # 抓来源（带缓存）
                for mat_name in sorted(need_names):
                    if mat_name == "摩拉":
                        source_map[mat_name] = {"source_lines": ["通用货币"], "schedule": None}
                        continue

                    if mat_name in material_source_cache:
                        source_map[mat_name] = material_source_cache[mat_name]
                        continue

                    link = name_to_link.get(mat_name)
                    if not link:
                        # 兜底：百科搜索材料名
                        best_mat = await find_best_content(page, mat_name, "material")
                        if best_mat and best_mat.get("score", 0) >= 20:
                            link = DETAIL_URL.format(cid=int(best_mat["id"]))

                    if not link:
                        source_map[mat_name] = {"source_lines": ["未在百科页面自动匹配到材料详情"], "schedule": None}
                        material_source_cache[mat_name] = source_map[mat_name]
                        continue

                    source_info = await fetch_material_source(page, link)
                    source_map[mat_name] = source_info
                    material_source_cache[mat_name] = source_info

                entity["ascension_material_sources"] = source_map
                if entity_type == "avatar" and "talent_materials" in entity:
                    entity["talent_materials"]["sources"] = {
                        k: source_map.get(k, {"source_lines": ["未匹配到来源"], "schedule": None})
                        for step in entity["talent_materials"]["upgrade_steps"]
                        for k in step.get("materials", {}).keys()
                    }

                if entity_type == "avatar":
                    stat["avatar_matched"] += 1
                else:
                    stat["weapon_matched"] += 1

            except Exception as exc:  # noqa: BLE001
                stat["errors"].append(f"{entity_type}:{zh_name}: {str(exc)[:120]}")

        avatar_items = list(avatars.items())
        weapon_items = list(weapons.items())

        if limit_avatars > 0:
            avatar_items = avatar_items[:limit_avatars]
        if limit_weapons > 0:
            weapon_items = weapon_items[:limit_weapons]

        for i, (k, v) in enumerate(avatar_items, 1):
            await enrich_one(k, v, "avatar")
            stat["avatar_done"] += 1
            if i % 10 == 0 or i == len(avatar_items):
                print(f"[avatar] {i}/{len(avatar_items)} 完成")

        for i, (k, v) in enumerate(weapon_items, 1):
            await enrich_one(k, v, "weapon")
            stat["weapon_done"] += 1
            if i % 20 == 0 or i == len(weapon_items):
                print(f"[weapon] {i}/{len(weapon_items)} 完成")

        await browser.close()

    out["_baike_enhance_meta"] = {
        "source": "baike.mihoyo.com",
        "note": "原始 yatta 字典未被覆盖，本文件为新生成增强字典",
        "stats": stat,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("✅ 完成：已生成新字典")
    print(f"输出: {output_path}")
    print(json.dumps(out["_baike_enhance_meta"], ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="全量米游社百科增强字典生成器")
    p.add_argument("--input", default="memory/game_dict_yatta.json", help="输入字典路径")
    p.add_argument("--output", default="memory/game_dict_baike_full.json", help="输出字典路径")
    p.add_argument("--proxy", default="http://127.0.0.1:7890", help="代理地址，空字符串表示不走代理")
    p.add_argument("--limit-avatars", type=int, default=0, help="仅处理前N个角色，0表示全部")
    p.add_argument("--limit-weapons", type=int, default=0, help="仅处理前N把武器，0表示全部")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        build_full_baike_dict(
            input_path=args.input,
            output_path=args.output,
            proxy_url=args.proxy,
            limit_avatars=args.limit_avatars,
            limit_weapons=args.limit_weapons,
        )
    )
