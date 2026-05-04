import asyncio
import json
from playwright.async_api import async_playwright


async def scroll_to_bottom(page, pause_ms=700, max_rounds=20):
    """滚动详情页，触发分段加载和延迟渲染。"""
    previous_height = await page.evaluate("() => document.body.scrollHeight")

    for _ in range(max_rounds):
        await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(pause_ms)
        current_height = await page.evaluate("() => document.body.scrollHeight")
        if current_height == previous_height:
            break
        previous_height = current_height

    await page.evaluate("() => window.scrollTo(0, 0)")
    await page.wait_for_timeout(300)

async def scrape_detail_page(url, base_url="https://gi.yatta.moe", proxy_url="http://127.0.0.1:7890"):
    """爬取单个物品的详细页面"""
    full_url = f"{base_url}{url}" if url.startswith('/') else url
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": proxy_url}
            )
            page = await browser.new_page()
            
            await page.goto(full_url, wait_until='load', timeout=30000)
            
            # 等待内容加载
            try:
                await page.wait_for_selector('h1, h2, .name, [class*="title"]', timeout=10000)
            except Exception:
                pass

            try:
                button = page.locator('text=显示初始至目前等级所需材料').first
                if await button.count():
                    await button.click(timeout=2000)
                    await page.wait_for_timeout(500)
            except Exception:
                pass
            
            # 延迟让JavaScript执行
            await page.evaluate('() => new Promise(r => setTimeout(r, 500))')
            await scroll_to_bottom(page)
            
            # 获取详细信息
            details = await page.evaluate('''
                () => {
                    const data = {};
                    
                    // 方法1: 获取主标题（h1）
                    let title = document.querySelector('h1')?.textContent?.trim();
                    if (!title) {
                        // 方法2: 尝试其他标题选择器
                        title = document.querySelector('h2')?.textContent?.trim() || '';
                        if (!title) {
                            title = document.querySelector('[class*="title"]')?.textContent?.trim() || '';
                        }
                    }
                    data.name = title || '';
                    
                    // 根据主物品卡片的背景等级判断稀有度
                    let rarity = 0;
                    const mainImage = document.querySelector('img[src*="UI_EquipIcon_"], img[src*="UI_AvatarIcon_"]');
                    const rarityCard = mainImage?.closest('[class*="bg-rarity"]');
                    const rarityClass = rarityCard?.className || '';
                    if (rarityClass.includes('bg-rarityFifth')) {
                        rarity = 5;
                    } else if (rarityClass.includes('bg-rarityFourth')) {
                        rarity = 4;
                    } else if (rarityClass.includes('bg-rarityThird')) {
                        rarity = 3;
                    } else if (rarityClass.includes('bg-raritySecond')) {
                        rarity = 2;
                    } else if (rarityClass.includes('bg-rarityFirst')) {
                        rarity = 1;
                    }
                    data.rarity = rarity;
                    
                    // 提取材料卡片（名称 + 数量）
                    const materialCards = [];
                    const seen = new Set();

                    document.querySelectorAll('a[href^="/chs/archive/material/"]').forEach(anchor => {
                        const href = anchor.getAttribute('href') || '';
                        const img = anchor.querySelector('img');
                        const name = (img?.getAttribute('title') || img?.getAttribute('alt') || '').trim();
                        const quantityNode = anchor.querySelector('div.absolute');
                        const quantityText = (quantityNode?.textContent || '').replace(/\\s+/g, ' ').trim();

                        if (!href || !name) {
                            return;
                        }

                        const key = `${href}|${name}|${quantityText}`;
                        if (seen.has(key)) {
                            return;
                        }
                        seen.add(key);

                        materialCards.push({
                            id: href.split('/').pop() || '',
                            name,
                            quantity_text: quantityText,
                            icon: img?.getAttribute('src') || '',
                            href,
                        });
                    });

                    data.materials_detail = materialCards;
                    data.materials = materialCards.map(item => item.name);
                    
                    return data;
                }
            ''')
            
            await browser.close()
            return details
            
        except Exception as e:
            print(f"  ❌ {url}: {str(e)[:50]}")
            try:
                await browser.close()
            except Exception:
                pass
            return {"name": "", "rarity": 0, "materials": [], "error": str(e)[:100]}


