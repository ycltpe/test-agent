# 技术栈与部署形态

架构脊柱 Stack 章节的定稿选型。版本以下限要求为准，最新版核实日期见各行备注（FastAPI 于 2026-10-23 复核，其余为 2026-10-22 核实）。

## 技术栈

| Name | Version | 备注 |
| --- | --- | --- |
| Python | ≥3.11 | |
| FastAPI | ≥0.115.0 | 下限已核实存在；最新版以 PyPI 为准（2026-10-23 核实为 0.161.1） |
| Uvicorn | ≥0.32.0 | 截至 2026-10-22 经 PyPI 核实最新 0.54.0 |
| Pydantic | ≥2.9.0 | 截至 2026-10-22 经 PyPI 核实最新 2.14.1 |
| LangGraph | 1.2.16 | LLM 子图编排（仅 LLM 生成过滤器内部使用，见 AD-2） |
| LangChain-OpenAI | ≥1.6.2 | 截至 2026-10-22 经 PyPI 核实最新 1.7.2 |
| redis-py | 8.1.0 | L0 缓存客户端 |
| Langfuse SDK | 5.0.4 | 全链路 trace 与成本追踪 |
| cachetools | 7.2.4 | L1 进程内缓存（TTLCache） |
| OpenAI API | gpt-4o / gpt-4o-mini | API 级模型名；**经 OpenAI 官方弃用公告核实（2026-10-14 通知）：gpt-4o 全系列（含 mini）将于 2027-01-14 从 API 关停，官方替代 gpt-6-luna**；模型名经配置注入（alias 指向当前快照，禁硬编码），迁移路径见 [architecture-decisions.md](architecture-decisions.md) Deferred |

## 部署形态

- Agent 以**独立 Python 服务**部署，与既有 SpringBoot 微服务体系经 Kafka 解耦（不修改现有体系）。
- 逻辑架构要求**实例无状态**：任意实例可处理任意消息；L1 进程内缓存仅为优化层，不影响正确性（见 [architecture-decisions.md](architecture-decisions.md) Deferred 与 AD-5）。
- 具体部署拓扑（K8s vs 公司 PaaS、实例水平扩展、可用区冗余）待运维/架构评审决策。

## 排除说明

既有 `my-agent` 脚手架（anthropic、a2a-sdk、postgres checkpoint、sse-starlette 等依赖）为无关原型依赖，本架构**不复用、不继承**。新服务按 [structural-seed.md](structural-seed.md) 的目录种子从零搭建。
