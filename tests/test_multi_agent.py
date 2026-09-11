"""
https://cloud.tencent.com/developer/article/2649756
Multi-Agent 技术研究团队
基于 LangGraph 2026 最新API
依赖: pip install langgraph langchain-openai psycopg2-binary
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import operator
import json
import os

load_dotenv()  # 从项目根目录 .env 加载配置

# ============ 1. 定义共享状态 ============
class TeamState(TypedDict):
    topic: str                                    # 研究主题
    search_queries: list[str]                     # 搜索关键词列表
    raw_results: Annotated[list[str], operator.add]  # 原始搜索结果（累加）
    key_findings: list[dict]                      # 提取的关键发现
    analysis: str                                 # 深度分析结果
    code_examples: list[str]                      # 生成的代码示例
    report: str                                   # 最终报告
    revision_count: int                           # 修订次数
    messages: Annotated[list[dict], operator.add] # Agent间通信记录

# ============ 2. 初始化模型（配置来自 .env）============
_llm_kwargs = {
    "model": os.environ["LLM_MODEL_ID"],
    "api_key": os.environ["LLM_API_KEY"],
    "base_url": os.environ["LLM_BASE_URL"],
}
llm_smart = ChatOpenAI(temperature=0.1, **_llm_kwargs)      # 研究和分析用
llm_creative = ChatOpenAI(temperature=0.7, **_llm_kwargs)    # 写作用

# ============ 3. 定义Agent节点 ============
def extract_json(text: str):
    """从模型输出中解析JSON：截取第一个 [ 或 { 到匹配的最后一个 ] 或 }，兼容前后多余文字和 ``` 包裹"""
    text = text.strip()
    start_candidates = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not start_candidates:
        return json.loads(text)  # 直接解析，让原生报错信息抛出
    start = min(start_candidates)
    end_char = "]" if text[start] == "[" else "}"
    end = text.rfind(end_char)
    return json.loads(text[start:end + 1])

def research_node(state: TeamState) -> dict:
    """研究员Agent：搜索并提取关键信息"""
    prompt = f"""你是一位AI技术研究专家。
    主题: {state['topic']}

    请生成3个最有效的搜索查询来收集该主题的最新信息。
    返回JSON格式: {{"queries": ["query1", "query2", "query3"]}}"""

    response = llm_smart.invoke(prompt)
    queries = extract_json(response.content)["queries"]

    # 模拟搜索（实际项目中替换为真实搜索API调用）
    results = []
    for q in queries:
        results.append(
            f"[搜索: {q}] 命中5篇文章，摘要如下："
            f"文章围绕「{state['topic']}」展开，介绍了该方向的最新架构设计、"
            f"性能基准测试结果、典型落地案例以及社区 adoption 情况，"
            f"并对比了多种主流实现方案的优劣。"
        )

    # 提取关键发现
    extract_prompt = f"""以下是内部检索系统返回的搜索结果摘要（真实数据，直接基于它们做提取，不要索要更多信息）。

基于以下搜索结果，提取5个最关键的技术发现。
严格返回JSON数组格式，每个元素包含: title(标题), content(内容), source(来源)

搜索结果:
{chr(10).join(results)}"""

    findings_raw = llm_smart.invoke(extract_prompt).content
    try:
        findings = extract_json(findings_raw)
    except json.JSONDecodeError:
        print(f"!!! findings JSON 解析失败，模型原始返回:\n{findings_raw[:500]}")
        raise

    return {
        "search_queries": queries,
        "raw_results": results,
        "key_findings": findings,
        "messages": [{"agent": "researcher", "action": "搜索完成", "findings": len(findings)}]
    }

def analysis_node(state: TeamState) -> dict:
    """分析师Agent：深度技术分析"""
    findings_text = json.dumps(state["key_findings"], ensure_ascii=False, indent=2)

    prompt = f"""你是一位资深技术分析师。基于以下研究发现，提供深度技术分析。

    要求:
    1. 技术原理剖析（底层架构、核心算法）
    2. 与竞品的对比分析（至少3个维度）
    3. 实际应用场景和落地难度评估
    4. 未来6-12个月的发展预测

    研究发现:
    {findings_text}"""

    analysis = llm_smart.invoke(prompt).content

    # 生成配套代码示例（用代码块格式，比JSON字符串更稳定）
    code_prompt = f"""基于分析内容，生成2个实用的代码示例。
    每个示例20-40行，覆盖不同技术点。
    用 ```python 代码块``` 逐个给出，不要输出JSON。

    分析内容: {analysis[:2000]}"""

    code_raw = llm_smart.invoke(code_prompt).content
    # 兼容模型可能的 ```python 前缀行：去掉首行语言标记
    cleaned = []
    for block in code_raw.split("```"):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        if lines[0].strip().lower() in ("python", "py", "json"):
            block = "\n".join(lines[1:])
        if block.strip():
            cleaned.append(block.strip())
    code_examples = cleaned[:2] if cleaned else [code_raw]

    return {
        "analysis": analysis,
        "code_examples": code_examples,
        "messages": [{"agent": "analyst", "action": "分析完成"}]
    }

def writing_node(state: TeamState) -> dict:
    """编辑Agent：生成最终报告"""
    prompt = f"""你是一位技术自媒体编辑。基于以下素材撰写技术文章。

    要求:
    - 开头用场景或数据切入，不要用"近年来"开头
    - 正文不少于2000字
    - 包含代码示例和对比表格
    - 语言专业但不晦涩，像资深工程师面对面聊技术

    分析素材:
    {state['analysis']}

    代码示例:
    {chr(10).join(state['code_examples'])}"""

    report = llm_creative.invoke(prompt).content

    return {
        "report": report,
        "messages": [{"agent": "writer", "action": "报告生成完成"}]
    }

# ============ 4. 条件路由 ============
def route_after_research(state: TeamState) -> Literal["analyze", "retry"]:
    """搜索结果质量检查"""
    if len(state.get("key_findings", [])) < 3:
        return "retry"    # 发现太少，重新搜索
    return "analyze"      # 质量合格，进入分析

def quality_check(state: TeamState) -> Literal["write", "revise"]:
    """分析质量检查"""
    if len(state.get("analysis", "")) < 500:
        return "revise"   # 分析太浅，要求修订
    return "write"        # 质量合格，进入写作

# ============ 5. 构建工作流图 ============
builder = StateGraph(TeamState)

# 添加节点
builder.add_node("research", research_node)
builder.add_node("analyze", analysis_node)
builder.add_node("write", writing_node)

# 设置入口和边
builder.set_entry_point("research")
builder.add_conditional_edges("research", route_after_research, {"analyze": "analyze", "retry": "research"})
builder.add_conditional_edges("analyze", quality_check, {"write": "write", "revise": "analyze"})
builder.add_edge("write", END)

# ============ 6. 编译并运行 ============
DB_URI = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_team")

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()  # 首次运行：创建 checkpoints 表
    app = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["analyze"]  # 分析前暂停，等待人工确认
    )

    config = {"configurable": {"thread_id": "research-2026-09-11"}}

    # 启动研究任务
    result = app.invoke(
        {"topic": "2026年Multi-Agent框架最新技术演进和历史", "revision_count": 0},
        config=config,
    )

    # interrupt_before=["analyze"]：首次执行到分析前会暂停，恢复后继续跑完
    if not result or "report" not in result:
        print(">>> 已在 analyze 节点前暂停（人工确认点），继续执行剩余流程...")
        result = app.invoke(None, config=config)

    print(f"研究完成! 报告长度: {len(result['report'])}字")
    print(f"{result['report']}")
