import os

HISTORY_FILE = os.path.join("memory", "chat_context.json")
SYSTEM_RULES_FILE = os.path.join("prompts", "system_rules.md")

BGI_DIR = "/mnt/c/Program Files/BetterGI"
BGI_EXE = "BetterGI.exe"

BGI_ONE_DRAGON_CONFIG = os.path.join(BGI_DIR, "User", "OneDragon", "默认配置测试.json")
BGI_MAP_CONFIG = os.path.join(BGI_DIR, "User", "ScriptGroup", "地图素材.json")
BGI_GLOBAL_CONFIG = os.path.join(BGI_DIR, "User", "config.json")
BGI_BOSS_CONFIG = os.path.join(
    BGI_DIR,
    "User",
    "JsScript",
    "批量讨伐角色养成材料BOSS",
    "assets",
    "config",
    "config.json",
)

DEFAULT_UID = "286682352"
MAX_HISTORY_MESSAGES = 20
