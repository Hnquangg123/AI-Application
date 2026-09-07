from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.models.schemas import InterviewConfigRequest
from app.services.interview_ai_service import (
    EvaluationCompetency,
    EvaluationOutput,
    EvaluationQuestionFeedback,
    PlannedQuestion,
    QuestionPlanOutput,
    TurnDecisionOutput,
    get_interview_ai_service,
)
from main import app


class FakeInterviewAI:
    model = "fake-model"
    conversation_calls = 0

    def generate_plan(self, config: InterviewConfigRequest, **_kwargs) -> QuestionPlanOutput:
        return QuestionPlanOutput(
            questions=[
                PlannedQuestion(
                    title=f"Question {index + 1}",
                    text=f"Tell me about skill {index + 1}.",
                    skill_tag=config.skills[index % len(config.skills)],
                    type="technical",
                )
                for index in range(config.num_questions)
            ]
        )

    def generate_project_question(
        self, config: InterviewConfigRequest, *, project_name: str, project_context: list[str]
    ) -> PlannedQuestion:
        return PlannedQuestion(
            title="Project architecture",
            text=f"How does data flow through {project_name}?",
            skill_tag=None,
            type="system_design",
        )

    def decide_turn(self, config, question, recent_messages, follow_up_count) -> TurnDecisionOutput:
        if follow_up_count == 0:
            return TurnDecisionOutput(
                reply="What measurable result did that produce?",
                action="follow_up",
                score=None,
                note=None,
            )
        return TurnDecisionOutput(
            reply="Thanks, that is useful context.",
            action="next_question",
            score=4,
            note="Clear and specific.",
        )

    def decide_conversation_turn(
        self, config, question, recent_messages, follow_up_count, project_context
    ) -> TurnDecisionOutput:
        self.conversation_calls += 1
        assert project_context == []
        return self.decide_turn(config, question, recent_messages, follow_up_count)

    def evaluate(self, config, questions, messages) -> EvaluationOutput:
        return EvaluationOutput(
            overall_score=80,
            readiness="interview_ready",
            competencies=[
                EvaluationCompetency(name="Communication", score=4, comment="Clear examples.")
            ],
            strengths=["Structured communication"],
            improvements=["Quantify more outcomes"],
            per_question=[
                EvaluationQuestionFeedback(
                    question_id=question["id"],
                    score=question["progressive_score"] or 0,
                    feedback="Useful evidence." if question["progressive_score"] else "Not attempted.",
                )
                for question in questions
            ],
            summary_text="A strong practice session with clear, structured answers.",
        )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_interview_ai_service] = lambda: FakeInterviewAI()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_complete_interview_journey(client: TestClient) -> None:
    created = client.post(
        "/api/interviews",
        json={
            "job_role": "Backend Engineer",
            "level": "senior",
            "skills": ["Python", "PostgreSQL"],
            "num_questions": 3,
            "language": "en",
            "style": "mixed",
        },
    )
    assert created.status_code == 201
    session = created.json()
    assert session["action"] == "created"
    assert session["config"]["mode"] == "structured"
    assert len(session["questions"]) == 3
    assert session["current_question"]["index"] == 0

    session_id = session["session_id"]
    question_id = session["current_question"]["id"]
    follow_up = client.post(
        f"/api/interviews/{session_id}/answer",
        json={
            "message": "I led the API design and rollout.",
            "question_id": question_id,
            "client_message_id": "answer-0001",
        },
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["action"] == "follow_up"

    advanced = client.post(
        f"/api/interviews/{session_id}/answer",
        json={
            "message": "It reduced latency by 30 percent.",
            "question_id": question_id,
            "client_message_id": "answer-0002",
        },
    )
    assert advanced.status_code == 200
    session = advanced.json()
    assert session["action"] == "next_question"
    assert session["current_question"]["index"] == 1

    skipped = client.post(f"/api/interviews/{session_id}/skip")
    assert skipped.status_code == 200
    assert skipped.json()["current_question"]["index"] == 2

    ended = client.post(f"/api/interviews/{session_id}/end")
    assert ended.status_code == 200
    assert ended.json()["status"] == "summarized"
    assert ended.json()["summary"]["overall_score"] == 80

    restored = client.get(f"/api/interviews/{session_id}")
    assert restored.status_code == 200
    assert restored.json()["summary"]["readiness"] == "interview_ready"

    history = client.get("/api/interviews?limit=10&offset=0")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["session_id"] == session_id
    assert history.json()["items"][0]["message_count"] == 6

    summary = client.get(f"/api/interviews/{session_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["competencies"][0]["score"] == 4

    archived = client.patch(
        f"/api/interviews/{session_id}/archive",
        json={"archived": True},
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/api/interviews").json()["total"] == 0


def test_conversation_mode_uses_langgraph_turn_path(client: TestClient) -> None:
    created = client.post(
        "/api/interviews",
        json={
            "job_role": "Backend Engineer",
            "level": "senior",
            "skills": ["Python"],
            "num_questions": 1,
            "language": "en",
            "style": "technical",
            "mode": "conversation",
        },
    )
    assert created.status_code == 201
    session = created.json()
    assert session["config"]["mode"] == "conversation"

    answer = client.post(
        f'/api/interviews/{session["session_id"]}/answer',
        json={
            "message": "I built a Python API.",
            "question_id": session["current_question"]["id"],
            "client_message_id": "conversation-0001",
        },
    )
    assert answer.status_code == 200
    assert answer.json()["action"] == "follow_up"


def test_active_session_can_toggle_conversation_mode(client: TestClient) -> None:
    created = client.post(
        "/api/interviews",
        json={
            "job_role": "Backend Engineer",
            "level": "senior",
            "skills": ["Python"],
            "num_questions": 1,
            "language": "en",
            "style": "technical",
        },
    )
    session_id = created.json()["session_id"]

    enabled = client.patch(
        f"/api/interviews/{session_id}/mode",
        json={"mode": "conversation"},
    )
    assert enabled.status_code == 200
    assert enabled.json()["config"]["mode"] == "conversation"

    disabled = client.patch(
        f"/api/interviews/{session_id}/mode",
        json={"mode": "structured"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["config"]["mode"] == "structured"


def test_create_interview_with_project_serializes_project_id(client: TestClient) -> None:
    project = client.post(
        "/api/projects",
        json={"name": "QuickCart", "description": "Order processing platform"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    created = client.post(
        "/api/interviews",
        json={
            "job_role": "Backend Engineer",
            "level": "senior",
            "skills": ["Python"],
            "num_questions": 1,
            "language": "en",
            "style": "mixed",
            "project_id": project_id,
        },
    )

    assert created.status_code == 201
    assert created.json()["config"]["project_id"] == project_id
    assert len(created.json()["questions"]) == 2
    assert created.json()["questions"][-1]["title"] == "Project deep dive"

    refreshed = client.get(f"/api/interviews/{created.json()['session_id']}")
    assert refreshed.status_code == 200
    assert refreshed.json()["questions"][-1]["title"] == "Project architecture"
