#!/usr/bin/env python3
"""
完整BOSS敌首掉落素材爬虫
1. 首先滚动BOSS列表页面，加载所有BOSS
2. 收集所有BOSS的ID和名称
3. 逐个访问详情页面提取掉落物品
"""

import json
import asyncio
import time
from typing import Dict, List, Tuple, Set
import os
import sys

async def collect_all_bosses_from_list():
    """
    访问BOSS列表页面，通过滚动加载所有BOSS
    返回 [(id, name), ...] 列表
    """
    from playwright.async_api import async_playwright
    
    boss_set: Set[Tuple[int, str]] = set()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("🌐 正在访问BOSS列表页面...")
        try:
            url = "https://baike.mihoyo.com/ys/obc/channel/map/189/6"
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print("✅ 页面加载成功")
        except Exception as e:
            print(f"❌ 页面加载失败: {e}")
            await browser.close()
            return []
        
        # 等待页面稳定
        await page.wait_for_timeout(2000)
        
        # 获取初始BOSS数量
        initial_count = 0
        try:
            initial_count = await page.evaluate("() => document.querySelectorAll('a[href*=\"/ys/obc/content/\"]').length")
            print(f"📋 初始加载的BOSS数: {initial_count}")
        except Exception as e:
            print(f"⚠️  无法获取初始BOSS数: {e}")
        
        # 不断滚动页面，直到没有新BOSS加载
        last_count = 0
        scroll_count = 0
        max_scrolls = 100
        
        print("\n📜 开始滚动加载BOSS...")
        
        while scroll_count < max_scrolls:
            # 获取当前页面上所有的BOSS链接
            try:
                boss_links = await page.evaluate("""
                    () => {
                        const links = document.querySelectorAll('a[href*="/ys/obc/content/"]');
                        const bosses = [];
                        for (let link of links) {
                            const href = link.getAttribute('href');
                            // 提取ID和名称
                            const match = href.match(/\\/content\\/(\\d+)\\/detail/);
                            if (match) {
                                const id = parseInt(match[1]);
                                const name = link.textContent?.trim();
                                if (name && id && name !== '加载中') {
                                    bosses.push({id, name});
                                }
                            }
                        }
                        return bosses;
                    }
                """)
                
                # 去重并添加到集合
                for boss in boss_links:
                    boss_set.add((boss['id'], boss['name']))
                
                current_count = len(boss_set)
                
                if current_count != last_count:
                    print(f"  [{scroll_count}] 当前BOSS总数: {current_count}")
                    last_count = current_count
                
            except Exception as e:
                print(f"  ⚠️  提取BOSS失败: {e}")
            
            # 滚动页面
            try:
                await page.evaluate("() => window.scrollBy(0, 500)")
                await page.wait_for_timeout(500)  # 等待内容加载
                scroll_count += 1
            except Exception as e:
                print(f"  ⚠️  滚动失败: {e}")
                break
            
            # 检查是否还有更多内容要加载
            # 如果5次滚动都没有新BOSS，则认为已全部加载
            if current_count == last_count and scroll_count > 5:
                consecutive_no_change = 0
                temp_count = current_count
                
                for _ in range(5):
                    await page.evaluate("() => window.scrollBy(0, 500)")
                    await page.wait_for_timeout(300)
                    
                    try:
                        boss_links = await page.evaluate("""
                            () => {
                                const links = document.querySelectorAll('a[href*="/ys/obc/content/"]');
                                const bosses = [];
                                for (let link of links) {
                                    const href = link.getAttribute('href');
                                    const match = href.match(/\\/content\\/(\\d+)\\/detail/);
                                    if (match) {
                                        const id = parseInt(match[1]);
                                        const name = link.textContent?.trim();
                                        if (name && id && name !== '加载中') {
                                            bosses.push({id, name});
                                        }
                                    }
                                }
                                return bosses;
                            }
                        """)
                        
                        for boss in boss_links:
                            boss_set.add((boss['id'], boss['name']))
                        
                        if len(boss_set) == temp_count:
                            consecutive_no_change += 1
                        else:
                            temp_count = len(boss_set)
                            consecutive_no_change = 0
                    except:
                        pass
                
                if consecutive_no_change >= 5:
                    print(f"\n✅ 已加载所有BOSS，共计: {len(boss_set)} 个")
                    break
        
        await browser.close()
    
    # 排序并返回
    boss_list = sorted(list(boss_set), key=lambda x: x[0], reverse=True)
    return boss_list


