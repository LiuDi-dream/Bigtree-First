#!/usr/bin/env python3
"""
测试脚本：验证新的 LLM 多提供商配置是否正确工作
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("🧪 LLM 配置系统测试")
print("="*60)

# 测试1：检查环境变量是否正确加载
print("\n📋 检查当前配置:")
provider = os.getenv("LLM_PROVIDER", "github")
model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
print(f"  LLM_PROVIDER: {provider}")
print(f"  MODEL_NAME: {model_name}")

# 测试2：尝试创建客户端
print("\n🔨 尝试创建 LLM 客户端...")
try:
    from brain import llm_brain
    client = llm_brain._make_client()
    print(f"  ✅ {provider.upper()} 客户端创建成功!")
    print(f"  客户端类型: {type(client).__name__}")
except Exception as e:
    print(f"  ❌ 创建客户端失败: {e}")

# 测试3：验证各提供商配置
print("\n📝 各提供商配置检查:")

providers_config = {
    "github": {
        "token_env": "GITHUB_TOKEN",
        "base_url": "https://models.inference.ai.azure.com",
    },
    "openai": {
        "token_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
    },
    "nvidia": {
        "token_env": "NVIDIA_API_KEY",
        "base_url_env": "NVIDIA_BASE_URL",
    },
    "custom": {
        "token_env": "CUSTOM_API_KEY",
        "base_url_env": "CUSTOM_BASE_URL",
    },
}

for prov, config_keys in providers_config.items():
    token_env = config_keys.get("token_env", "")
    token_status = "✅ 已配置" if os.getenv(token_env) else "⚠️  未配置"
    
    if "base_url_env" in config_keys:
        base_url_env = config_keys["base_url_env"]
        base_url_status = "✅ 已配置" if os.getenv(base_url_env) else "⚠️  未配置"
        print(f"  {prov.upper()}: {token_status}, {base_url_status}")
    else:
        print(f"  {prov.upper()}: {token_status}")

print("\n" + "="*60)
print("💡 使用说明:")
print("  1. 在 .env 文件中设置 LLM_PROVIDER 为：github, openai, nvidia, custom")
print("  2. 根据选择的提供商配置对应的 API Key 和 Base URL")
print("  3. 项目会自动读取 .env 并选择对应的 API 提供商")
print("="*60)
