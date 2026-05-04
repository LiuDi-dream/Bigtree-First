import asyncio
import json
from playwright.async_api import async_playwright

async def fetch_weapons_data():
    """从 yatta.moe 爬取武器数据（包含升级材料）"""
    print("📡 正在从 yatta.moe 爬取武器数据...")
    
    async with async_playwright() as p:
        # 尝试使用代理
        proxy_url = "http://127.0.0.1:7890"
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy_url}
        )
        page = await browser.new_page()
        
        
        # 等待页面渲染完成
        await page.wait_for_selector('[class*="weapon"]', timeout=10000)
        
        # 从页面中提取所有武器元素
        weapons_data = await page.evaluate('''
            () => {
                const weapons = [];
                // 查找所有武器卡片
                const elements = document.querySelectorAll('a[href*="/weapon/"]');
                
                elements.forEach(el => {
                    try {
                        const name = el.querySelector('[class*="name"]')?.textContent?.trim();
                        const rarity = el.querySelector('[class*="star"], [class*="rarity"]')?.textContent?.trim();
                        const type = el.querySelector('[class*="type"], [class*="weapon-type"]')?.textContent?.trim();
                        const href = el.getAttribute('href');
                        
                        if (name && href) {
                            weapons.push({
                                name: name,
                                rarity: rarity || '0',
                                type: type || 'unknown',
                                url: href
                            });
                        }
                    } catch (e) {}
                });
                
                return weapons;
            }
        ''')
        
        await browser.close()
        return weapons_data


async def fetch_avatars_data():
    """从 yatta.moe 爬取角色数据（包含升级材料）"""
    print("📡 正在从 yatta.moe 爬取角色数据...")
    
    async with async_playwright() as p:
        # 尝试使用代理
        proxy_url = "http://127.0.0.1:7890"
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy_url}
        )
        page = await browser.new_page()
        
        
        # 等待页面渲染完成
        await page.wait_for_selector('[class*="avatar"]', timeout=10000)
        
        # 从页面中提取所有角色元素
        avatars_data = await page.evaluate('''
            () => {
                const avatars = [];
                // 查找所有角色卡片
                const elements = document.querySelectorAll('a[href*="/avatar/"]');
                
                elements.forEach(el => {
                    try {
                        const name = el.querySelector('[class*="name"]')?.textContent?.trim();
                        const rarity = el.querySelector('[class*="star"], [class*="rarity"]')?.textContent?.trim();
                        const element = el.querySelector('[class*="element"], [class*="vision"]')?.textContent?.trim();
                        const href = el.getAttribute('href');
                        
                        if (name && href) {
                            avatars.push({
                                name: name,
                                rarity: rarity || '0',
                                element: element || 'unknown',
                                url: href
                            });
                        }
                    } catch (e) {}
                });
                
                return avatars;
            }
        ''')
        
        await browser.close()
        return avatars_data


async def fetch_weapon_details(weapon_url):
    """获取单个武器的详细信息（包含升级材料）"""
    async with async_playwright() as p:
        # 尝试使用代理
        proxy_url = "http://127.0.0.1:7890"
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy_url}
        )
        page = await browser.new_page()
        
        try:
            
            details = await page.evaluate('''
                () => {
                    const data = {};
                    
                    // 提取武器名称
                    data.name = document.querySelector('h1')?.textContent?.trim() || '';
                    
                    // 提取稀有度
                    const rarity = document.querySelectorAll('[class*="star"]').length;
                    data.rarity = rarity || 0;
                    
                    // 提取武器类型
                    data.type = document.querySelector('[class*="weapon-type"]')?.textContent?.trim() || 'unknown';
                    
                    // 提取升级材料
                    const materials = [];
                    document.querySelectorAll('[class*="material"], [class*="ascension"]').forEach(el => {
                        const mat = el.textContent?.trim();
                        if (mat && mat.length > 0 && mat.length < 50) {
                            materials.push(mat);
                        }
                    });
                    data.materials = [...new Set(materials)].slice(0, 10); // 去重，最多10个
                    
                    return data;
                }
            ''')
            
            await browser.close()
            return details
        except Exception as e:
            await browser.close()
            return {"error": str(e)}


