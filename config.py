import os
import platform
from dotenv import load_dotenv

# 🌟 强制在此处加载一次环境变量，防止被 main.py 的导入顺序坑到
load_dotenv()

HISTORY_FILE = os.path.join("memory", "chat_context.json")
SYSTEM_RULES_FILE = os.path.join("prompts", "system_rules.md")

# ==========================================
# 🌟 智能路径解析逻辑
# ==========================================
def get_default_bgi_dir():
    """根据系统环境自动推断 BetterGI 的默认安装路径"""
    # 检查是否在 WSL 环境中
    if "microsoft" in platform.uname().release.lower():
        return "/mnt/c/Program Files/BetterGI"
    else:
        # 纯 Windows 环境的默认路径
        return r"C:\Program Files\BetterGI"

# 优先读取 .env 中用户自定义的 BGI_DIR，如果没有配置，则使用智能判断的默认值
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