import json
import os
from typing import Dict, List, Optional
import re


# BOSS掉落物品字典 - 从百科页面手工整理
# 包含BOSS名称和其掉落的所有素材
BOSS_DROPS_DICT = {
    "丘尔德里克": ["摩拉", "禁咒绘卷", "封魔绘卷", "导能绘卷", "不祥的面具", "污秽的面具", "破损的面具"],
    "深黯魇语之主": ["冒险阅历", "角色经验", "摩拉", "好感经验", "魇翼枯骸", "最胜紫晶", "最胜紫晶块", "最胜紫晶断片", "最胜紫晶碎屑", "角斗士的终幕礼", "流浪大地的乐团", "教官", "流放者", "祭雷之人", "游医"],
}

def load_boss_drops() -> Dict[str, List[str]]:
    """加载BOSS掉落物品字典"""
    dict_path = "memory/boss_drops_dict.json"
    
    if os.path.exists(dict_path):
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  加载字典失败: {str(e)}")
            return BOSS_DROPS_DICT.copy()
    
    return BOSS_DROPS_DICT.copy()

def save_boss_drops(boss_dict: Dict[str, List[str]]) -> None:
    """保存BOSS掉落物品字典"""
    dict_path = "memory/boss_drops_dict.json"
    os.makedirs(os.path.dirname(dict_path), exist_ok=True)
    
    try:
        with open(dict_path, 'w', encoding='utf-8') as f:
            json.dump(boss_dict, f, ensure_ascii=False, indent=2)
        print(f"✅ 字典已保存到: {dict_path}")
    except Exception as e:
        print(f"❌ 保存失败: {str(e)}")

def add_boss_drops(boss_name: str, drops: List[str]) -> None:
    """添加一个BOSS的掉落物品"""
    boss_dict = load_boss_drops()
    boss_dict[boss_name] = sorted(list(set(drops)))  # 去重并排序
    save_boss_drops(boss_dict)
    print(f"✅ 已添加 {boss_name}: {len(drops)} 种材料")

def get_all_boss_drops() -> Dict[str, List[str]]:
    """获取所有BOSS的掉落物品"""
    return load_boss_drops()

def print_boss_drops_summary() -> None:
    """打印BOSS掉落物品摘要"""
    boss_dict = load_boss_drops()
    print(f"\n📊 BOSS掉落物品统计:")
    print(f"  共找到 {len(boss_dict)} 个BOSS")
    
    if len(boss_dict) > 0:
        for name, drops in list(boss_dict.items())[:5]:
            print(f"\n  {name}:")
            for drop in drops[:5]:
                print(f"    - {drop}")
            if len(drops) > 5:
                print(f"    ... 还有 {len(drops) - 5} 个材料")
    
    if len(boss_dict) > 5:
        print(f"\n  ... 还有 {len(boss_dict) - 5} 个BOSS")


if __name__ == "__main__":
    # 初始化字典
    save_boss_drops(BOSS_DROPS_DICT)
    
    # 打印摘要
    print_boss_drops_summary()
    
    # 演示添加新BOSS
    print("\n\n演示添加新BOSS:")
    add_boss_drops("摩诃婆苏提婆耶弗太子", ["摩拉", "禁咒绘卷", "导能绘卷", "炽烈的花蜜"])
    
    # 再次打印摘要
    print_boss_drops_summary()
