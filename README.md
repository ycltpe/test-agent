# my-agent

一个基于 FastAPI 的 Agent 服务，封装了 Claude API，支持会话历史管理。

## 功能

- 通过 HTTP POST `/api/v1/chat` 与 Agent 对话
- 可选的 `session_id` 维持多轮会话上下文
- 通过 DELETE `/api/v1/sessions/{session_id}` 清空会话历史
- 健康检查接口 `/api/v1/health`

## 环境变量

复制 `.env.example` 为 `.env` 并填写：

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

## 开发

```bash
# 安装依赖
uv sync --all-extras

# 运行服务
uv run my-agent

# 运行测试
uv run pytest

# 代码检查与格式化
uv run ruff check .
uv run ruff format .
uv run mypy src
```

## API 示例

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "demo"}'
```
