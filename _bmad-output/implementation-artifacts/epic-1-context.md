# Epic 1 Context: 消息管道基座与会话状态

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

建立微聊首响 Agent 的管道-过滤器骨架与信封模型，实现会话状态单写者管理、健康检查端点与 Langfuse 全链路追踪脚手架。本 Epic 是所有后续 Epic（意图分类、缓存、LLM、转人工）赖以运行的基座：完成后，任意买家消息可被服务可靠接收、沿过滤器链编排处理，且在多实例部署下读取一致的会话上下文。骨架本身必须独立可交付、可验收——错误兜底依赖最小占位模板集，不等待 Epic 4 的完整模板库。

## Stories

- Story 1.1: 项目骨架与信封模型
- Story 1.2: 管道过滤器编排与统一错误兜底
- Story 1.3: 会话状态单写者管理
- Story 1.4: 健康检查端点
- Story 1.5: Langfuse 全链路追踪脚手架

## Requirements & Constraints

- 会话状态一致性：同一 session 的连续消息无论由哪个实例处理都读到一致状态；会话状态存 Redis，TTL 30 分钟；并发读写无竞态（Redis 原子操作）；会话过期后重新发起对话从零初始化、无残留。
- 竞态语义明确：会话 TTL 过期瞬间恰有消息在管道中处理时，过期判定以消息入管道时的会话读取结果为准，处理中途过期不中断在途消息（转人工终态除外）。
- 端到端延迟预算 P99 < 3s 适用于本 Epic 的兜底路径：内部异常/超时触发兜底时买家收到应答的时限受该预算约束，不得傻等全量超时后才返回。
- 服务实例无状态：逻辑架构保持任意实例可处理任意消息；任何进程内优化不得影响正确性。
- 可观测：每个请求携带贯穿全链路的 trace_id 并记录成本（token 消耗与模型调用费用），后续验收口径以 Langfuse trace 数据为准。
- 健康检查：服务就绪时 `GET /health` 返回 200，未就绪返回非 200，供负载均衡与发布流程摘挂实例。
- 骨架可独立验收：附带最小占位模板集（每意图一条安全文案），在 Epic 4 的完整模板库就位前支撑错误兜底机制验收。

## Technical Decisions

- 管道-过滤器架构：过滤器仅消费上游信封、产出下游信封，禁止跨过滤器直接函数调用。过滤器链为 intent_router → cache_lookup → risk_review → response_assembler（Epic 1 先建骨架与占位过滤器，具体能力由后续 Epic 填充）。
- 热路径手写纯 Python，不依赖 LangGraph Runtime；LLM 生成过滤器（后续 Epic）内部允许 LangGraph 子图，对外仅暴露同步生成接口。
- 信封：单一 Pydantic 模型，全链路 `model_validate` 校验。核心字段 session_id、house_id、turn、intent、timestamp、trace_id；架构另约定 message（买家原文）、resolved_message（消解后消息）、coref（引用元数据，可空）、media_type（text/other）字段，信封随管道逐跳填充，实现本 Epic 时模型应预留这些字段。
- 项目骨架按 Structural Seed 建目录：`adapters/`、`filters/`、`llm/`、`session/`、`cache/`、`models/`、`workers/`、`observability/`、`health/`。
- 技术栈锁定：Python ≥3.11、FastAPI ≥0.115.0、Uvicorn ≥0.32.0、Pydantic ≥2.9.0、redis-py 8.1.0、Langfuse SDK 5.0.4、cachetools 7.2.4（LangGraph、LangChain-OpenAI 为 Epic 4 依赖）。既有 my-agent 脚手架（anthropic、a2a-sdk、postgres checkpoint、sse-starlette）为无关原型依赖，不复用、不继承。
- 会话状态单写者：会话状态仅由会话管理模块（session/）写入，过滤器只读并传 session_id；`turn` 为会话内绝对消息序号，由会话管理模块在消息入管道前赋值；handoff 状态（后续 Epic）由会话管理模块在转人工分支写入。
- 统一错误兜底：所有过滤器捕获异常后降级至模板兜底（转人工分支除外）；禁止将未审核内容发买家；错误响应携带 trace_id。
- 数据格式：Redis 值用 JSON 序列化；意图标签为单一 Literal 枚举（9 类），未知值 fail-closed 到模板兜底。
- 部署拓扑（K8s vs 公司 PaaS）尚未决策，代码不得假设特定部署形态。

## Cross-Story Dependencies

- Story 1.1（骨架与信封）是其余全部故事的前置：信封模型与目录结构就位后，才能编排过滤器链（1.2）、接入会话管理（1.3）、挂健康端点（1.4）与埋 trace（1.5）。
- Story 1.2 的占位模板集仅服务本 Epic 的独立验收，将在 Story 4.1 被完整模板库替换；Epic 1 交付不依赖 Epic 4。
- Story 1.5 的 trace_id 贯穿机制是 Story 1.2 错误响应携带 trace_id、以及后续各 Epic 验收（降级事件、审核结果、缓存命中、追问禁走缓存）的统一数据源，宜在编排定型后尽早接入。
- Story 1.3 定义的会话状态读写接口被 Epic 2（意图写入、追问计数）、Epic 3（handoff 快照一致性）与 Epic 5（handoff 状态写入）直接消费，接口边界在本 Epic 内须按单写者原则一次定准。
