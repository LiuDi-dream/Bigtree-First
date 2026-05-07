"""
Fill missing `talent_materials.sources` for avatars in memory/game_dict_baike_full.json.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from playwright.async_api import async_playwright

from build_baike_full_dict import scrape_detail
import repair_baike_full_dict as repair

JSON_PATH = Path('memory/game_dict_baike_full.json')

async def process_one(page, key: str, ent: Dict[str, Any]) -> bool:
    name = ent.get('name_zh') or key
    if not ent.get('talent_materials'):
        return False
    if ent['talent_materials'].get('sources'):
        return False
    baike = ent.get('baike')
    if not baike or not baike.get('url'):
        return False
    detail = await scrape_detail(page, baike['url'])
    # get talent steps from page
    talent_steps = repair.parse_talent_upgrade_steps(detail.get('tables', []))
    # need names from talent_materials upgrade_steps
    upgrade_steps = ent['talent_materials'].get('upgrade_steps', [])
    need_names = []
    for step in upgrade_steps:
        need_names.extend(list(step.get('materials', {}).keys()))
    need_names = list(sorted(set(need_names)))
    if not need_names:
        ent['talent_materials']['sources'] = {}
        return True
    source_map = await repair.build_source_map(page, detail, need_names, {})
    ent['talent_materials']['sources'] = {
        n: source_map.get(n, {"source_lines":["未匹配到来源"], "schedule": None})
        for n in need_names
    }
    return True

async def main():
    d = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    avatars = d.get('avatars', {})
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server":"http://127.0.0.1:7890"})
        page = await browser.new_page(viewport={"width":1600, "height":2600})
        changed = 0
        for key, ent in avatars.items():
            try:
                ok = await process_one(page, key, ent)
            except Exception:
                ok = False
            if ok:
                changed += 1
                print('Patched', key, ent.get('name_zh'))
        await browser.close()
    if changed:
        JSON_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Done. patched=', changed)

if __name__ == '__main__':
    asyncio.run(main())
