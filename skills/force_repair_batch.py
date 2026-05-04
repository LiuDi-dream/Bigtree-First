"""
强制批量修复脚本：直接填充所有缺失的 ascension_materials_detail/talent_materials，不受现有字段影响。
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from playwright.async_api import async_playwright, Page

from build_baike_full_dict import (
    DETAIL_URL,
    scrape_detail,
    parse_ascension_tables,
    parse_talent_upgrade_steps,
)

SEARCH_URL = "https://baike.mihoyo.com/ys/obc/search?keyword={keyword}"

# 已确认的链接
MANUAL_DETAIL_URLS = {
    "哥伦比娅": "https://baike.mihoyo.com/ys/obc/content/507505/detail?bbs_presentation_style=no_header&visit_device=pc",
    "梦见月瑞希": "https://baike.mihoyo.com/ys/obc/content/504440/detail?bbs_presentation_style=no_header&visit_device=pc",
    "狼的末路": "https://baike.mihoyo.com/ys/obc/content/218/detail?bbs_presentation_style=no_header&visit_device=pc",
    "天空之翼": "https://baike.mihoyo.com/ys/obc/content/323/detail?bbs_presentation_style=no_header&visit_device=pc",
    "祭礼弓": "https://baike.mihoyo.com/ys/obc/content/177/detail?bbs_presentation_style=no_header&visit_device=pc",
}

async def search_baike(page: Page, name: str) -> List[Dict[str, Any]]:
    """搜索米游社百科，优先返回非卡牌页面"""
    await page.goto(SEARCH_URL.format(keyword=name), wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(800)
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
                result.push({ id, href, title });
            }
            // 去重
            const uniq = [];
            const seen = new Set();
            for (const item of result) {
                if (seen.has(item.id)) continue;
                seen.add(item.id);
                uniq.push(item);
            }
            return uniq;
        }
        """
    )
    
    # 排序：优先非卡牌、非成就、非攻略的页面
    def score(row):
        title = row.get("title", "")
        # 卡牌类型通常会显示"装备牌"、"类型"等
        if "装备牌" in title or "类型 :" in title or "获取 :" in title:
            return -1000
        if "成就" in title or "攻略" in title:
            return -500
        return 0
    
    sorted_rows = sorted(rows, key=score, reverse=True)
    return sorted_rows[:10]

async def force_repair_entity(page: Page, entity_key: str, entity: Dict[str, Any], entity_type: str, name_zh: str) -> bool:
    """强制填充缺失字段"""
    # 优先使用手动 URL
    url = MANUAL_DETAIL_URLS.get(name_zh)
    
    if not url:
        # 否则搜索 name_zh
        candidates = await search_baike(page, name_zh)
        if not candidates:
            print(f"  搜索无结果: {name_zh}")
            return False
        url = candidates[0]["href"]
    
    try:
        detail = await scrape_detail(page, url)
        tiers, total = parse_ascension_tables(detail.get("tables", []))
        talent = parse_talent_upgrade_steps(detail.get("tables", [])) if entity_type == "avatar" else []
        
        has_any = bool(tiers or total or talent)
        if not has_any:
            print(f"  无法解析表格: {name_zh}")
            return False
        
        # 强制覆盖（即使已有）
        cid_match = re.search(r"/content/(\d+)", url)
        cid = int(cid_match.group(1)) if cid_match else 0
        
        entity["baike"] = {
            "content_id": cid,
            "url": url,
            "title": detail.get("title", name_zh),
            "search_score": 999,
        }
        
        if tiers:
            entity["ascension_materials_detail"] = {
                "description": "米游社百科突破分段材料",
                "tiers": tiers,
            }
        
        if total:
            entity["ascension_total_cost"] = {
                "description": "米游社百科突破总材料",
                "materials": total,
            }
        
        if entity_type == "avatar" and talent:
            entity["talent_materials"] = {
                "description": "米游社百科天赋倍率表升级材料（单天赋）",
                "upgrade_steps": talent,
            }
        
        print(f"  ✓ {name_zh}")
        return True
    except Exception as e:
        print(f"  ✗ {name_zh}: {e}")
        return False

async def main():
    dict_path = Path("memory/game_dict_baike_full.json")
    d = json.loads(dict_path.read_text(encoding="utf-8"))
    
    # 找出缺失 ascension_materials_detail 的条目
    missing = []
    for key, v in d["avatars"].items():
        if not v.get("ascension_materials_detail"):
            missing.append((key, v, "avatar"))
    for key, v in d["weapons"].items():
        if not v.get("ascension_materials_detail"):
            missing.append((key, v, "weapon"))
    
    print(f"\n发现 {len(missing)} 个缺失 ascension_materials_detail 的条目")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": "http://127.0.0.1:7890"})
        page = await browser.new_page(viewport={"width": 1600, "height": 2600})
        
        ok_count = 0
        for i, (key, entity, entity_type) in enumerate(missing, 1):
            name_zh = entity.get("name_zh", key)
            print(f"[{i}/{len(missing)}] {entity_type}:{name_zh}")
            
            ok = await force_repair_entity(page, key, entity, entity_type, name_zh)
            if ok:
                ok_count += 1
        
        await browser.close()
    
    # 保存
    dict_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成: {ok_count}/{len(missing)} 修复成功")

if __name__ == "__main__":
    asyncio.run(main())
