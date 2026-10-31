# 评审：Stack 版本与现实性核查

- **对象**: ARCHITECTURE-SPINE.md（updated 2026-10-23，新增 AD-11 指代消解，Stack 未变）
- **评审日期**: 2026-10-23
- **评审方式**: PyPI JSON API 逐包核实版本与 requires_python；OpenAI 官方文档核实模型生命周期
- **判定**: **needs-work**

## 总体结论

Stack 中 8 个 Python 库全部真实存在、版本号与 PyPI 当前最新一致、requires_python 均兼容 Python ≥3.11，无"已不存在/已改名"项。但有两处必须处理：

1. **gpt-4o / gpt-4o-mini 已被 OpenAI 官宣 API 弃用**（2026-10-14 公告，2027-01-14 关停），脊柱备注"可用性以采购合同为准"未覆盖该事实，备注不充分，构成实质性风险漏报。
2. FastAPI 备注中的"经 PyPI 核实最新 0.159.1"已过时（当日实际为 0.161.1）。

## 逐项核查结果

| 库 | 脊柱声明 | PyPI 最新（2026-10-23） | requires_python | 结论 |
| --- | --- | --- | --- | --- |
| Python | ≥3.11 | — | — | OK |
| FastAPI | ≥0.115.0（备注：最新 0.159.1） | 0.161.1 | >=3.10 | **备注过时**；下限本身合理 |
| Uvicorn | ≥0.32.0（备注：最新 0.54.0） | 0.54.0 | >=3.10 | OK，备注准确 |
| Pydantic | ≥2.9.0（备注：最新 2.14.1） | 2.14.1 | >=3.10 | OK，备注准确 |
| LangGraph | 1.2.16 | 1.2.16 | >=3.10 | OK，精确钉版即当前最新 |
| LangChain-OpenAI | ≥1.6.2（备注：最新 1.7.2） | 1.7.2 | >=3.10,<4 | OK，备注准确 |
| redis-py | 8.1.0 | 8.1.0 | >=3.10 | OK，精确钉版即当前最新 |
| Langfuse SDK | 5.0.4 | 5.0.4 | >=3.11 | OK；其 requires_python 恰好以 3.11 为下限，与 Stack 的 Python ≥3.11 一致 |
| cachetools | 7.2.4 | 7.2.4 | >=3.10 | OK，精确钉版即当前最新 |

所有库均适配 Python ≥3.11，无版本冲突迹象。精确钉版的三个库（LangGraph / redis-py / Langfuse / cachetools）当前恰为最新，短期无漂移；但建议在依赖清单（requirements/lock）层面而非脊柱层面跟踪。

## Findings

### [P0] gpt-4o / gpt-4o-mini 已官宣 API 弃用，备注严重不足

- **位置**: Stack 表末行（"OpenAI API | gpt-4o / gpt-4o-mini | API 级模型名，可用性以采购合同为准"）
- **事实**: OpenAI 于 2026-10-14 发布弃用公告，`gpt-4o-2024-08-06`、`gpt-4o-2024-11-20`、`gpt-4o-mini-2024-07-18` 将于 **2027-01-14 从 API 关停**，官方推荐替代为 `gpt-6-luna`。来源：[OpenAI API Deprecations](https://developers.openai.com/api/docs/deprecations)。
- **影响**: 脊柱将 gpt-4o 系列作为生成主模型（AD-9 降级链、LLM 生成过滤器均以其为前提）。MVP 虽可能在 2027-01 前上线，但：采购合同无法阻止 OpenAI 侧关停；V2 范围（多级降级链）落地时主模型可能已不可用；意图分类器选型（Deferred，OQ-1，候选含 gpt-4o-mini zero-shot）同样受影响。
- **建议**: 备注至少补三点——(a) 2027-01-14 API 关停日期与官方替代 `gpt-6-luna`；(b) 模型名使用 alias（`gpt-4o`/`gpt-4o-mini` 指向当前快照）以便快照切换；(c) 与 AD-9 降级链衔接，明确主模型迁移路径与里程碑（如 V2 前完成替代模型验证）。

### [P2] FastAPI "经核实最新"备注过时

- **位置**: Stack 表 FastAPI 行备注（"截至 2026-10-22 经 PyPI 核实最新 0.159.1"）
- **事实**: 2026-10-23 核实 PyPI 最新为 0.161.1。
- **影响**: 仅信息性偏差，下限 ≥0.115.0 不受影响；但"经核实最新"类断言会快速过期，持续产生维护噪声。
- **建议**: 要么更新数字，要么将措辞改为"下限已核实存在，最新版本以 PyPI 为准"，避免脊柱携带易腐断言。

## 其余技术断言核查

- 全文除 Stack 表外无其他版本/外部事实断言；AD-1 至 AD-11 均为内部架构规则，不涉及第三方版本声明，无需现实性核查。
- 表注声明 my-agent 脚手架依赖（anthropic、a2a-sdk、postgres checkpoint、sse-starlette）不复用、不继承——与 Stack 无冲突，不构成未核实风险（属内部既有资产声明，且明确排除）。
- gpt-4o 备注之外的模型可用性：脊柱未声明 gpt-4o 以外的模型，Deferred 中 DeepSeek/Qwen 仅为方向性提及，无版本断言。

## 复核清单（若修订）

1. Stack 表 gpt-4o 行补充关停日期（2027-01-14）、官方替代（gpt-6-luna）、alias 策略与 AD-9 衔接说明。
2. FastAPI 行备注更新为 0.161.1 或改为非易腐措辞。
3. 修订后无需重新核查其余 7 库（本次已核实为当前最新）。
