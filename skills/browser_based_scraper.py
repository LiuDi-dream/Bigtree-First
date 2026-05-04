#!/usr/bin/env python3
"""
BOSS敌首掉落素材自动爬虫
从米游社百科页面自动爬取所有BOSS敌首及其掉落物品
"""

import json
import time
import re
from typing import Dict, List, Tuple, Optional


def extract_boss_info_from_page(page_html: str, boss_name: str) -> Optional[List[str]]:
    """
    从BOSS详情页HTML中提取掉落物品
    """
    try:
        # 查找"掉落物品"相关内容
        match = re.search(r'掉落物品[^<]*</td>\s*<td[^>]*>(.*?)</td>', page_html, re.DOTALL)
        if not match:
            return None
        
        drops_html = match.group(1)
        
        # 移除HTML标签
        drops_text = re.sub(r'<[^>]+>', ' ', drops_html)
        # 清理特殊字符和多余空白
        drops_text = re.sub(r'[\n\r\t]+', ' ', drops_text)
        drops_text = re.sub(r'\s+', ' ', drops_text).strip()
        
        # 提取所有物品名称
        drops = []
        for item in drops_text.split():
            # 过滤掉纯数字和特殊符号
            if item and not re.match(r'^[\d×÷%]*$', item) and item != '无':
                # 移除末尾数字
                clean_item = re.sub(r'\s*\d+\s*$', '', item).strip()
                if clean_item and clean_item not in drops:
                    drops.append(clean_item)
        
        return drops if drops else None
    except Exception as e:
        print(f"❌ 解析错误 ({boss_name}): {str(e)}")
        return None


def scrape_all_bosses_from_browser() -> Dict[str, List[str]]:
    """
    使用浏览器页面数据爬取所有BOSS信息
    此函数会被调用多次，每次处理一个BOSS
    """
    return {}


# BOSS列表 - 从浏览器页面获取的所有敌首ID和名称
BOSS_LIST = [
    (508281, "丘尔德里克"),
    (508280, "摩诃婆苏提婆耶弗太子"),
    (508282, "辖域守护者"),
    (508279, "守望者·堕天"),
    (508031, "玻瑞亚斯之影"),
    (508006, "蕴光月守宫"),
    (507667, "「博士」"),
    (507662, "蕴光凛狼"),
    (507665, "驰岚·霜夜灵嗣"),
    (507663, "深黯魇语之主"),
    (507664, "金礞·霜夜灵嗣"),
    (507666, "涌流·霜夜灵嗣"),
    (507658, "十六倍曼陀草"),
    (507660, "望乡的孤狼"),
    (507661, "深黯钓客"),
    (507659, "海捷德"),
    (507351, "超重型陆巡舰·机动战垒"),
    (507055, "「猎月人」雷利尔"),
    (506916, "霜夜巡天灵主"),
    (506167, "荒野狂狩士"),
    (506166, "荒野幽徒"),
    (506281, "拉斯科尔尼科夫"),
    (506176, "「蟹沙皇」"),
    (506133, "凌晶·霜夜灵嗣"),
    (506132, "辉电·霜夜灵嗣"),
    (506134, "蔓结·霜夜灵嗣"),
    (506131, "灼烜·霜夜灵嗣"),
    (506159, "西格德"),
    (505689, "巴窟纳瓦"),
    (505677, "最后的特诺奇兹托克人"),
    (505313, "秘源机兵·统御械"),
    (505312, "门扉前的弈局"),
    (508501, "深古秘源机龙"),
    (504935, "天使海兔"),
    (504934, "猎刀鳐"),
    (504932, "帽子水母"),
    (503951, "蚀灭的源焰之主"),
    (503950, "灵觉隐修的迷者"),
    (502358, "莉琉"),
    (501187, "西尼阿斯"),
    (501883, "巴拉奇科"),
    (501882, "科西霍"),
    (501881, "异色三连星"),
    (501880, "海浪中的莎孚"),
    (501879, "金焰绒翼龙暴君"),
    (501884, "贪食匿叶龙山王"),
    (1987, "若陀龙王"),
    (1223, "「公子」"),
    (212, "北风的王狼"),
    (209, "裂空的魔龙"),
    (189, "狂风之核"),
    (173, "无相之雷·阿莱夫"),
    (2626, "雷音权现"),
    (3573, "祸津御建鸣神命"),
    (1769, "洛蒂娅的愤怒"),
    (1770, "深渊使徒·激流"),
    (2461, "无相之火·亚因"),
    (2624, "「女士」"),
    (2625, "无相之水·希伊"),
    (2027, "深渊咏者·紫电"),
]


def create_scraper_script():
    """
    创建一个可以与浏览器交互的爬虫脚本
    """
    scraper_code = """
    // 这个脚本会被在浏览器console中执行
    // 用于从当前BOSS详情页提取掉落物品
    
    const getBossDrops = () => {
        const bossName = document.querySelector('h1')?.textContent?.trim();
        const drops = [];
        
        // 查找表格中的"掉落物品"行
        const cells = document.querySelectorAll('td');
        for (let i = 0; i < cells.length; i++) {
            if (cells[i].textContent?.includes('掉落物品')) {
                const nextRow = cells[i].closest('tr')?.nextElementSibling;
                if (nextRow) {
                    const items = nextRow.querySelectorAll('li');
                    items.forEach(item => {
                        const text = item.textContent?.trim();
                        if (text && !text.match(/^\\d+$/) && text !== '无') {
                            const clean = text.replace(/\\s*\\d+\\s*$/, '').trim();
                            if (clean && !drops.includes(clean)) {
                                drops.push(clean);
                            }
                        }
                    });
                } else {
                    // 备用: 直接从下一个单元格提取
                    const dropCell = cells[i].nextElementSibling;
                    if (dropCell) {
                        const fullText = dropCell.textContent || '';
                        const parts = fullText.split(/[\\s\\n]+/).filter(p => p.trim());
                        parts.forEach(part => {
                            if (!part.match(/^\\d+$/) && part !== '无' && part.length > 0) {
                                const clean = part.replace(/\\s*\\d+\\s*$/, '').trim();
                                if (clean && !drops.includes(clean)) {
                                    drops.push(clean);
                                }
                            }
                        });
                    }
                }
                break;
            }
        }
        
        return {
            name: bossName,
            drops: drops
        };
    };
    
    getBossDrops();
    """
    return scraper_code


if __name__ == "__main__":
    print("=" * 70)
    print("BOSS敌首掉落素材自动爬虫")
    print("=" * 70)
    print()
    print(f"📊 待爬取的BOSS总数: {len(BOSS_LIST)}")
    print()
    print("⚠️  此爬虫需要与浏览器配合使用")
    print()
    print("使用方法:")
    print("1. 运行: python skills/browser_based_scraper.py")
    print("2. 等待浏览器自动逐个访问每个BOSS页面")
    print("3. 自动提取并保存掉落物品数据")
    print()
    print("BOSS列表预览:")
    for i, (boss_id, boss_name) in enumerate(BOSS_LIST[:10], 1):
        print(f"  {i:2d}. {boss_name} (ID: {boss_id})")
    print(f"  ... 还有 {len(BOSS_LIST) - 10} 个BOSS")
    print()
