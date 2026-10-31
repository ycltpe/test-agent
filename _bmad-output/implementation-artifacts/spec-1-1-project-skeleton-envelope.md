---
title: 'Story 1.1 项目骨架与信封模型'
type: 'feature'
created: '2026-10-31'
status: 'ready-for-dev'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '_bmad-output/implementation-artifacts/epic-1-context.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-test-2026-10-22/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 微聊首响 Agent 尚无统一项目骨架，各模块将各自为战；过滤器间缺少唯一通信契约（信封），管道-过滤器架构（过滤器间仅通过信封传递）无法落地。

**Approach:** 按架构 Structural Seed 建立全新包骨架（九目录），定义单一信封 Pydantic 模型（六核心字段 + 架构预留四字段），并按架构 Stack 表锁定 pyproject 依赖；既有 my-agent 原型按"不复用、不继承"处置。

## Boundaries & Constraints

**Always:**
- 目录严格按 Structural Seed：`adapters/`、`filters/`、`llm/`、`session/`、`cache/`、`models/`、`workers/`、`observability/`、`health/`，位于新包 `src/` 下。
- 信封为全链路唯一通信模型；六核心字段 `session_id`、`house_id`、`turn`、`intent`、`timestamp`、`trace_id`；预留 `message`、`resolved_message`、`coref`、`media_type` 四字段（本 Story 仅定义，不消费）。
- 信封提供 `model_validate` 类方法校验任意来源 dict；缺失必填字段、类型错误、未知枚举值一律 fail-closed（抛 `ValidationError`），由调用方兜底。
- pyproject 与架构 Stack 表一致：Python ≥3.11、FastAPI ≥0.115.0、Uvicorn ≥0.32.0、Pydantic ≥2.9.0、redis-py 8.1.0、Langfuse SDK 5.0.4、cachetools 7.2.4。
- 既有 my-agent 脚手架（anthropic、a2a-sdk、sse-starlette、postgres checkpoint 相关）不复用、不继承。
- 决策（Open Questions 已决）：新包名为 `weiliao_agent`；旧原型 `src/my_agent/` 与耦合测试（tests/ 下 5 个文件）直接删除，原型依赖从 pyproject 移除。

**Never:**
- 不实现任何过滤器逻辑、HTTP 端点、会话/缓存实现——本 Story 仅骨架与信封。
- 骨架代码不引入 LangGraph Runtime 依赖（LangGraph/LangChain-OpenAI 依赖按 Stack 表锁定版本，但代码不使用）。
- 不改 docker-compose.yml 与 .env 中的密钥内容。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | 合法六字段 dict 经 model_validate | 信封实例，timestamp 为 datetime 类型 | N/A |
| MISSING_REQUIRED | 缺 session_id 或 house_id 的 dict | ValidationError（fail-closed） | 调用方捕获后走模板兜底（本 Story 仅保证异常被抛出） |
| UNKNOWN_FIELD | 含未定义字段的 dict | 默认忽略（Pydantic 行为），不报错 | N/A |
| BAD_TYPE | trace_id 为非字符串（如 dict） | ValidationError | 同上，fail-closed |

</frozen-after-approval>

## Code Map

- `pyproject.toml` -- 项目定义（hatchling，wheel 打包 `src/my_agent`）；依赖与打包路径的调整对象
- `uv.lock` -- 已锁 95 包；redis/langfuse/cachetools 未锁定，`uv add` 需联网
- `src/my_agent/` -- 旧原型 9 文件（main.py、config.py、api/、agent/、a2a/），处置对象，不可复用
- `tests/test_a2a.py`、`tests/test_agent.py`、`tests/test_multi_agent.py`、`tests/test_api.py`、`tests/conftest.py` -- 全部深度耦合旧原型，随处置方案删除或重写
- `.env.example` -- 仅 LLM_* 三变量；本 Story 不新增（REDIS_URL 等留给 Story 1.3）
- `docker-compose.yml` -- 本地服务合集（含 redis 7:6379，无 Kafka），只读
- `.venv/` -- Python 3.11.15 可用，fastapi 0.139.2 / pydantic 2.13.4 已装

## Tasks & Acceptance

**Execution:**
- [ ] `pyproject.toml` -- 重命名项目与新包路径，移除原型依赖，按 Stack 表新增 redis 8.1.0、langfuse 5.0.4、cachetools 7.2.4（LangGraph 1.2.16、LangChain-OpenAI ≥1.6.2 按表核对保留），`uv sync` 更新 lock -- AC 要求 pyproject 与 Stack 表一致
- [ ] `src/<新包>/` -- 创建 Structural Seed 九目录（各含 `__init__.py`）-- 基座目录契约
- [ ] `src/<新包>/models/envelope.py` -- 实现信封模型 + `model_validate` 校验 -- AC 核心交付
- [ ] `tests/test_envelope.py` -- I/O 矩阵四场景单测 -- AC 可独立验收
- [ ] 旧原型处置 -- 按 Open Questions 答案删除或迁移 `src/my_agent/` 与耦合测试 -- 架构"不复用、不继承"

**Acceptance Criteria:**
- Given 架构 Structural Seed 定义，当初始化代码库与依赖，则全部目录与最小可运行骨架就位，pyproject 版本与 Stack 表一致，既有 my-agent 依赖不复用、不继承
- Given 任意来源的信封 dict，当经 `model_validate` 校验，则合法输入产出信封实例，缺必填字段/类型错误 fail-closed 抛 `ValidationError`

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

信封字段必填性：`session_id`、`house_id`、`timestamp`、`trace_id` 必填；`turn`、`intent` 允许为 None（turn 由会话管理在入管道前赋值、intent 由分类器填写，均属后续 Story），但非 None 时类型必须正确。`intent` 本 Story 为 `str | None`，9 类 Literal 枚举在 Story 2.1 定义后收窄。预留四字段默认 None，不参与本 Story 验收。

## Verification

**Commands:**
- `uv sync` -- expected: lock 更新成功，无依赖冲突
- `uv run pytest` -- expected: 全绿（旧耦合测试已按处置方案移除）
- `uv run ruff check .` -- expected: 无告警
- `uv run mypy src` -- expected: strict 模式无错误
