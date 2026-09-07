import json
from hashlib import sha256
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.clients.openai_client import get_openai_client
from app.config.settings import get_settings
from app.models.schemas import InterviewConfigRequest


StructuredOutput = TypeVar("StructuredOutput", bound=BaseModel)


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlannedQuestion(StrictOutput):
    title: str = Field(min_length=2, max_length=80)
    text: str = Field(min_length=5, max_length=1200)
    skill_tag: str | None = Field(max_length=100)
    type: Literal["technical", "behavioral", "system_design", "coding", "hr"]


class QuestionPlanOutput(StrictOutput):
    questions: list[PlannedQuestion]


class TurnDecisionOutput(StrictOutput):
    reply: str = Field(min_length=1, max_length=1200)
    action: Literal["follow_up", "next_question", "end_interview"]
    score: int | None = Field(ge=0, le=5)
    note: str | None = Field(max_length=500)


class EvaluationCompetency(StrictOutput):
    name: str = Field(min_length=2, max_length=100)
    score: int = Field(ge=0, le=5)
    comment: str = Field(min_length=2, max_length=500)


class EvaluationQuestionFeedback(StrictOutput):
    question_id: str
    score: int = Field(ge=0, le=5)
    feedback: str = Field(min_length=2, max_length=700)


class EvaluationOutput(StrictOutput):
    overall_score: int = Field(ge=0, le=100)
    readiness: Literal["needs_practice", "getting_there", "interview_ready"]
    competencies: list[EvaluationCompetency]
    strengths: list[str]
    improvements: list[str]
    per_question: list[EvaluationQuestionFeedback]
    summary_text: str = Field(min_length=5, max_length=2000)


