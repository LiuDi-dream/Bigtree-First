#!/usr/bin/env python3
"""
BOSS掉落物品提取助手
用于从米游社百科页面中提取敌首（BOSS）的掉落物品

使用方法:
1. 在浏览器中打开敌人详情页面：
   https://baike.mihoyo.com/ys/obc/content/{ID}/detail?bbs_presentation_style=no_header&visit_device=pc

2. 运行此脚本并按照提示输入BOSS信息

3. 脚本会保存到 memory/boss_drops_dict.json
"""

import json
import os
from boss_drop_scraper import load_boss_drops, save_boss_drops

def interactive_add_boss():
    """交互式添加BOSS信息"""
    print("\n" + "="*60)
    print("BOSS掉落物品提取助手")
    print("="*60)
    
    boss_dict = load_boss_drops()
    
    while True:
        print("\n选项:")
        print("  1. 添加新BOSS")
        print("  2. 查看所有BOSS")
        print("  3. 删除BOSS")
        print("  4. 修改BOSS掉落物品")
        print("  5. 导出JSON")
        print("  0. 退出")
        
        choice = input("\n请选择 (0-5): ").strip()
        
        if choice == "1":
            add_new_boss(boss_dict)
        elif choice == "2":
            view_all_bosses(boss_dict)
        elif choice == "3":
            delete_boss(boss_dict)
        elif choice == "4":
            modify_boss(boss_dict)
        elif choice == "5":
            export_json(boss_dict)
        elif choice == "0":
            print("\n保存并退出...")
            save_boss_drops(boss_dict)
            break
        else:
            print("❌ 无效选择")

def add_new_boss(boss_dict):
    """添加新BOSS"""
    print("\n--- 添加新BOSS ---")
    name = input("输入BOSS名称: ").strip()
    
    if name in boss_dict:
        print(f"⚠️  BOSS '{name}' 已存在")
        return
    
    print("输入掉落物品 (多个物品用逗号分隔，如: 摩拉, 禁咒绘卷, 导能绘卷)")
    drops_input = input("掉落物品: ").strip()
    
    drops = [d.strip() for d in drops_input.split(',') if d.strip()]
    
    if not drops:
        print("❌ 未输入任何物品")
        return
    
    boss_dict[name] = drops
    save_boss_drops(boss_dict)
    print(f"✅ 已添加 {name}: {len(drops)} 种材料")
    print(f"   材料: {', '.join(drops)}")

def view_all_bosses(boss_dict):
    """查看所有BOSS"""
    print("\n--- 所有BOSS及掉落物品 ---")
    
    if not boss_dict:
        print("⚠️  暂无BOSS数据")
        return
    
    for idx, (name, drops) in enumerate(sorted(boss_dict.items()), 1):
        print(f"\n{idx}. {name}")
        print(f"   掉落物品数: {len(drops)}")
        
        # 分组显示（每行5个）
        for i in range(0, len(drops), 5):
            materials = drops[i:i+5]
            print(f"   - {', '.join(materials)}")

def delete_boss(boss_dict):
    """删除BOSS"""
    print("\n--- 删除BOSS ---")
    name = input("输入要删除的BOSS名称: ").strip()
    
    if name not in boss_dict:
        print(f"❌ 未找到BOSS '{name}'")
        return
    
    confirm = input(f"确认删除 '{name}' ? (y/n): ").strip().lower()
    
    if confirm == 'y':
        del boss_dict[name]
        save_boss_drops(boss_dict)
        print(f"✅ 已删除 {name}")
    else:
        print("取消操作")

def modify_boss(boss_dict):
    """修改BOSS掉落物品"""
    print("\n--- 修改BOSS掉落物品 ---")
    name = input("输入要修改的BOSS名称: ").strip()
    
    if name not in boss_dict:
        print(f"❌ 未找到BOSS '{name}'")
        return
    
    print(f"\n当前掉落物品:")
    for i, drop in enumerate(boss_dict[name], 1):
        print(f"  {i}. {drop}")
    
    print("\n选项:")
    print("  1. 添加新物品")
    print("  2. 移除物品")
    print("  3. 替换全部物品")
    
    choice = input("请选择 (1-3): ").strip()
    
    if choice == "1":
        new_item = input("输入新物品名称: ").strip()
        if new_item and new_item not in boss_dict[name]:
            boss_dict[name].append(new_item)
            boss_dict[name].sort()
            save_boss_drops(boss_dict)
            print(f"✅ 已添加 {new_item}")
        else:
            print("❌ 物品已存在或输入为空")
    
    elif choice == "2":
        item = input("输入要移除的物品名称: ").strip()
        if item in boss_dict[name]:
            boss_dict[name].remove(item)
            save_boss_drops(boss_dict)
            print(f"✅ 已移除 {item}")
        else:
            print(f"❌ 未找到物品 {item}")
    
    elif choice == "3":
        drops_input = input("输入新的掉落物品 (逗号分隔): ").strip()
        drops = [d.strip() for d in drops_input.split(',') if d.strip()]
        if drops:
            boss_dict[name] = sorted(drops)
            save_boss_drops(boss_dict)
            print(f"✅ 已更新 {name} 的掉落物品")

def export_json(boss_dict):
    """导出JSON"""
    print("\n--- 导出JSON ---")
    filepath = input("输入导出路径 (默认: memory/boss_drops_dict.json): ").strip()
    
    if not filepath:
        filepath = "memory/boss_drops_dict.json"
    
    try:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(boss_dict, f, ensure_ascii=False, indent=2)
        print(f"✅ 已导出到 {filepath}")
    except Exception as e:
        print(f"❌ 导出失败: {str(e)}")

if __name__ == "__main__":
    interactive_add_boss()
