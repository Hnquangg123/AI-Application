from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.services.project_service import retrieve_project_context


class ConversationState(TypedDict, total=False):
    config: dict[str, Any]
    question: dict[str, Any]
    recent_messages: list[dict[str, str]]
    follow_up_count: int
    project_context: list[str]
    decision: Any


def _retrieve_context(state: ConversationState, *, db: Session) -> dict[str, list[str]]:
    config = state["config"]
    project_id = config.get("project_id")
    if not project_id:
        return {"project_context": []}

    context = retrieve_project_context(
        db,
        UUID(str(project_id)),
        f'{config.get("job_role", "")} {" ".join(config.get("skills", []))} '
        f'{state["question"].get("text", "")}',
    )
    return {"project_context": context[:5]}


def build_conversation_graph(*, db: Session, ai: Any):
    def decide(state: ConversationState) -> dict[str, Any]:
        decision = ai.decide_conversation_turn(
            config=state["config"],
            question=state["question"],
            recent_messages=state["recent_messages"],
            follow_up_count=state["follow_up_count"],
            project_context=state.get("project_context", []),
        )
        return {"decision": decision}

    graph = StateGraph(ConversationState)
    graph.add_node("retrieve_context", lambda state: _retrieve_context(state, db=db))
    graph.add_node("decide", decide)
    graph.add_edge(START, "retrieve_context")
    graph.add_edge("retrieve_context", "decide")
    graph.add_edge("decide", END)
    return graph.compile()


def run_conversation_turn(
    *,
    db: Session,
    ai: Any,
    config: dict[str, Any],
    question: dict[str, Any],
    recent_messages: list[dict[str, str]],
    follow_up_count: int,
) -> tuple[Any, list[str]]:
    result = build_conversation_graph(db=db, ai=ai).invoke(
        {
            "config": config,
            "question": question,
            "recent_messages": recent_messages,
            "follow_up_count": follow_up_count,
        }
    )
    return result["decision"], result.get("project_context", [])