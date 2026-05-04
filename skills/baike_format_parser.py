"""
针对米游社百科特定表格格式的材料解析器
"""
import re
from typing import List, Dict, Tuple, Any


def extract_materials_from_cell(cell_text: str) -> Dict[str, int]:
    """
    从单个单元格中提取材料信息
    格式: "材料名 *数字 材料名 *数字 ..."
    可能包含换行符和多余空格
    """
    materials = {}
    
    # 规范化文本：移除多余空格和换行符
    cell_text = ' '.join(cell_text.split())
    
    # 模式: "材料名 *数字" 或 "材料名*数字"
    pattern = r'([^*\d\n]+?)[\s]*\*[\s]*(\d+(?:\.\d+)?[KMkm]?)'
    matches = re.findall(pattern, cell_text)
    
    for name, qty in matches:
        name = name.strip()
        # 过滤掉无关的标签
        if name and name not in ['突破材料', '升级材料', '天赋', '摩拉'] and len(name) > 1:
            # 解析数量（支持K、M后缀）
            qty_value = float(qty)
            if qty.upper().endswith('K'):
                qty_value = int(float(qty[:-1]) * 1000)
            elif qty.upper().endswith('M'):
                qty_value = int(float(qty[:-1]) * 1000000)
            else:
                qty_value = int(qty_value)
            
            if name in materials:
                materials[name] += qty_value
            else:
                materials[name] = qty_value
    
    return materials


def parse_baike_ascension_table(table_rows: List[List[str]]) -> Dict[str, Any]:
    """
    解析米游社百科的升级/突破材料表格
    这个表格的特点是在行0的第2列有"摩拉消耗"和总材料信息
    后续行包含按阶段的升级材料信息
    """
    
    result = {
        "total_materials": {},  # 升到90需要的全部材料
        "tiers": [],            # 按阶段的升级材料
        "raw_data": table_rows
    }
    
    if len(table_rows) < 2:
        return result
    
    # 第一行是总材料和最终属性
    if len(table_rows[0]) > 1:
        total_cell = table_rows[0][1]  # 第二列通常包含总材料
        total_materials = extract_materials_from_cell(total_cell)
        result["total_materials"] = total_materials
    
    # 后续行是按等级的升级材料
    # 每行的结构: [等级信息, 材料信息, ...]
    for row_idx, row in enumerate(table_rows[1:], 1):
        if len(row) >= 2:
            level_cell = row[0]
            material_cell = row[1]
            
            # 提取等级信息（如"Lv.20", "突破前", "第1阶"等）
            level_match = re.search(r'Lv\.?\s*(\d+)', level_cell)
            level_num = None
            if level_match:
                level_num = int(level_match.group(1))
            
            # 提取材料信息
            materials = extract_materials_from_cell(material_cell)
            
            if materials or level_num:
                result["tiers"].append({
                    "index": row_idx - 1,
                    "level": level_num,
                    "level_text": level_cell.strip(),
                    "materials": materials
                })
    
    return result


def extract_baike_character_upgrade_path(all_tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    从所有表格中提取角色的完整升级路径
    """
    
    result = {
        "ascension_path": [],
        "total_cost": {},
        "talent_materials": {},
        "tables_analyzed": []
    }
    
    for table_info in all_tables:
        table_idx = table_info.get('index')
        table_rows = table_info.get('rows', [])
        
        if not table_rows:
            continue
        
        # 检查这是否是升级材料表格
        full_text = ' '.join([' '.join(row) for row in table_rows])
        
        if '突破' in full_text or ('升级' in full_text and '材料' in full_text):
            # 解析升级材料表格
            parsed = parse_baike_ascension_table(table_rows)
            
            if parsed.get('total_materials'):
                result["ascension_path"].append({
                    "table_index": table_idx,
                    "total_materials": parsed['total_materials'],
                    "tiers": parsed['tiers']
                })
                
                # 累计总消耗
                for mat, qty in parsed['total_materials'].items():
                    if '摩拉' in mat or mat == '摩拉':
                        continue  # 摩拉单独处理
                    result["total_cost"][mat] = result["total_cost"].get(mat, 0) + qty
                
                result["tables_analyzed"].append({
                    "index": table_idx,
                    "type": "ascension",
                    "tiers_count": len(parsed['tiers'])
                })
        
        # 检查天赋表格
        if '天赋' in full_text:
            # 提取天赋材料
            result["tables_analyzed"].append({
                "index": table_idx,
                "type": "talent"
            })
    
    return result


# 测试
if __name__ == "__main__":
    # 模拟从米游社百科提取的表格数据
    test_table = [
        ['突破材料', '坚牢黄玉碎屑 *1 空羽蛾 *3 磨损的执凭 *3 摩拉 *1000'],
        ['Lv.20', '坚牢黄玉碎屑 *1 空羽蛾 *3'],
        ['Lv.40', '坚牢黄玉断片 *3 空羽蛾 *10 磨损的执凭 *15'],
    ]
    
    result = parse_baike_ascension_table(test_table)
    print("升级材料解析结果:")
    print(f"  总消耗: {result['total_materials']}")
    print(f"  升级阶段数: {len(result['tiers'])}")
    for tier in result['tiers']:
        print(f"    {tier['level_text']}: {tier['materials']}")
    
    # 测试单元格提取
    test_cell = "坚牢黄玉碎屑 *1 空羽蛾 *3 磨损的执凭 *3 摩拉 *1000"
    materials = extract_materials_from_cell(test_cell)
    print(f"\n单元格提取: {materials}")
