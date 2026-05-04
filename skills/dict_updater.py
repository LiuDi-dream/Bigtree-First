import requests
import json
import os
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

def _build_session():
    """构造带重试和代理回退的会话。"""
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def _fetch_with_fallback(url, proxy_first=True):
    """尝试先走代理，失败则直连获取数据。"""
    proxy_url = os.getenv("GENSHIN_PROXY", "http://127.0.0.1:7890")
    proxies = {"http": proxy_url, "https": proxy_url}
    
    attempts = []
    if proxy_first:
        attempts.append((proxies, "代理"))
    attempts.append((None, "直连"))
    
    last_error = None
    for plan_proxies, plan_name in attempts:
        try:
            with _build_session() as session:
                r = session.get(url, proxies=plan_proxies, timeout=(5, 20))
                r.raise_for_status()
                return r.json()
        except Exception as e:
            last_error = e
            # 继续尝试下一个方案
    
    raise last_error or RuntimeError("无法获取数据")

def _fetch_from_ambr():
    """从 Ambr.top 获取角色和武器数据。"""
    print("📡 尝试从 Ambr.top 获取数据...")
    try:
        char_data = _fetch_with_fallback("https://api.ambr.top/v2/cn/character/index", proxy_first=False)
        weapon_data = _fetch_with_fallback("https://api.ambr.top/v2/cn/weapon/index", proxy_first=False)
        
        result = {"characters": {}, "weapons": {}}
        
        # 提取角色数据
        for char_id, char_info in char_data.get("data", {}).items():
            result["characters"][char_id] = {
                "name": char_info.get("name", "未知"),
                "rarity": char_info.get("rarity", 0),
            }
        
        # 提取武器数据
        for weapon_id, weapon_info in weapon_data.get("data", {}).items():
            result["weapons"][weapon_id] = {
                "name": weapon_info.get("name", "未知"),
                "rarity": weapon_info.get("rarity", 0),
                "type": weapon_info.get("type", "unknown"),
            }
        
        print(f"✅ Ambr.top: 获取 {len(result['characters'])} 个角色，{len(result['weapons'])} 件武器")
        return result
    except Exception as e:
        print(f"⚠️ Ambr.top 失败: {e}")
        return None

def _fetch_from_genhin_data_repo():
    """备用方案：从 GenshinData GitHub 仓库获取数据。"""
    print("📡 尝试从 GenshinData 仓库获取数据...")
    try:
        # GenshinData 提供的角色和武器映射表
        char_url = "https://raw.githubusercontent.com/Dimbreath/GenshinData/master/TextMap/TextMapCN.json"
        
        loc_data = _fetch_with_fallback(char_url)
        
        # 从文本映射中提取角色和武器相关条目
        characters = {}
        weapons = {}
        
        for hash_str, name in loc_data.items():
            # 这是一个简化版本，实际的 GenshinData 提供更完整的数据结构
            # 这里仅作备用示例
            if "Character" in hash_str or any(c in name for c in ["安柏", "琴", "芭芭拉"]):
                hash_key = hash_str
                if hash_key not in characters:
                    characters[hash_key] = {"name": name, "rarity": 0}
        
        print(f"✅ GenshinData: 获取 {len(characters)} 个角色数据")
        return {"characters": characters, "weapons": weapons}
    except Exception as e:
        print(f"⚠️ GenshinData 失败: {e}")
        return None

def _extract_weapons_from_loc(loc_data):
    """从 loc.json 中智能提取武器信息。
    
    loc.json 包含所有游戏对象的名称哈希映射。
    通过启发式方法识别武器名称。
    """
    # 获取中文翻译 - 注意 EnkaNetwork 使用 zh-cn 而不是 chs
    zh_lang_keys = ["zh-cn", "chs", "zh-CN", "CHS"]
    zh_names = None
    for key in zh_lang_keys:
        if key in loc_data:
            zh_names = loc_data[key]
            print(f"   ✓ 使用中文键: {key}")
            break
    
    if not zh_names:
        print(f"   ⚠️ 找不到中文语言包！可用的键: {list(loc_data.keys())}")
        return {}
    
    # 从 loc.json 中提取武器
    # 武器名称通常在 nameTextMapHash 对应的条目中
    weapons = {}
    weapon_keywords = ["剑", "弓", "枪", "矛", "杖", "法器", "斧", "槌", "刀", "匕首", "弹弓"]
    
    for hash_key, name in zh_names.items():
        # 过滤条件：
        # 1. 不是属性或其他系统名称
        # 2. 包含武器关键词
        # 3. 名称长度合理（通常 2-15 字符）
        if name.startswith("FIGHT_PROP") or name.startswith("Lv.") or len(name) > 20:
            continue
        
        if not any(kw in name for kw in weapon_keywords):
            continue
        
        # 避免重复（同名武器）
        if name not in [w["name"] for w in weapons.values()]:
            weapons[hash_key] = {
                "name": name,
                "rarity": 3,  # 默认稀有度
                "type": "unknown"
            }
    
    return weapons