async def fetch_avatar_details(avatar_url):
    """获取单个角色的详细信息（包含升级材料）"""
    async with async_playwright() as p:
        # 尝试使用代理
        proxy_url = "http://127.0.0.1:7890"
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy_url}
        )
        page = await browser.new_page()
        
        try:
            
            details = await page.evaluate('''
                () => {
                    const data = {};
                    
                    // 提取角色名称
                    data.name = document.querySelector('h1')?.textContent?.trim() || '';
                    
                    // 提取稀有度
                    const rarity = document.querySelectorAll('[class*="star"]').length;
                    data.rarity = rarity || 0;
                    
                    // 提取元素
                    data.element = document.querySelector('[class*="element"], [class*="vision"]')?.textContent?.trim() || 'unknown';
                    
                    // 提取升级材料
                    const materials = [];
                    document.querySelectorAll('[class*="material"], [class*="ascension"], [class*="talent"]').forEach(el => {
                        const mat = el.textContent?.trim();
                        if (mat && mat.length > 0 && mat.length < 50) {
                            materials.push(mat);
                        }
                    });
                    data.materials = [...new Set(materials)].slice(0, 15); // 去重，最多15个
                    
                    return data;
                }
            ''')
            
            await browser.close()
            return details
        except Exception as e:
            await browser.close()
            return {"error": str(e)}


async def main():
    """主爬虫流程"""
    print("🔄 开始从 yatta.moe 爬取游戏数据...\n")
    
    # 爬取武器列表
    print("步骤 1: 爬取武器列表...")
    weapons_list = await fetch_weapons_data()
    print(f"✅ 找到 {len(weapons_list)} 件武器\n")
    
    # 爬取角色列表
    print("步骤 2: 爬取角色列表...")
    avatars_list = await fetch_avatars_data()
    print(f"✅ 找到 {len(avatars_list)} 名角色\n")
    
    # 爬取武器详情（仅前3个作为演示）
    print("步骤 3: 爬取武器详情（演示）...")
    weapons_full = {}
    for i, weapon in enumerate(weapons_list[:3]):
        print(f"  正在爬取: {weapon['name']}...")
        full_url = f"https://gi.yatta.moe{weapon['url']}" if weapon['url'].startswith('/') else weapon['url']
        details = await fetch_weapon_details(full_url)
        weapons_full[weapon['name']] = details
    print(f"✅ 武器详情爬取完成\n")
    
    # 爬取角色详情（仅前3个作为演示）
    print("步骤 4: 爬取角色详情（演示）...")
    avatars_full = {}
    for i, avatar in enumerate(avatars_list[:3]):
        print(f"  正在爬取: {avatar['name']}...")
        full_url = f"https://gi.yatta.moe{avatar['url']}" if avatar['url'].startswith('/') else avatar['url']
        details = await fetch_avatar_details(full_url)
        avatars_full[avatar['name']] = details
    print(f"✅ 角色详情爬取完成\n")
    
    # 保存结果
    result = {
        "weapons": {w['name']: w for w in weapons_list},
        "avatars": {a['name']: a for a in avatars_list},
        "weapons_detailed": weapons_full,
        "avatars_detailed": avatars_full,
    }
    
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    
    # 保存到文件
    import os
    os.makedirs("memory", exist_ok=True)
    
    with open("memory/yatta_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("📊 数据已保存到 memory/yatta_data.json")
    print(f"  - 武器总数: {len(result['weapons'])}")
    print(f"  - 角色总数: {len(result['avatars'])}")
    print(f"  - 详细信息：武器 {len(result['weapons_detailed'])} 件，角色 {len(result['avatars_detailed'])} 名")