async def process_items_batch(items, base_type, proxy_url="http://127.0.0.1:7890"):
    """批量处理物品列表，获取详细信息"""
    processed = {}
    
    print(f"\n正在获取 {len(items)} 个{base_type}的详细信息...")
    
    # 并发处理，每次最多2个，降低 Playwright 连接压力
    for i in range(0, len(items), 2):
        batch = items[i:i+2]
        tasks = [scrape_detail_page(item['url'], proxy_url=proxy_url) for item in batch]
        results = await asyncio.gather(*tasks)
        
        for j, item in enumerate(batch):
            details = results[j]
            # 使用URL中的名称作为key（更可靠）
            key = item['url'].split('/')[-1]  # 例如 "aquila-favonia"
            processed[key] = {
                "url": item['url'],
                "name_zh": details.get('name', ''),
                "rarity": details.get('rarity', 0),
                "materials": details.get('materials', []),
                "materials_detail": details.get('materials_detail', []),
                "name_en": key  # 保存英文名
            }
            
            # 每隔10个打印进度
            if (i + j + 1) % 10 == 0:
                print(f"  进度: {i + j + 1}/{len(items)}")
    
    return processed


async def main():
    """主流程"""
    print("🔄 从 yatta.moe 爬取详细信息...\n")
    
    proxy = "http://127.0.0.1:7890"
    
    # 读取之前爬取的列表
    with open("memory/yatta_data.json", "r", encoding="utf-8") as f:
        yatta_data = json.load(f)
    
    weapons = yatta_data.get('weapons', [])
    avatars = yatta_data.get('avatars', [])
    
    print("📦 加载的数据:")
    print(f"  - 武器: {len(weapons)} 件")
    print(f"  - 角色: {len(avatars)} 名")
    
    # 爬取武器详情
    weapons_detail = await process_items_batch(weapons, "武器", proxy)
    
    # 爬取角色详情
    avatars_detail = await process_items_batch(avatars, "角色", proxy)
    
    # 组合结果
    result = {
        "weapons": weapons_detail,
        "avatars": avatars_detail,
        "stats": {
            "total_weapons": len(weapons_detail),
            "total_avatars": len(avatars_detail),
            "weapons_with_name": len([w for w in weapons_detail.values() if w.get('name_zh')]),
            "avatars_with_name": len([a for a in avatars_detail.values() if a.get('name_zh')])
        }
    }
    
    # 保存结果
    output_file = "memory/game_dict_yatta.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存到 {output_file}")
    print("  📊 统计信息:")
    print(f"     - 武器总数: {result['stats']['total_weapons']}")
    print(f"     - 武器中文名获取: {result['stats']['weapons_with_name']}")
    print(f"     - 角色总数: {result['stats']['total_avatars']}")
    print(f"     - 角色中文名获取: {result['stats']['avatars_with_name']}")
    
    # 打印示例
    print("\n📋 武器示例 (前3件):")
    for i, (key, w) in enumerate(list(weapons_detail.items())[:3]):
        print(f"  - {w.get('name_zh', '未获取')} ({key})")
        if w.get('materials'):
            print(f"    材料: {', '.join(w['materials'][:3])}")
    
    print("\n👤 角色示例 (前3名):")
    for i, (key, a) in enumerate(list(avatars_detail.items())[:3]):
        print(f"  - {a.get('name_zh', '未获取')} ({key})")
        if a.get('materials'):
            print(f"    材料: {', '.join(a['materials'][:3])}")


if __name__ == "__main__":
    asyncio.run(main())
