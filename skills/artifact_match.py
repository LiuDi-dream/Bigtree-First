import json
import re

EXCEPTION_MAP = {
    "草": "深林的记忆",
    "风": "翠绿之影",
    "水": "沉沦之心",
    "火": "炽烈的炎之魔女",
    "冰": "冰风迷途的勇士",
    "下落": "长夜之誓",
}

def get_domain_by_user_intent(user_input, raw_json_data):
    # 1. 掐头去尾，提取核心词 (把 "我要刷绝缘套" 变成 "绝缘")
    keyword = user_input.replace("套", "").strip()
    
    # 2. 查例外字典
    official_name = EXCEPTION_MAP.get(keyword)
    
    # 3. 如果不是例外，遍历 JSON 找子串
    if not official_name:
        for item_id, data in raw_json_data.items():
            title = data.get("title", "")
            if keyword in title:
                official_name = title
                break
                
    # 4. 找到官方全名后，用正则提取获取途径里的副本名
    if official_name:
        for item_id, data in raw_json_data.items():
            if data.get("title") == official_name:
                for table in data.get("matched_tables", []):
                    for row in table.get("rows", []):
                        if len(row) >= 2 and row[0] == "获取途径":
                            match = re.search(r'^([^：:]+)[：:]', row[1])
                            if match:
                                return match.group(1).strip()
    
    return "未找到对应副本"