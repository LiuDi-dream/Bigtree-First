# 🏠 本地模型部署指南

> **如何在本地运行 LLM 模型而无需 API Key，实现完全离线和隐私保护**

## 📋 支持的本地模型框架

| 框架 | 支持度 | 推荐度 | 说明 |
|------|--------|--------|------|
| **Ollama** | ✅✅✅ | ⭐⭐⭐⭐⭐ | **最推荐**，使用最简单 |
| **vLLM** | ✅✅✅ | ⭐⭐⭐⭐ | 高性能，支持量化模型 |
| **LLaMA.cpp** | ✅✅✅ | ⭐⭐⭐ | 轻量级，CPU 友好 |
| **LocalAI** | ✅✅ | ⭐⭐⭐ | 通用框架，支持多种模型 |

---

## 🚀 快速开始（推荐 Ollama）

### 1️⃣ 安装 Ollama

**macOS & Linux**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows**
- 访问 https://ollama.ai 下载安装器

### 2️⃣ 启动 Ollama 服务

```bash
ollama serve
```

默认监听地址：`http://localhost:11434`

> ⚠️ **重要**: 项目期望的默认 API 地址是 `http://localhost:8000/v1`，如果使用 Ollama，需要配置代理或使用其他框架

### 3️⃣ 拉取模型

在另一个终端运行：

```bash
# 拉取 Llama2（7B，推荐）
ollama pull llama2

# 或其他模型
ollama pull mistral          # Mistral 7B（更快更聪明）
ollama pull neural-chat      # Neural Chat（中文友好）
ollama pull phind-codellama  # Code Llama（编程）
```

### 4️⃣ 配置项目

修改 `.env` 文件：

```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:11434/api/generate
MODEL_NAME=llama2
```

> 🔄 **Ollama 使用 `/api/generate` 端点，而不是标准的 `/v1/chat/completions`**

---

## 🔧 使用 vLLM（推荐高性能场景）

### 1️⃣ 安装 vLLM

```bash
pip install vllm

# 如果使用 GPU（推荐）
pip install vllm[cuda]  # 需要 CUDA 环境
```

### 2️⃣ 启动 vLLM 服务

```bash
# 使用 Llama2
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000

# 或使用 Mistral（更小更快）
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.1 \
    --port 8000
```

### 3️⃣ 配置项目

修改 `.env` 文件：

```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:8000/v1
MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
```

### 4️⃣ 运行项目

```bash
python main.py
```

---

## 💻 使用 LLaMA.cpp（轻量级，CPU 友好）

### 1️⃣ 构建 LLaMA.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make

# 下载模型（GGUF 格式）
# 例如从 https://huggingface.co/TheBloke 下载
```

### 2️⃣ 启动 API 服务器

```bash
./server -m models/llama-2-7b.gguf --port 8000 -c 2048
```

### 3️⃣ 配置项目

```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:8000/v1
MODEL_NAME=local
```

---

## 🌐 使用 LocalAI（通用框架）

### 1️⃣ 使用 Docker 快速启动

```bash
docker run -p 8080:8080 \
  -e MODELS_PATH=/models \
  -e THREADS=8 \
  localai/localai:v2.0.0
```

### 2️⃣ 配置项目

```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:8080/v1
MODEL_NAME=your-model-name
```

---

## 📊 性能对比与选择建议

### Ollama
```
✅ 优点:
  • 安装最简单，开箱即用
  • 自动下载优化的模型
  • 支持 GPU 加速
  
❌ 缺点:
  • 性能相对较低
  • 内存占用较大
```

### vLLM
```
✅ 优点:
  • 性能最好（提供最快的推理）
  • GPU 利用率最高
  • 支持 LoRA、量化等优化
  
❌ 缺点:
  • 安装配置复杂
  • 需要 CUDA 环境（GPU 推荐）
```

### LLaMA.cpp
```
✅ 优点:
  • 极其轻量级
  • CPU 运行也很快（支持量化）
  • 内存占用最少
  
❌ 缺点:
  • 需要手动编译
  • 模型格式限制（只支持 GGUF）
```

---

## 🖥️ 硬件需求

### 最低配置
- **CPU**: Intel i5 或等效（8 核心推荐）
- **RAM**: 16GB（8GB 可勉强运行）
- **磁盘**: 20GB+ (用于存储模型)

### 推荐配置（使用 GPU）
- **GPU**: NVIDIA RTX 3060 或更好（至少 6GB VRAM）
- **RAM**: 16GB+ (模型会加载到 VRAM)
- **磁盘**: 30GB+ SSD

### 模型大小参考
| 模型 | 大小 | 内存需求 | 速度 |
|------|------|---------|------|
| Llama2 7B | ~3.5GB | 8GB | 🟢 一般 |
| Mistral 7B | ~4GB | 8GB | 🟢 一般 |
| Llama2 13B | ~7GB | 16GB | 🟡 较慢 |
| Llama2 70B | ~33GB | 48GB+ | 🔴 很慢 |

---

## 🎯 推荐配置方案

### 🏠 普通笔记本 (CPU)
```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:8000/v1
MODEL_NAME=mistral  # 小模型，快速

# 使用 vLLM
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.1 \
  --port 8000 \
  --cpu-offload-gb 10
```

### 🎮 带 GPU 的工作站
```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:8000/v1
MODEL_NAME=meta-llama/Llama-2-13b-chat-hf

# 使用 vLLM（GPU 加速）
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-13b-chat-hf \
  --port 8000 \
  --tensor-parallel-size 2  # 多卡并行
```

### 🚀 极简配置（Ollama）
```ini
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:11434/api/generate
MODEL_NAME=mistral

# 仅需运行
ollama serve
ollama pull mistral
```

---

## 🔍 常见问题

### Q: 本地模型需要 API Key 吗？
❌ **不需要**！系统会自动使用占位符 "local"

### Q: 如何切换模型？
```ini
# 只需修改 MODEL_NAME
MODEL_NAME=llama2      # 改成 llama2
MODEL_NAME=mistral     # 改成 mistral
```

### Q: 如何检查本地服务是否运行？
```bash
# 测试连接
curl http://localhost:8000/v1/models

# 如果看到模型列表，说明服务正常
```

### Q: 模型推理太慢怎么办？
1. 使用较小的模型（如 Mistral 7B 而不是 Llama2 70B）
2. 启用量化（减小精度但增加速度）
3. 使用 GPU 加速
4. 增加更多 RAM 或 VRAM

### Q: 内存占用太高怎么办？
```bash
# 在 vLLM 中启用 CPU Offload
python -m vllm.entrypoints.openai.api_server \
  --model model_name \
  --cpu-offload-gb 10

# 或使用 LLaMA.cpp 的量化模型
```

---

## 📱 隐私与离线运行

✅ **本地模型的优势**

1. **完全离线**: 无需网络连接
2. **数据隐私**: 数据从不上传到云端
3. **成本**: 一次安装，永久免费使用
4. **控制**: 完全掌握模型和数据

---

## 🔗 有用资源

- **Ollama**: https://ollama.ai
- **vLLM**: https://github.com/lm-sys/vllm
- **LLaMA.cpp**: https://github.com/ggerganov/llama.cpp
- **LocalAI**: https://github.com/go-skynet/LocalAI
- **Hugging Face Models**: https://huggingface.co/models

---

**🎉 开始使用本地模型，享受完全的隐私和自由！**
