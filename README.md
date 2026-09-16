# my-agent

一个基于 FastAPI 的 Agent 服务，支持 A2A（Agent2Agent）协议接入，内置多轮会话管理。

## 功能

- 通过 HTTP POST `/api/v1/chat` 与 Agent 对话
- 可选的 `session_id` 维持多轮会话上下文
- 通过 DELETE `/api/v1/sessions/{session_id}` 清空会话历史
- 健康检查接口 `/api/v1/health`
- **A2A 协议支持**：JSON-RPC 端点 `POST /a2a`，AgentCard 暴露在 `GET /.well-known/agent-card.json`

## 环境变量

复制 `.env.example` 为 `.env` 并填写（LLM 网关使用 OpenAI 兼容接口）：

```bash
LLM_MODEL_ID=your_model_id
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://your-gateway/v1
```

## 开发

```bash
# 安装依赖
uv sync --all-extras

# 运行服务（同时暴露 /api/v1 与 /a2a）
uv run my-agent

# 只运行 A2A 协议服务（默认端口 8001）
uv run my-agent-a2a

# 运行测试
uv run pytest

# 代码检查与格式化
uv run ruff check .
uv run ruff format .
uv run mypy src
```

## A2A 协议说明

本服务基于 [a2a-sdk](https://github.com/google/A2A) 实现 A2A 协议 1.0：

- `GET /.well-known/agent-card.json`：AgentCard 描述文件
- `POST /a2a`：JSON-RPC 2.0 消息入口（`SendMessage` / `GetTask` 等方法）
- 会话上下文：首次调用后在响应的 `contextId` 字段获取上下文 ID，后续请求在 `message.contextId` 中携带即可维持多轮会话
- 请求需携带协议版本头：`A2A-Version: 1.0`

### A2A 调用示例

```bash
# 1. 查看 AgentCard
curl http://127.0.0.1:8000/.well-known/agent-card.json

# 2. 发送消息（首轮）
curl -X POST http://127.0.0.1:8000/a2a/ \
  -H "Content-Type: application/json" \
  -H "A2A-Version: 1.0" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "SendMessage",
    "params": {
      "message": {
        "role": "ROLE_USER",
        "parts": [{"text": "你好"}],
        "messageId": "msg-1"
      }
    }
  }'

# 3. 携带 contextId 继续对话（从上一轮响应的 contextId 字段获取）
```

## API 示例

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "demo"}'
```
