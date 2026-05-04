"""
从米游社百科爬虫提取的表格数据中解析升级材料信息
"""
import re
from typing import List, Dict, Any


def parse_material_row(row_text: str) -> Dict[str, int]:
    """
    从材料行解析材料名称和数量
    格式例如: "坚牢黄玉碎屑 *1 空羽蛾 *3 磨损的执凭 *3"
    或: "坚牢黄玉碎屑*1 空羽蛾*3 磨损的执凭*3"
    """
    materials = {}
    
    # 移除多余空格
    row_text = row_text.strip()
    
    # 尝试分割模式1: "名称 *数字"
    pattern1 = r'([^*\d]+?)\s*\*\s*(\d+)'
    matches = re.findall(pattern1, row_text)
    
    for name, qty in matches:
        name = name.strip()
        if name and name not in ['突破材料', '升级材料', '天赋材料', '天赋升级']:
            materials[name] = int(qty)
    
    return materials


def extract_ascension_materials(table_data: List[List[str]]) -> List[Dict[str, Any]]:
    """
    从升级/突破材料表格中提取分段材料信息
    
    表格结构通常如下:
    | 突破等阶 | 所需等级 | 所需材料 | 摩拉消耗 |
    | - | Lv.20 | 材料... | 数字 |
    | - | Lv.40 | 材料... | 数字 |
    """
    
    result = []
    
    # 找到"所需等级"列的索引
    header_row = table_data[0] if table_data else []
    level_col_idx = -1
    material_col_idx = -1
    
    for idx, header in enumerate(header_row):
        header_text = str(header).strip()
        if '等级' in header_text or 'Lv' in header_text:
            level_col_idx = idx
        if '材料' in header_text or '所需' in header_text:
            material_col_idx = idx
    
    # 如果找不到明确的列，使用启发式方法
    if level_col_idx == -1:
        # 通常第2列是等级
        level_col_idx = 1 if len(header_row) > 1 else 0
    
    if material_col_idx == -1:
        # 通常第3列是材料
        material_col_idx = 2 if len(header_row) > 2 else 1
    
    # 处理数据行
    for row_idx, row in enumerate(table_data[1:], 1):
        if len(row) <= max(level_col_idx, material_col_idx):
            continue
        
        level_text = str(row[level_col_idx]).strip() if level_col_idx >= 0 else ""
        material_text = str(row[material_col_idx]).strip() if material_col_idx >= 0 else ""
        
        # 检查是否包含等级信息
        level_match = re.search(r'Lv\.?\s*(\d+)', level_text)
        if not level_match and not re.search(r'Lv\.?\s*(\d+)', material_text):
            continue
        
        # 提取等级
        level = None
        if level_match:
            level = int(level_match.group(1))
        else:
            level_match = re.search(r'Lv\.?\s*(\d+)', material_text)
            if level_match:
                level = int(level_match.group(1))
        
        # 解析材料
        materials = parse_material_row(material_text)
        
        if materials or level:
            result.append({
                "level": level,
                "level_text": level_text,
                "materials": materials,
                "raw_material_text": material_text
            })
    
    return result


def parse_baike_character_materials(tables: List[List[List[str]]]) -> Dict[str, Any]:
    """
    从所有表格中提取角色的升级、天赋等材料信息
    """
    
    result = {
        "ascension_materials": {},  # 按等级组织的突破材料
        "talent_materials": [],      # 天赋升级材料
        "total_ascending_cost": {},  # 升到90级需要的总材料数
        "raw_tables": []
    }
    
    for table_idx, table in enumerate(tables):
        if not table:
            continue
        
        table_text = ' '.join([' '.join(str(cell) for cell in row) for row in table])
        
        # 检查是否是升级/突破材料表格
        if '突破材料' in table_text or ('等级' in table_text and '材料' in table_text):
            
            # 提取分段升级材料
            tiers = extract_ascension_materials(table)
            
            if tiers:
                result["ascension_materials"][table_idx] = tiers
                result["raw_tables"].append({
                    "index": table_idx,
                    "type": "ascension",
                    "tiers": tiers
                })
        
        # 检查是否是天赋材料表格
        if '天赋' in table_text and '材料' in table_text:
            # 从这个表格提取天赋材料
            talent_materials = []
            for row in table[1:]:  # 跳过标题
                row_text = ' '.join(str(cell) for cell in row)
                materials = parse_material_row(row_text)
                if materials:
                    talent_materials.extend(list(materials.keys()))
            
            if talent_materials:
                result["talent_materials"].extend(list(set(talent_materials)))
    
    # 计算升到90级的总材料消耗
    total_cost = {}
    for tiers_by_table in result["ascension_materials"].values():
        for tier in tiers_by_table:
            for mat_name, qty in tier.get("materials", {}).items():
                total_cost[mat_name] = total_cost.get(mat_name, 0) + qty
    
    result["total_ascending_cost"] = total_cost
    
    return result


# 测试
if __name__ == "__main__":
    # 示例表格数据（从baike_material_scraper提取）
    sample_table = [
        ['突破等阶', '所需等级', '所需材料', '摩拉消耗'],
        ['-', 'Lv.20', '坚牢黄玉碎屑 *1 空羽蛾 *3', '1000'],
        ['-', 'Lv.40', '坚牢黄玉断片 *3 空羽蛾 *10', '4000'],
    ]
    
    tiers = extract_ascension_materials(sample_table)
    print("提取的升级材料层级:")
    for tier in tiers:
        print(f"  Lv.{tier.get('level')}: {tier.get('materials')}")
    
    # 测试材料解析
    test_text = "坚牢黄玉碎屑 *1 空羽蛾 *3 磨损的执凭 *3"
    materials = parse_material_row(test_text)
    print(f"\n解析结果: {materials}")
