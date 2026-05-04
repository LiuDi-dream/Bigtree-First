import asyncio
import json
import re
from playwright.async_api import async_playwright
from typing import Dict, List, Any, Tuple


def parse_quantity(qty_text: str) -> int:
    """将数量文本转换为数字，支持 K/M 后缀"""
    if not qty_text or not isinstance(qty_text, str):
        return 0
    
    qty_text = qty_text.strip().upper()
    
    # 移除不相关的文本，只保留数字和单位
    match = re.search(r'(\d+\.?\d*)\s*([KM]?)', qty_text)
    if not match:
        return 0
    
    value = float(match.group(1))
    unit = match.group(2)
    
    if unit == 'K':
        value *= 1000
    elif unit == 'M':
        value *= 1000000
    
    return int(value)


async def scrape_baike_materials(character_id: int, character_name: str, proxy_url: str = "http://127.0.0.1:7890") -> Dict[str, Any]:
    """
    从米游社百科爬取角色的分段升级材料和天赋材料
    
    Args:
        character_id: 米游社百科的内容ID（从URL获取）
        character_name: 角色中文名
        proxy_url: 代理地址
    
    Returns:
        {
            "ascension_materials": [
                {
                    "tier": 1,
                    "level_range": "1-20",
                    "materials": [{"name": "...", "quantity": 123}, ...]
                },
                ...
            ],
            "talent_materials": [
                {
                    "talent_type": "普通攻击",
                    "materials": [{"name": "...", "quantity": 123}, ...]
                },
                ...
            ],
            "ascension_bosses": [
                {"name": "...", "domain": "...", "description": "..."},
                ...
            ]
        }
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy_url}
        )
        page = await browser.new_page()
        
        url = f"https://baike.mihoyo.com/ys/obc/content/{character_id}/detail?bbs_presentation_style=no_header&visit_device=pc"
        
        try:
            print(f"📖 正在爬取: {character_name} (ID: {character_id})")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 提取完整的材料数据
            material_data = await page.evaluate(r'''
                () => {
                    const result = {
                        all_tables: [],
                        ascension_table_indices: []
                    };
                    
                    // 提取所有表格，保留完整的结构
                    const allTables = document.querySelectorAll('table');
                    
                    allTables.forEach((table, tableIdx) => {
                        const rows = table.querySelectorAll('tr');
                        if (rows.length < 2) return;
                        
                        const tableText = table.textContent || '';
                        const tableData = [];
                        
                        // 提取所有行和列
                        rows.forEach((row) => {
                            const cells = Array.from(row.querySelectorAll('td, th')).map(cell => {
                                // 保留完整的单元格文本，包含数字和所有信息
                                return cell.textContent?.trim() || '';
                            });
                            
                            // 只保存非空行
                            const rowText = cells.join('|');
                            if (rowText.trim()) {
                                tableData.push(cells);
                            }
                        });
                        
                        if (tableData.length > 1) {
                            result.all_tables.push({
                                index: tableIdx,
                                rows: tableData,
                                full_text: tableText.substring(0, 300)
                            });
                            
                            // 标记升级/突破材料表格
                            if (tableText.includes('突破') || tableText.includes('升级')) {
                                result.ascension_table_indices.push(tableIdx);
                            }
                        }
                    });
                    
                    return result;
                }
            ''')
            
            await browser.close()
            
            # 返回原始表格数据
            return {
                "all_tables": material_data.get('all_tables', []),
                "ascension_table_indices": material_data.get('ascension_table_indices', [])
            }
            
        except Exception as e:
            print(f"  ❌ 错误: {str(e)[:100]}")
            await browser.close()
            return {
                "error": str(e)[:200],
                "ascension_materials": [],
                "talent_materials": []
            }


async def parse_level_material_table(table_data: List[List[str]]) -> Dict[str, Any]:
    """
    解析升级材料表格，提取分段升级材料
    表格格式通常是:
    | 突破等阶 | 所需等级 | 所需材料 |
    | 第1阶 | Lv.20 | 材料... |
    | 第2阶 | Lv.40 | 材料... |
    等等
    """
    if not table_data or len(table_data) < 2:
        return {}
    
    result = {
        "tiers": []
    }
    
    # 处理每一行
    for row_idx, row in enumerate(table_data):
        if row_idx == 0:  # 跳过标题行
            continue
        
        if not row:
            continue
        
        # 查找包含等级信息的行
        row_text = ' '.join(str(cell) for cell in row)
        
        # 检查是否包含等级信息
        if 'Lv' in row_text or '等级' in row_text or '突破' in row_text:
            # 这一行可能包含等级和材料信息
            tier_info = {
                "raw_row": row,
                "level_info": "",
                "materials": []
            }
            
            # 提取等级信息
            level_match = re.search(r'Lv\.?\s*(\d+)', row_text)
            if level_match:
                tier_info["level_info"] = level_match.group(0)
            
            result["tiers"].append(tier_info)
    
    return result


async def main():
    """测试爬虫"""
    # 导入解析器（同目录）
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from baike_table_parser import extract_ascension_materials, parse_baike_character_materials
    
    # 测试角色: 林尼 (ID: 508198)
    test_cases = [
        (508198, "林尼"),
    ]
    
    proxy = "http://127.0.0.1:7890"
    
    for char_id, char_name in test_cases:
        data = await scrape_baike_materials(char_id, char_name, proxy)
        
        print(f"\n📊 {char_name} 原始表格数据:")
        print(f"  总表格数: {len(data.get('all_tables', []))}")
        print(f"  升级材料表格索引: {data.get('ascension_table_indices', [])}")
        
        # 显示所有表格的摘要
        for table in data.get('all_tables', [])[:5]:
            print(f"\n  表格 {table['index']}:")
            print(f"    行数: {len(table['rows'])}")
            print(f"    首行: {' | '.join(table['rows'][0][:3])}")
            if len(table['rows']) > 1:
                print(f"    次行: {' | '.join(table['rows'][1][:3])}")
        
        # 使用解析器处理升级材料
        if data.get('all_tables'):
            print(f"\n📈 升级材料分析:")
            for idx in data.get('ascension_table_indices', [])[:1]:
                for table in data.get('all_tables', []):
                    if table['index'] == idx:
                        tiers = extract_ascension_materials(table['rows'])
                        print(f"  找到 {len(tiers)} 个升级阶段:")
                        for tier in tiers:
                            if tier.get('materials'):
                                mats = ', '.join([f"{name}x{qty}" for name, qty in tier['materials'].items()])
                                print(f"    Lv.{tier.get('level')}: {mats}")


if __name__ == "__main__":
    asyncio.run(main())
