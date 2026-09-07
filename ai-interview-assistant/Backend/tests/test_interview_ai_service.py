import json
from types import SimpleNamespace

from app.models.schemas import InterviewConfigRequest
from app.services.interview_ai_service import (
    InterviewAIService,
    PlannedQuestion,
    QuestionPlanOutput,
)


class RecordingCompletions:
    def __init__(self) -> None:
        self.schema_names: list[str] = []

    def create(self, **kwargs):
        self.schema_names.append(kwargs["response_format"]["json_schema"]["name"])
        payload = json.loads(kwargs["messages"][1]["content"])
        questions = [
            {
                "title": f"{skill} question",
                "text": f"Explain your experience and a production trade-off involving {skill}.",
                "skill_tag": skill,
                "type": "technical",
            }
            for skill in payload["skills"]
        ]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"questions": questions})))]
        )


def make_service(completions: RecordingCompletions) -> InterviewAIService:
    service = InterviewAIService.__new__(InterviewAIService)
    service.client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    )
    service.model = "fake-model"
    service.chat_api = "chat_completions"
    service.openai_base_url = "https://gateway.example/v2"
    return service


def test_gateway_schema_name_varies_by_plan_payload() -> None:
    completions = RecordingCompletions()
    service = make_service(completions)

    java_config = InterviewConfigRequest(
        job_role="Backend Engineer",
        level="senior",
        skills=["Java", "Spring Boot"],
        num_questions=2,
        language="en",
        style="technical",
    )
    python_config = java_config.model_copy(
        update={"skills": ["Python", "FastAPI"]},
    )

    java_plan = service.generate_plan(java_config)
    python_plan = service.generate_plan(python_config)

    assert [question.skill_tag for question in java_plan.questions] == ["Java", "Spring Boot"]
    assert [question.skill_tag for question in python_plan.questions] == ["Python", "FastAPI"]
    assert completions.schema_names[0] != completions.schema_names[1]


def test_plan_validation_rejects_unrequested_skills() -> None:
    config = InterviewConfigRequest(
        job_role="Backend Engineer",
        level="senior",
        skills=["Java", "Spring Boot"],
        num_questions=2,
        language="en",
        style="mixed",
    )
    stale_plan = QuestionPlanOutput(
        questions=[
            PlannedQuestion(
                title="Python",
                text="Describe Python API development.",
                skill_tag="Python",
                type="technical",
            ),
            PlannedQuestion(
                title="FastAPI",
                text="Explain FastAPI dependency injection.",
                skill_tag="FastAPI",
                type="technical",
            ),
        ]
    )

    error = InterviewAIService._plan_validation_error(config, stale_plan)

    assert error is not None
    assert "not requested" in error
