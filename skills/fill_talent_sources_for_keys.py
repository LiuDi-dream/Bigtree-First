"""
Fill talent_materials.sources for specific avatar keys with normalization matching.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Any

from playwright.async_api import async_playwright
from build_baike_full_dict import scrape_detail, find_best_content, fetch_material_source

JSON_PATH = Path('memory/game_dict_baike_full.json')
TARGET_KEYS = ['kirara', 'dehya']
PROXY = 'http://127.0.0.1:7890'

def norm(s: str) -> str:
    if not s:
        return ''
    s = s.replace('\u3000', ' ')
    s = re.sub(r"\*\s*\d+", '', s)  # remove *N
    # normalize Chinese quotes and spaces
    s = s.replace('“', '').replace('”', '').replace('「', '').replace('」', '')
    s = s.replace('·', '')
    s = re.sub(r"\s+", ' ', s)
    return s.strip().lower()

async def process_keys(keys):
    d = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    avatars = d.get('avatars', {})
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY})
        page = await browser.new_page(viewport={"width":1600, "height":2600})
        changed = 0
        for k in keys:
            ent = avatars.get(k)
            if not ent:
                print('Missing key', k)
                continue
            name = ent.get('name_zh') or k
            print('\nProcessing', k, name)
            # ensure talent_materials exists
            tm = ent.get('talent_materials')
            if not tm or not tm.get('upgrade_steps'):
                print(' No talent_materials.upgrade_steps')
                continue
            # get baike url
            baike = ent.get('baike') or {}
            url = baike.get('url')
            if not url:
                print('  no baike url; searching')
                best = await find_best_content(page, name, 'avatar')
                if not best:
                    print('  search failed')
                    continue
                url = f"https://baike.mihoyo.com/ys/obc/content/{best['id']}/detail?bbs_presentation_style=no_header&visit_device=pc"

            detail = await scrape_detail(page, url)
            # build normalized link map
            link_map = {}
            for lk in detail.get('links', []):
                t = lk.get('text') or ''
                h = lk.get('href') or ''
                nn = norm(t)
                if not nn:
                    continue
                # keep first occurrence
                link_map.setdefault(nn, h)
                # also map without quotes
                link_map.setdefault(norm(re.sub(r'[""\'"\u3000]', '', t)), h)

            # gather needed material names
            need = set()
            for step in tm['upgrade_steps']:
                need.update(step.get('materials', {}).keys())
            need = sorted(need)
            sources = {}
            for mat in need:
                print('  material', mat)
                if mat == '摩拉':
                    sources[mat] = {"source_lines": ["通用货币"], "schedule": None}
                    continue
                nmat = norm(mat)
                href = None
                # direct normalized match
                if nmat in link_map:
                    href = link_map[nmat]
                    print('   matched exact link text')
                else:
                    # substring match
                    for lk_txt, lk_href in link_map.items():
                        if nmat in lk_txt or lk_txt in nmat:
                            href = lk_href
                            print('   matched by substring:', lk_txt)
                            break
                if not href:
                    # fallback: search baike for material
                    print('   fallback search for material')
                    best = await find_best_content(page, mat, 'material')
                    if best and best.get('score',0) >= 20:
                        href = f"https://baike.mihoyo.com/ys/obc/content/{best['id']}/detail?bbs_presentation_style=no_header&visit_device=pc"
                if not href:
                    print('   no href found; marking unmapped')
                    sources[mat] = {"source_lines": ["未匹配到材料详情页"], "schedule": None}
                    continue
                info = await fetch_material_source(page, href)
                sources[mat] = info
                print('   fetched source:', info.get('source_lines')[:2])

            ent['talent_materials']['sources'] = sources
            changed += 1
        await browser.close()
    if changed:
        JSON_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\nDone. changed=', changed)

if __name__ == '__main__':
    asyncio.run(process_keys(TARGET_KEYS))