class InterviewAIService:
    def __init__(self, client=None, model: str | None = None) -> None:
        settings = get_settings()
        self.client = client or get_openai_client()
        self.model = model or settings.openai_model_chat
        self.chat_api = settings.openai_chat_api
        self.openai_base_url = settings.openai_base_url or ""

    def _parse(
        self,
        *,
        instructions: str,
        payload: object,
        output_type: type[StructuredOutput],
        exact_list_lengths: dict[str, int] | None = None,
    ) -> StructuredOutput:
        use_chat_completions = self.chat_api == "chat_completions" or (
            self.chat_api == "auto" and self.openai_base_url.strip()
        )
        serialized_payload = json.dumps(payload, ensure_ascii=False, default=str)

        if use_chat_completions:
            schema_object = output_type.model_json_schema()
            for field_name, item_count in (exact_list_lengths or {}).items():
                field_schema = schema_object["properties"][field_name]
                field_schema["minItems"] = item_count
                field_schema["maxItems"] = item_count
            schema = json.dumps(schema_object, ensure_ascii=False)
            request_digest = sha256(
                f"{instructions}\0{serialized_payload}".encode("utf-8")
            ).hexdigest()[:12]
            schema_name = f"{output_type.__name__}_{request_digest}"
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{instructions}\nReturn JSON only. "
                            f"The JSON must match this schema exactly: {schema}"
                        ),
                    },
                    {"role": "user", "content": serialized_payload},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": True,
                        "schema": schema_object,
                    },
                },
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("The model returned an empty structured response")
            return output_type.model_validate_json(content)

        response = self.client.responses.parse(
            model=self.model,
            instructions=instructions,
            input=serialized_payload,
            text_format=output_type,
        )
        if response.output_parsed is None:
            raise ValueError("The model returned an invalid structured response")
        return response.output_parsed

    def generate_plan(
        self,
        config: InterviewConfigRequest,
        *,
        project_name: str = "",
        project_context: list[str] | None = None,
    ) -> QuestionPlanOutput:
        context = [item.strip() for item in (project_context or []) if item.strip()]
        project_instruction = ""
        if config.project_id:
            project_instruction = (
                f" The candidate selected project '{project_name or 'the selected project'}'. "
                "At least one question must specifically test understanding of that project's architecture, "
                "implementation, trade-offs, or failure handling. Use only the supplied project context; do not "
                "invent project details."
            )
        failure_reason = ""
        for attempt in range(2):
            correction = (
                f" This is a corrective retry. Fix this issue from the previous response: {failure_reason}."
                if attempt
                else ""
            )
            result = self._parse(
                instructions=(
                    "You design realistic mock interview question plans. "
                    f"The questions array must contain exactly {config.num_questions} items: no more and no fewer. "
                    "Use concise, non-duplicative questions ordered from warm-up to deeper assessment. Questions "
                    "must match the role, seniority, skills, language, and requested style. Write every user-facing "
                    "field in the configured language (en means English; vi means Vietnamese). Each requested skill "
                    "must appear in at least one question text or skill_tag. skill_tag must be null or exactly one "
                    "of the requested skills. Do not introduce technologies that were not requested. "
                    "Do not include answers."
                    f"{project_instruction}"
                    f"{correction}"
                ),
                payload={**config.model_dump(), "project_context": context},
                output_type=QuestionPlanOutput,
                exact_list_lengths={"questions": config.num_questions},
            )
            if len(result.questions) > config.num_questions:
                result = QuestionPlanOutput(questions=result.questions[: config.num_questions])

            failure_reason = self._plan_validation_error(config, result) or ""
            if not failure_reason:
                return result

        raise ValueError(f"The model returned an invalid question plan: {failure_reason}")

    @staticmethod
    def _plan_validation_error(
        config: InterviewConfigRequest,
        plan: QuestionPlanOutput,
    ) -> str | None:
        if len(plan.questions) != config.num_questions:
            return f"returned {len(plan.questions)} questions; expected {config.num_questions}"

        requested = {skill.casefold(): skill for skill in config.skills}
        generated_tags = {
            question.skill_tag.casefold(): question.skill_tag
            for question in plan.questions
            if question.skill_tag
        }
        unexpected = [tag for key, tag in generated_tags.items() if key not in requested]
        if unexpected:
            return f"used skills that were not requested: {', '.join(unexpected)}"

        searchable = " ".join(
            f"{question.skill_tag or ''} {question.text}".casefold()
            for question in plan.questions
        )
        missing = [skill for key, skill in requested.items() if key not in searchable]
        if missing:
            return f"did not cover requested skills: {', '.join(missing)}"
        return None

    def generate_project_question(
        self,
        config: InterviewConfigRequest,
        *,
        project_name: str,
        project_context: list[str],
    ) -> PlannedQuestion:
        """Generate one final deep-dive question from retrieved project context."""
        result = self._parse(
            instructions=(
                "Create exactly one interview question about the selected project. "
                "The question must test the candidate's understanding of architecture, "
                "implementation choices, trade-offs, data flow, reliability, or failure "
                "handling using only the supplied context. Do not invent project details "
                "and do not include an answer. Make it appropriate for the configured role "
                "and seniority. Write every user-facing field in the configured language "
                "(en means English; vi means Vietnamese). skill_tag must be null or exactly "
                "one of the configured skills. Prefer technical or system_design as type."
            ),
            payload={
                "config": config.model_dump(mode="json"),
                "project_name": project_name,
                "project_context": project_context,
            },
            output_type=QuestionPlanOutput,
            exact_list_lengths={"questions": 1},
        )
        if len(result.questions) != 1:
            raise ValueError("The model did not return exactly one project question")
        return result.questions[0]

    def decide_turn(


        self,
        config: dict,
        question: dict,
        recent_messages: list[dict],
        follow_up_count: int,
    ) -> TurnDecisionOutput:
        payload = {
            "config": config,
            "current_question": question,
            "follow_up_count": follow_up_count,
            "recent_messages": recent_messages,
        }
        return self._parse(
            instructions=(
                "You are a concise, encouraging mock interviewer. Ask one question at a time. Decide whether "
                "the newest candidate answer needs one focused follow-up or whether to advance. Use follow_up "
                "only when one concrete detail would materially improve the answer. If a follow-up was already "
                "asked, advance. Use end_interview only when the candidate explicitly asks to stop. The reply "
                "must contain only a short acknowledgement or focused follow-up; the server adds the next planned "
                "question. Write the reply and note in the configured language (en means English; vi means Vietnamese). "
                "Score 0-5 only when advancing. This is coaching, never a hiring decision."
            ),
            payload=payload,
            output_type=TurnDecisionOutput,
        )

    def decide_conversation_turn(
        self,
        config: dict,
        question: dict,
        recent_messages: list[dict],
        follow_up_count: int,
        project_context: list[str] | None = None,
    ) -> TurnDecisionOutput:
        """Decide the next conversational move with optional project grounding."""
        return self._parse(
            instructions=(
                "You are a conversational mock interviewer. Keep the interview focused on the current planned "
                "question, but respond naturally to the candidate's latest answer. Ask one concise, specific "
                "follow-up when a useful detail is missing; otherwise advance to the next planned question. "
                "If a follow-up was already asked, advance. End only when the candidate explicitly asks to stop. "
                "Use the project context only when it is relevant and never invent project details. The reply "
                "must be a natural short acknowledgement or follow-up; the server adds the next planned question. "
                "Write the reply and note in the configured language. Score 0-5 only when advancing."
            ),
            payload={
                "config": config,
                "current_question": question,
                "follow_up_count": follow_up_count,
                "recent_messages": recent_messages,
                "project_context": project_context or [],
            },
            output_type=TurnDecisionOutput,
        )

    def evaluate(self, config: dict, questions: list[dict], messages: list[dict]) -> EvaluationOutput:
        return self._parse(
            instructions=(
                "Provide evidence-based coaching feedback for a completed mock interview. Be supportive, specific, "
                "and calibrated to the target level. Return a practice score and readiness label, not a hire/no-hire "
                "decision. Write all user-facing feedback in the configured language (en means English; vi means "
                "Vietnamese). Include feedback for every supplied question ID. Skipped or unattempted questions "
                "receive score 0 with a neutral explanation."
            ),
            payload={"config": config, "questions": questions, "messages": messages},
            output_type=EvaluationOutput,
        )


def get_interview_ai_service() -> InterviewAIService:
    return InterviewAIService()
