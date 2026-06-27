import os
import platform

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)

HISTORY_FILE = os.path.join(BASE_DIR, "memory", "chat_context.json")
SYSTEM_RULES_FILE = os.path.join(BASE_DIR, "prompts", "system_rules.md")


def get_default_bgi_dir():
    """Infer the default BetterGI install path from the platform."""
    if "microsoft" in platform.uname().release.lower():
        return "/mnt/c/Program Files/BetterGI"
    return r"C:\Program Files\BetterGI"


BGI_DIR = os.getenv("BGI_DIR", get_default_bgi_dir())
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
