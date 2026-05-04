import asyncio
import json
from playwright.async_api import async_playwright
import os


async def scroll_to_bottom(page, pause_ms=700, max_rounds=30):
    """滚动页面直到内容不再增长，用于触发懒加载/虚拟列表渲染。"""
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

async def fetch_archive_page(url, selector, proxy_url="http://127.0.0.1:7890"):
    """从存档页面爬取数据"""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": proxy_url}
            )
            page = await browser.new_page()
            
            # 增加超时和等待时间
            print(f"  访问 {url}...")
            await page.goto(url, wait_until='load', timeout=60000)
            
            print("  等待页面元素...")
            await page.wait_for_selector(selector, timeout=30000)
            
            # 延迟一秒确保JavaScript完全渲染
            await page.evaluate('() => new Promise(r => setTimeout(r, 1000))')
            
            await browser.close()
            return True
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            await browser.close()
            return False


async def scrape_items(url, item_type, proxy_url="http://127.0.0.1:7890"):
    """爬取物品列表（武器或角色）"""
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": proxy_url}
            )
            page = await browser.new_page()
            
            print(f"📄 正在加载 {item_type} 列表...")
            await page.goto(url, wait_until='load', timeout=60000)
            
            print("  等待页面渲染...")
            try:
                await page.wait_for_selector('a[href*="/avatar/"], a[href*="/weapon/"]', timeout=15000)
            except Exception:
                pass
            
            await scroll_to_bottom(page)
            await scroll_to_bottom(page)
            
            # 尝试多种方式提取数据
            items = await page.evaluate('''
                () => {
                    const items = [];
                    
                    // 方法1: 查找所有链接
                    document.querySelectorAll('a').forEach(link => {
                        const href = link.getAttribute('href') || '';
                        if (href.includes('/avatar/') || href.includes('/weapon/')) {
                            const text = link.textContent?.trim() || '';
                            const img = link.querySelector('img');
                            const title = img?.getAttribute('alt') || img?.getAttribute('title') || text;
                            const label = title.replace(/\\s+/g, ' ').trim();

                            if (!label || label === 'Home Yatta! Menu 搜索 设置') {
                                return;
                            }
                            
                            if (label && label.length > 0 && label.length < 100) {
                                items.push({
                                    name: label,
                                    url: href,
                                    type: href.includes('/avatar/') ? 'avatar' : 'weapon'
                                });
                            }
                        }
                    });
                    
                    // 方法2: 查找所有 div 容器
                    document.querySelectorAll('div[class*="item"], div[class*="card"]').forEach(div => {
                        const link = div.querySelector('a');
                        const text = div.textContent?.trim() || '';
                        if (link && text.length > 0 && text.length < 100 && !items.some(i => i.name === text)) {
                            items.push({
                                name: text,
                                url: link.getAttribute('href') || '',
                                type: 'unknown'
                            });
                        }
                    });
                    
                    // 去重
                    const unique = [];
                    const seen = new Set();
                    items.forEach(item => {
                        const key = item.url;
                        if (!seen.has(key) && key) {
                            seen.add(key);
                            unique.push(item);
                        }
                    });
                    
                    return unique;
                }
            ''')
            
            await browser.close()
            
            print(f"✅ 成功获取 {len(items)} 项")
            return items
            
        except Exception as e:
            print(f"❌ 爬取失败: {e}")
            await browser.close()
            return []


async def main():
    """主爬虫流程"""
    print("🔄 从 yatta.moe 爬取游戏数据...\n")
    
    proxy = "http://127.0.0.1:7890"
    
    # 爬取武器列表
    print("步骤 1️⃣ : 爬取武器列表")
    weapons = await scrape_items('https://gi.yatta.moe/chs/archive/weapon', 'weapon', proxy)
    print()
    
    # 爬取角色列表
    print("步骤 2️⃣ : 爬取角色列表")
    avatars = await scrape_items('https://gi.yatta.moe/chs/archive/avatar', 'avatar', proxy)
    print()
    
    # 保存结果
    result = {
        "weapons": weapons,
        "avatars": avatars,
        "stats": {
            "total_weapons": len(weapons),
            "total_avatars": len(avatars)
        }
    }
    
    # 创建输出目录
    os.makedirs("memory", exist_ok=True)
    
    # 保存到文件
    output_file = "memory/yatta_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"📊 数据已保存到 {output_file}")
    print(f"  ✓ 武器总数: {len(weapons)}")
    print(f"  ✓ 角色总数: {len(avatars)}")
    
    # 打印示例
    if weapons:
        print("\n📋 武器示例 (前3件):")
        for w in weapons[:3]:
            print(f"  - {w['name']} ({w['url']})")
    
    if avatars:
        print("\n👤 角色示例 (前3名):")
        for a in avatars[:3]:
            print(f"  - {a['name']} ({a['url']})")


if __name__ == "__main__":
    asyncio.run(main())
