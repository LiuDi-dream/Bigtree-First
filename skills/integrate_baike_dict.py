"""
从米游社百科爬虫获取数据，并与现有的game_dict整合
"""
import asyncio
import json
import os
from typing import Dict, List, Any


async def integrate_baike_data_with_game_dict(game_dict_path: str = "memory/game_dict_yatta.json"):
    """
    将米游社百科的升级材料数据整合到现有的game_dict中
    """
    from baike_material_scraper import scrape_baike_materials
    from baike_format_parser import extract_baike_character_upgrade_path
    
    # 加载现有的game_dict
    print("📖 正在加载现有game_dict...")
    if not os.path.exists(game_dict_path):
        print(f"❌ 文件不存在: {game_dict_path}")
        return None
    
    with open(game_dict_path, 'r', encoding='utf-8') as f:
        game_dict = json.load(f)
    
    avatars = game_dict.get('avatars', {})
    print(f"✓ 加载了 {len(avatars)} 个角色")
    
    # 米游社百科角色映射（英文名 -> 百科ID）
    # 这个映射需要根据实际情况建立
    # 示例：从URL https://baike.mihoyo.com/ys/obc/content/508198/... 可以得到508198
    baike_id_mapping = {
        "lyney": 508198,
        # 可以添加更多映射
    }
    
    proxy = "http://127.0.0.1:7890"
    updated_count = 0
    
    # 对每个有映射的角色，爬取其米游社百科数据
    for char_en_name, baike_id in baike_id_mapping.items():
        if char_en_name not in avatars:
            print(f"⚠️ 角色 {char_en_name} 未在game_dict中找到")
            continue
        
        char_data = avatars[char_en_name]
        char_zh_name = char_data.get('name_zh', char_en_name)
        
        print(f"\n🌐 正在爬取 {char_zh_name} 的米游社百科数据...")
        
        try:
            baike_data = await scrape_baike_materials(baike_id, char_zh_name, proxy)
            
            # 解析表格数据
            upgrade_path = extract_baike_character_upgrade_path(baike_data.get('all_tables', []))
            
            # 将升级路径信息添加到角色数据中
            if upgrade_path.get('ascension_path'):
                # 初始化结构
                if 'ascension_materials_detail' not in char_data:
                    char_data['ascension_materials_detail'] = {}
                
                # 添加升级材料信息
                for path in upgrade_path['ascension_path']:
                    char_data['ascension_materials_detail']['tiers'] = path.get('tiers', [])
                    char_data['ascension_materials_detail']['total_cost'] = path.get('total_materials', {})
                
                # 添加总消耗信息
                if upgrade_path.get('total_cost'):
                    char_data['ascension_total_cost'] = upgrade_path['total_cost']
                
                updated_count += 1
                print(f"  ✓ 成功添加升级材料数据 ({len(upgrade_path['ascension_path'])} 个表格)")
                
                # 显示样本数据
                if upgrade_path['total_cost']:
                    sample = list(upgrade_path['total_cost'].items())[:3]
                    print(f"    样本消耗: {sample}")
        
        except Exception as e:
            print(f"  ❌ 爬取失败: {str(e)[:100]}")
            continue
    
    # 保存更新后的game_dict
    if updated_count > 0:
        print(f"\n💾 正在保存更新后的game_dict...")
        output_path = game_dict_path.replace('.json', '_enhanced.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(game_dict, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存到 {output_path}")
        print(f"✓ 更新了 {updated_count} 个角色的材料数据")
    else:
        print("⚠️ 没有更新任何角色数据")
    
    return game_dict


async def main():
    """主函数"""
    print("=" * 60)
    print("🔄 米游社百科数据整合工具")
    print("=" * 60)
    
    # 首先运行爬虫获取一个角色的数据来演示
    print("\n📖 演示：爬取林尼的米游社百科数据...")
    from baike_material_scraper import scrape_baike_materials
    from baike_format_parser import extract_baike_character_upgrade_path
    
    data = await scrape_baike_materials(508198, "林尼", "http://127.0.0.1:7890")
    upgrade_path = extract_baike_character_upgrade_path(data.get('all_tables', []))
    
    print(f"\n✓ 成功爬取数据:")
    print(f"  - 表格数: {len(data.get('all_tables', []))}")
    print(f"  - 升级路径: {len(upgrade_path.get('ascension_path', []))}")
    print(f"  - 总材料成本: {len(upgrade_path.get('total_cost', {}))}")
    
    # 显示升级阶段详情
    for path in upgrade_path.get('ascension_path', [])[:1]:
        print(f"\n  升级阶段 (表格 {path['table_index']}):")
        for tier in path['tiers']:
            if tier['materials']:
                mats = ', '.join([f"{k}x{v}" for k, v in list(tier['materials'].items())[:3]])
                print(f"    {tier['level_text']}: {mats}")
    
    # 显示总消耗
    if upgrade_path.get('total_cost'):
        print(f"\n  升级到90级的总消耗 (前5项):")
        for mat, qty in list(upgrade_path['total_cost'].items())[:5]:
            print(f"    - {mat}: {qty}")
    
    # 现在可以集成到game_dict
    # print("\n正在集成到game_dict...")
    # await integrate_baike_data_with_game_dict()


if __name__ == "__main__":
    asyncio.run(main())
