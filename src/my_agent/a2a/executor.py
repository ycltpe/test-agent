"""A2A 协议执行器：将内部 Agent 接入 A2A 协议。

参考：https://github.com/google/A2A
"""

import os
from datetime import UTC, datetime

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()  # 从项目根目录 .env 加载 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL

_llm = ChatOpenAI(
    model=os.environ["LLM_MODEL_ID"],
    api_key=SecretStr(os.environ["LLM_API_KEY"]),
    base_url=os.environ["LLM_BASE_URL"],
    temperature=0.1,
)

# 会话历史：context_id -> A2A 消息列表
_sessions: dict[str, list[Message]] = {}


def _extract_text(message: Message) -> str:
    """从 A2A 消息中提取文本内容。"""
    return "".join(part.text for part in message.parts if part.text)


class A2AAgentExecutor(AgentExecutor):
    """A2A 执行器：接收 A2A 消息，调用 LLM，回发 Task 事件。

    用 A2A 的 context_id 作为会话 ID，让同一对话上下文共享多轮会话历史。
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """执行一次 A2A 请求并发布任务事件。"""
        user_text = _extract_text(context.message)  # type: ignore[arg-type]
        task_id = context.task_id
        context_id = context.context_id

        # 1. 先发布初始任务（框架要求 Task 必须在状态更新事件之前入队）
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_SUBMITTED,
                    timestamp=datetime.now(UTC),
                ),
            )
        )

        # 2. 任务开始：进入工作状态
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    timestamp=datetime.now(UTC),
                ),
            )
        )

        # 3. 调用 LLM（同一 context_id 共享多轮历史）
        try:
            history = _sessions.setdefault(context_id, [])  # type: ignore[arg-type]
            langchain_messages = [
                ("human" if m.role == Role.ROLE_USER else "ai", _extract_text(m))
                for m in history
            ]
            reply = (await _llm.ainvoke([*langchain_messages, ("human", user_text)])).content
            history.append(context.message)  # type: ignore[arg-type]
            history.append(
                Message(role=Role.ROLE_AGENT, parts=[Part(text=str(reply))])
            )
        except Exception as exc:
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    status=TaskStatus(
                        state=TaskState.TASK_STATE_FAILED,
                        message=Message(
                            role=Role.ROLE_AGENT,
                            parts=[Part(text=f"Agent 执行出错: {exc}")],
                        ),
                        timestamp=datetime.now(UTC),
                    ),
                )
            )
            return

        # 4. 产出结果 artifact
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=Artifact(
                    artifact_id="reply",
                    name="agent_reply",
                    parts=[Part(text=str(reply))],
                ),
            )
        )

        # 5. 任务完成
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_COMPLETED,
                    message=Message(
                        role=Role.ROLE_AGENT,
                        parts=[Part(text=str(reply))],
                    ),
                    timestamp=datetime.now(UTC),
                ),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """取消任务：当前实现直接把任务标记为已取消。"""
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_CANCELED,
                    timestamp=datetime.now(UTC),
                ),
            )
        )