async def scrape_boss_drops(boss_id: int, boss_name: str):
    """
    爬取单个BOSS的掉落物品
    """
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            url = f"https://baike.mihoyo.com/ys/obc/content/{boss_id}/detail?bbs_presentation_style=no_header&visit_device=pc"
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(1000)
            
            # 提取掉落物品
            drops = await page.evaluate("""
                () => {
                    const result = [];
                    
                    // 查找所有包含"掉落"的单元格
                    const cells = document.querySelectorAll('td');
                    for (let i = 0; i < cells.length; i++) {
                        if (cells[i].textContent?.includes('掉落')) {
                            // 找到该行的下一个单元格
                            const row = cells[i].closest('tr');
                            if (row) {
                                const allCells = row.querySelectorAll('td');
                                if (allCells.length >= 2) {
                                    const dropCell = allCells[1];
                                    // 查找所有列表项和链接
                                    const items = dropCell.querySelectorAll('li, a');
                                    items.forEach(item => {
                                        const text = item.textContent?.trim();
                                        if (text && !text.match(/^\\d+$/) && text !== '无') {
                                            const clean = text.replace(/\\s*\\d+\\s*$/, '').trim();
                                            if (clean && clean.length > 0 && !result.includes(clean)) {
                                                result.push(clean);
                                            }
                                        }
                                    });
                                }
                            }
                            break;
                        }
                    }
                    
                    return result;
                }
            """)
            
            return (boss_name, drops if drops else [])
            
        except Exception as e:
            print(f"    ⚠️  提取失败: {e}")
            return (boss_name, [])
        finally:
            await browser.close()


async def scrape_all_drops(boss_list: List[Tuple[int, str]]):
    """
    逐个爬取所有BOSS的掉落物品
    使用单个浏览器实例以提高效率
    """
    from playwright.async_api import async_playwright
    
    boss_dict = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"\n🚀 开始爬取 {len(boss_list)} 个BOSS的掉落物品...\n")
        
        for idx, (boss_id, boss_name) in enumerate(boss_list, 1):
            print(f"[{idx:3d}/{len(boss_list)}] {boss_name}", end=" ")
            sys.stdout.flush()
            
            try:
                url = f"https://baike.mihoyo.com/ys/obc/content/{boss_id}/detail?bbs_presentation_style=no_header&visit_device=pc"
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(800)
                
                # 提取掉落物品
                drops = await page.evaluate("""
                    () => {
                        const result = [];
                        
                        const cells = document.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].textContent?.includes('掉落')) {
                                const row = cells[i].closest('tr');
                                if (row) {
                                    const allCells = row.querySelectorAll('td');
                                    if (allCells.length >= 2) {
                                        const dropCell = allCells[1];
                                        const items = dropCell.querySelectorAll('li, a');
                                        items.forEach(item => {
                                            const text = item.textContent?.trim();
                                            if (text && !text.match(/^\\d+$/) && text !== '无' && text !== '暂无') {
                                                const clean = text.replace(/\\s*\\d+\\s*$/, '').trim();
                                                if (clean && clean.length > 0 && !result.includes(clean)) {
                                                    result.push(clean);
                                                }
                                            }
                                        });
                                    }
                                }
                                break;
                            }
                        }
                        
                        return result;
                    }
                """)
                
                if drops:
                    boss_dict[boss_name] = drops
                    print(f"✅ ({len(drops)} 种掉落)")
                else:
                    print(f"⚠️  (未找到掉落)")
                
            except Exception as e:
                print(f"❌ ({str(e)[:30]})")
            
            # 间隔延迟
            if idx < len(boss_list):
                await page.wait_for_timeout(500)
        
        await browser.close()
    
    return boss_dict


async def main():
    """
    主函数
    """
    print("=" * 70)
    print("🔄 BOSS敌首完整掉落素材爬虫 v3.0")
    print("=" * 70)
    print()
    
    # 第一步：收集所有BOSS
    print("📍 第一步: 从列表页收集所有BOSS\n")
    boss_list = await collect_all_bosses_from_list()
    
    if not boss_list:
        print("\n❌ 无法获取BOSS列表，请检查网络连接")
        return
    
    print(f"\n✅ 成功收集 {len(boss_list)} 个BOSS")
    
    # 第二步：爬取所有BOSS的掉落物品
    print("\n📍 第二步: 爬取所有BOSS的掉落物品\n")
    boss_dict = await scrape_all_drops(boss_list)
    
    # 保存到JSON文件
    output_path = "memory/boss_drops_dict.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(boss_dict, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    print(f"\n" + "=" * 70)
    print("✅ 爬虫完成！")
    print("=" * 70)
    print(f"\n📊 统计信息:")
    print(f"  • 成功爬取: {len(boss_dict)} 个BOSS")
    total_drops = sum(len(drops) for drops in boss_dict.values())
    print(f"  • 总掉落物品种类: {total_drops}")
    if boss_dict:
        print(f"  • 平均每个BOSS: {total_drops / len(boss_dict):.1f} 种")
    print(f"\n  • 已保存到: {output_path}")
    
    # 打印前15个BOSS
    print(f"\n📋 数据预览 (前15个BOSS):")
    for i, (name, drops) in enumerate(list(boss_dict.items())[:15], 1):
        print(f"\n  {i:2d}. {name}")
        print(f"      掉落数: {len(drops)}")
        if drops:
            print(f"      物品: {', '.join(drops[:4])}{'...' if len(drops) > 4 else ''}")
    
    if len(boss_dict) > 15:
        print(f"\n  ... 还有 {len(boss_dict) - 15} 个BOSS")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断爬虫")
    except Exception as e:
        print(f"\n❌ 爬虫运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
