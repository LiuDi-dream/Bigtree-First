# GI_Agent 合并版说明

## 这个版本是什么

这是把原来的 DeepSeek 接入能力和客户端回滚能力合并后的版本。现在只保留一个主分支概念，模型提供商通过 `LLM_PROVIDER` 在 GitHub 和 DeepSeek 之间切换，回滚能力则始终保留。

## 主要特点

- 支持 `github` 和 `deepseek` 两种模型提供商
- 通过 `.env` 中的 `LLM_PROVIDER` 切换模型
- 每轮执行前自动生成 checkpoint
- 同时保存文件系统快照和对话记忆
- 支持回滚最后一次已提交快照
- 支持在 CLI 和飞书入口中处理 `rollback`

## 已验证内容

- GitHub 模型客户端可创建
- DeepSeek 模型客户端可创建
- 真实启动流程可运行
- 回滚回归测试可通过
- 文件状态可以恢复
- `memory/chat_context.json` 也可以恢复

## 启动方式

1. 配置 `.env`
2. 安装依赖
3. 运行 `python main.py`
4. 需要时在命令行输入 `rollback`

## `.env` 里怎么切换

- 用 GitHub：`LLM_PROVIDER=github`
- 用 DeepSeek：`LLM_PROVIDER=deepseek`

两个 Key 可以同时保留在 `.env`，程序只读取当前 `LLM_PROVIDER` 对应的那一组。

## 适合谁看

- 想只维护一个版本的人
- 想理解“双模型 + 回滚”组合的人
- 想继续扩展 checkpoint 机制的人

## 备注

- 本版本新增了 `test_rollback_flow.py` 和 `test_provider_matrix.py`
- `.vibelign/checkpoints/` 用于保存快照