def _fetch_weapon_data_from_web():
    """尝试从网络获取完整的武器数据列表。"""
    try:
        # 尝试从 enka-indexer 获取武器列表
        url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/lookup-chardecorationaffixdecorationlevels.json"
        data = _fetch_with_fallback(url, proxy_first=False)
        # 如果获取成功，返回处理后的数据
        return data
    except:
        pass
    
    try:
        # 备用：尝试其他源
        url = "https://raw.githubusercontent.com/DimbrethGenshinData/master/ExcelBinOutput/WeaponExcelConfigData.json"
        data = _fetch_with_fallback(url, proxy_first=False)
        return data
    except:
        pass
    
    return None

def _fetch_from_enka_network():
    """从 EnkaNetwork 获取角色和武器数据。
    
    数据来源：
    - 角色数据和名称从 EnkaNetwork 官方 API 仓库获取
    - 武器数据通过智能提取 loc.json 生成
    """
    print("📡 尝试从 EnkaNetwork 获取数据...")
    try:
        char_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/characters.json"
        loc_url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/loc.json"
        
        char_data = _fetch_with_fallback(char_url)
        loc_data = _fetch_with_fallback(loc_url)
        
        # 侦测语言包键（EnkaNetwork 使用 zh-cn 格式）
        zh_cn_key = None
        possible_keys = ["zh-cn", "chs", "zh-CN", "CHS"]
        for key in possible_keys:
            if key in loc_data:
                zh_cn_key = key
                break
        
        if not zh_cn_key:
            print(f"⚠️ 找不到中文语言包！可用的键: {list(loc_data.keys())}")
            return None
        
        lang_dict = loc_data[zh_cn_key]
        get_name = lambda h: lang_dict.get(h, "未知")
        
        # 提取角色
        characters = {}
        for avatar_id, info in char_data.items():
            name_hash = str(info.get("NameTextMapHash") or info.get("nameTextMapHash", ""))
            name = get_name(name_hash)
            if name and name != "未知":
                characters[str(avatar_id)] = {"name": name, "rarity": 0}
        
        print(f"✅ 提取了 {len(characters)} 个角色")
        
        # 提取武器
        weapons = _extract_weapons_from_loc(loc_data)
        print(f"✅ 提取了 {len(weapons)} 件武器")
        
        return {"characters": characters, "weapons": weapons}
    except Exception as e:
        print(f"⚠️ EnkaNetwork 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_dictionary():
    """更新游戏数据字典（角色+武器）。"""
    print("🔄 开始更新游戏数据字典...\n")
    
    # 尝试多个数据源
    data = None
    for fetcher in [_fetch_from_ambr, _fetch_from_genhin_data_repo, _fetch_from_enka_network]:
        data = fetcher()
        if data and (data.get("characters") or data.get("weapons")):
            break
        print()
    
    if not data or (not data.get("characters") and not data.get("weapons")):
        print("❌ 所有数据源均失败！")
        return
    
    # 构建最终字典
    final_dict = {
        "characters": {},
        "weapons": {},
        "metadata": {
            "version": "1.0",
            "description": "Genshin Impact game data with characters and weapons",
        }
    }
    
    # 处理角色数据
    if data.get("characters"):
        for char_id, char_info in data["characters"].items():
            if isinstance(char_info, dict):
                final_dict["characters"][str(char_id)] = char_info
            else:
                final_dict["characters"][str(char_id)] = {"name": str(char_info), "rarity": 0}
    
    # 处理武器数据
    if data.get("weapons"):
        for weapon_id, weapon_info in data["weapons"].items():
            if isinstance(weapon_info, dict):
                final_dict["weapons"][str(weapon_id)] = weapon_info
            else:
                final_dict["weapons"][str(weapon_id)] = {"name": str(weapon_info), "rarity": 0, "type": "unknown"}
    
    # 统计
    char_count = len(final_dict["characters"])
    weapon_count = len(final_dict["weapons"])
    print(f"\n📊 解析统计: {char_count} 个角色，{weapon_count} 件武器")
    
    # 保存
    os.makedirs("memory", exist_ok=True)
    dict_path = "memory/game_dict.json"
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(final_dict, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已保存至: {dict_path}")
    
    # 为了向后兼容，也保存一份简化的 avatar_dict.json（仅角色名称）
    compat_dict = {k: v.get("name", "未知") if isinstance(v, dict) else v 
                   for k, v in final_dict["characters"].items()}
    compat_path = "memory/avatar_dict.json"
    with open(compat_path, "w", encoding="utf-8") as f:
        json.dump(compat_dict, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 向后兼容字典已保存至: {compat_path}")

if __name__ == "__main__":
    update_dictionary()