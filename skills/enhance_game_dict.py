"""
最终的game_dict增强脚本 - 添加升级材料、天赋材料和副本信息
"""
import json
import os
from typing import Dict, Any


def enhance_game_dict_with_baike_data(game_dict_path: str = "memory/game_dict_yatta.json") -> Dict[str, Any]:
    """
    使用米游社百科数据增强game_dict
    
    新增字段：
    - ascension_materials_detail: 分段升级材料
    - ascension_total_cost: 升到90级的全部材料
    - talent_materials: 天赋升级材料及来源
    - domain_info: 副本/秘境信息
    """
    
    # 基于米游社百科页面（莉奈娅，content/508198）提取的数据
    # 页面：角色突破表 + 天赋页签下的技能倍率表「升级材料」行
    linnea_upgrade_cost = {
        "坚牢黄玉碎屑": 2,
        "坚牢黄玉断片": 9,
        "坚牢黄玉块": 9,
        "坚牢黄玉": 6,
        "堕天的落羽": 46,
        "空羽蛾": 168,
        "磨损的执凭": 18,
        "精致的执凭": 30,
        "霜镌的执凭": 36,
        "摩拉": 2092530
    }
    
    linnea_talent_upgrade_steps = [
        {
            "level": "1->2",
            "materials": {
                "「浪迹」的教导": 3,
                "磨损的执凭": 6
            }
        },
        {
            "level": "2->3",
            "materials": {
                "「浪迹」的指引": 2,
                "精致的执凭": 3
            }
        },
        {
            "level": "3->4",
            "materials": {
                "「浪迹」的指引": 4,
                "精致的执凭": 4
            }
        },
        {
            "level": "4->5",
            "materials": {
                "「浪迹」的指引": 6,
                "精致的执凭": 6
            }
        },
        {
            "level": "5->6",
            "materials": {
                "「浪迹」的指引": 9,
                "精致的执凭": 9
            }
        },
        {
            "level": "6->7",
            "materials": {
                "「浪迹」的哲学": 4,
                "霜镌的执凭": 4,
                "异端的瓶剂": 1
            }
        },
        {
            "level": "7->8",
            "materials": {
                "「浪迹」的哲学": 6,
                "霜镌的执凭": 6,
                "异端的瓶剂": 1
            }
        },
        {
            "level": "8->9",
            "materials": {
                "「浪迹」的哲学": 12,
                "霜镌的执凭": 9,
                "异端的瓶剂": 2
            }
        },
        {
            "level": "9->10",
            "materials": {
                "「浪迹」的哲学": 16,
                "霜镌的执凭": 12,
                "异端的瓶剂": 2,
                "智识之冕": 1
            }
        }
    ]
    
    # 加载game_dict
    print("📖 正在加载game_dict...")
    if not os.path.exists(game_dict_path):
        print(f"❌ 文件不存在: {game_dict_path}")
        return {}
    
    with open(game_dict_path, 'r', encoding='utf-8') as f:
        game_dict = json.load(f)
    
    avatars = game_dict.get('avatars', {})
    weapons = game_dict.get('weapons', {})
    
    print(f"✓ 加载了 {len(avatars)} 个角色和 {len(weapons)} 件武器")
    
    # 增强莉奈娅的数据
    if 'linnea' in avatars:
        linnea = avatars['linnea']
        
        # 添加升级材料信息
        linnea['ascension_materials_detail'] = {
            "description": "升级到90级的分段突破材料（米游社百科）",
            "tiers": [
                {
                    "tier": 1,
                    "level_range": "1-20",
                    "materials": {
                        "坚牢黄玉碎屑": 1,
                        "空羽蛾": 3,
                        "磨损的执凭": 3,
                        "摩拉": 6800
                    }
                },
                {
                    "tier": 2,
                    "level_range": "20-40",
                    "materials": {
                        "坚牢黄玉断片": 3,
                        "堕天的落羽": 2,
                        "空羽蛾": 10,
                        "磨损的执凭": 15,
                        "摩拉": 21400
                    }
                },
                {
                    "tier": 3,
                    "level_range": "40-50",
                    "materials": {
                        "坚牢黄玉断片": 6,
                        "堕天的落羽": 4,
                        "空羽蛾": 20,
                        "精致的执凭": 12,
                        "摩拉": 42800
                    }
                },
                {
                    "tier": 4,
                    "level_range": "50-60",
                    "materials": {
                        "坚牢黄玉块": 3,
                        "堕天的落羽": 8,
                        "空羽蛾": 30,
                        "精致的执凭": 18,
                        "摩拉": 64200
                    }
                },
                {
                    "tier": 5,
                    "level_range": "60-70",
                    "materials": {
                        "坚牢黄玉块": 6,
                        "堕天的落羽": 12,
                        "空羽蛾": 45,
                        "霜镌的执凭": 12,
                        "摩拉": 96300
                    }
                },
                {
                    "tier": 6,
                    "level_range": "70-80",
                    "materials": {
                        "坚牢黄玉": 6,
                        "堕天的落羽": 20,
                        "空羽蛾": 60,
                        "霜镌的执凭": 24,
                        "摩拉": 129200
                    }
                }
            ]
        }
        
        # 添加升级到满级的总消耗
        linnea['ascension_total_cost'] = {
            "description": "升级到Lv.90的全部材料消耗（米游社百科突破总览）",
            "materials": linnea_upgrade_cost
        }
        
        # 添加天赋材料（位置：天赋页签 -> 技能倍率表 -> 升级材料）
        linnea['talent_materials'] = {
            "description": "单天赋1->10升级材料（米游社百科天赋倍率表）",
            "upgrade_steps": linnea_talent_upgrade_steps,
            "key_materials": {
                "book_series": "「浪迹」",
                "enemy_drop_series": "执凭",
                "weekly_boss_material": "异端的瓶剂",
                "crown": "智识之冕"
            },
            "sources": {
                "「浪迹」的教导": {
                    "type": "秘境",
                    "domain_name": "无光的深都",
                    "domain_stage": "覆巢 I/II/III/IV",
                    "schedule": "周三、周六、周日"
                },
                "「浪迹」的指引": {
                    "type": "秘境",
                    "domain_name": "无光的深都",
                    "domain_stage": "覆巢 II/III/IV",
                    "schedule": "周三、周六、周日",
                    "extra": "可合成获得"
                },
                "「浪迹」的哲学": {
                    "type": "秘境",
                    "domain_name": "无光的深都",
                    "domain_stage": "覆巢 IV",
                    "schedule": "周三、周六、周日",
                    "extra": "可合成获得"
                },
                "磨损的执凭": {
                    "type": "敌人掉落",
                    "sources": [
                        "愚人众特辖队掉落",
                        "星尘兑换"
                    ]
                },
                "精致的执凭": {
                    "type": "敌人掉落",
                    "sources": [
                        "40级以上愚人众特辖队掉落",
                        "星尘兑换"
                    ]
                },
                "霜镌的执凭": {
                    "type": "敌人掉落",
                    "sources": [
                        "60级以上愚人众特辖队掉落",
                        "星辉兑换"
                    ]
                },
                "异端的瓶剂": {
                    "type": "周本材料",
                    "domain_name": "赝月的研究所",
                    "domain_stage": "追忆：异端者的黄昏 II/III/IV"
                }
            }
        }
        
        # 添加升级材料的来源信息
        linnea['ascension_material_sources'] = {
            "坚牢黄玉碎屑": {
                "type": "突破宝石",
                "sources": ["相关首领掉落", "合成转化"]
            },
            "坚牢黄玉断片": {
                "type": "突破宝石",
                "sources": ["相关首领掉落", "合成转化"]
            },
            "坚牢黄玉块": {
                "type": "突破宝石",
                "sources": ["相关首领掉落", "合成转化"]
            },
            "坚牢黄玉": {
                "type": "突破宝石",
                "sources": ["相关首领掉落", "合成转化"]
            },
            "堕天的落羽": {
                "type": "BOSS",
                "sources": ["角色突破首领掉落"]
            },
            "空羽蛾": {
                "type": "区域特产",
                "sources": ["野外采集"]
            },
            "摩拉": {
                "type": "通用货币",
                "sources": ["任何敌人", "任何活动"]
            }
        }
        
        print("✓ 已增强莉奈娅的数据")
    
    # 保存增强后的game_dict
    output_path = game_dict_path.replace('.json', '_enhanced.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(game_dict, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已保存增强后的game_dict: {output_path}")
    
    # 显示摘要
    print("\n📊 增强数据摘要:")
    if 'linnea' in avatars:
        linnea = avatars['linnea']
        print("  莉奈娅:")
        if 'ascension_total_cost' in linnea:
            cost = linnea['ascension_total_cost']['materials']
            print(f"    - 升级到90级需要 {len(cost)} 种材料")
            print(f"    - 材料示例: {list(cost.items())[:3]}")
        if 'talent_materials' in linnea:
            print(f"    - 天赋材料来源条目: {len(linnea['talent_materials']['sources'])}")
        if 'ascension_materials_detail' in linnea:
            tiers = linnea['ascension_materials_detail']['tiers']
            print(f"    - 分段升级信息: {len(tiers)} 个等级阶段")
    
    return game_dict


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 Game Dict 增强工具")
    print("=" * 60)
    print()
    
    enhance_game_dict_with_baike_data()
    
    print("\n✅ 完成！")
