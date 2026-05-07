# 🚀 快速参考：LLM 多提供商配置

## ⚡ 30 秒快速开始

### GitHub Models（默认，推荐）
```env
LLM_PROVIDER=github
GITHUB_TOKEN=ghp_xxx...
MODEL_NAME=gpt-4o-mini
```

### OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o
```

### nVidia
```env
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-xxx...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL_NAME=meta/llama-3.1-405b-instruct
```

### 交大 API / 自定义 OpenAI 兼容 API
```env
LLM_PROVIDER=custom
CUSTOM_API_KEY=your-key
CUSTOM_BASE_URL=https://api.example.com/v1
MODEL_NAME=model-name
```

---

## 📝 修改步骤

1. **打开 `.env` 文件**
2. **修改这两行**：
   ```
   LLM_PROVIDER=github          # 改成: openai, nvidia, custom
   GITHUB_TOKEN=ghp_xxx...      # 改成对应的 API Key
   ```
3. **保存并运行**：
   ```bash
   python main.py  # 或 python feishu_main.py
   ```

---

## ✅ 验证配置

```bash
./gi_env/bin/python test_llm_config.py
```

应该看到：`✅ [PROVIDER] 客户端创建成功!`

---

## 🎯 推荐方案

| 场景 | 推荐 | 理由 |
|------|------|------|
| 🏠 个人开发 | GitHub | 免费 + 快 |
| 🎓 学生/高校 | 交大 API | 校网免费 |
| 💰 小成本 | nVidia | 免费额度大 |
| 🎯 最优精度 | OpenAI | 模型最好 |

---

## 🔧 常见问题

### 我想用 OpenAI，怎么改？
1. 去 https://platform.openai.com/api-keys 获取 API Key
2. 修改 `.env`:
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-你的key
   ```
3. 完成！

### 我想用交大 API，怎么改？
1. 获取交大 API 的 Key 和 Base URL
2. 修改 `.env`:
   ```env
   LLM_PROVIDER=custom
   CUSTOM_API_KEY=你的key
   CUSTOM_BASE_URL=交大api的url
   MODEL_NAME=交大的模型名
   ```
3. 完成！

### 改了 `.env` 还是不行？
- 确保 `.env` 文件保存了
- 检查 API Key 是否正确
- 运行验证脚本：`./gi_env/bin/python test_llm_config.py`

---

## 📚 详细文档

- 📖 完整指南: `LLM_PROVIDER_GUIDE.md`
- 📋 修改总结: `MODIFICATION_SUMMARY.md`
- 🧪 配置测试: `test_llm_config.py`

---

**提示**: 这次修改是零风险的！✨
- ✅ 不修改任何现有功能
- ✅ 不破坏任何代码逻辑
- ✅ 100% 向后兼容
- ✅ 只涉及 API 客户端初始化
