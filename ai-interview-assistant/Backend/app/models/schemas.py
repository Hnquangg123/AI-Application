from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    reply: str


Level = Literal["intern", "fresher", "junior", "mid", "senior", "lead"]
InterviewStyle = Literal["technical", "behavioral", "mixed"]
Language = Literal["vi", "en"]
InterviewMode = Literal["structured", "conversation"]


class InterviewConfigRequest(BaseModel):
    job_role: str = Field(min_length=2, max_length=120)
    level: Level
    skills: list[str] = Field(min_length=1, max_length=12)
    job_description: str | None = Field(default=None, max_length=12000)
    num_questions: int = Field(default=6, ge=1, le=12)
    language: Language = "en"
    style: InterviewStyle = "mixed"
    mode: InterviewMode = "structured"
    project_id: UUID | None = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if not cleaned:
            raise ValueError("At least one skill is required")
        return list(dict.fromkeys(cleaned))


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=5000)


class ProjectUpdateRequest(ProjectCreateRequest):
    pass


class ProjectDataCreateRequest(BaseModel):
    source_type: Literal["text", "image"]
    source_content: str = Field(min_length=1, max_length=2_000_000)


class ProjectDataView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_section_id: UUID | None = None
    chunk_index: int | None = None
    source_type: str
    status: str
    extracted_text: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class ProjectSectionBlock(BaseModel):
    type: Literal["text", "image"]
    value: str = Field(min_length=1, max_length=2_000_000)
    caption: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_block(self) -> "ProjectSectionBlock":
        self.value = self.value.strip()
        if not self.value:
            raise ValueError("Section blocks cannot be empty")
        if self.type == "image" and not self.value.startswith("data:image/"):
            raise ValueError("Image blocks must contain a data:image/... URL")
        return self


class ProjectSectionContent(BaseModel):
    blocks: list[ProjectSectionBlock] = Field(default_factory=list, max_length=100)


class ProjectSectionCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    content: ProjectSectionContent = Field(default_factory=ProjectSectionContent)
    sort_order: int = Field(default=0, ge=0, le=10000)


class ProjectSectionUpdateRequest(ProjectSectionCreateRequest):
    pass


class ProjectSectionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    slug: str
    content: ProjectSectionContent
    sort_order: int
    indexing_status: str
    indexing_error: str | None
    created_at: datetime
    updated_at: datetime


class ProjectView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    data: list[ProjectDataView]
    sections: list[ProjectSectionView] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class QuestionView(BaseModel):
    id: UUID
    index: int
    text: str
    title: str
    skill_tag: str | None
    type: str
    status: str
    score: int | None
    follow_up_count: int


class MessageView(BaseModel):
    id: UUID
    role: str
    content: str
    question_id: UUID | None
    created_at: datetime


class ProgressView(BaseModel):
    answered: int
    completed: int
    total: int


class CompetencyView(BaseModel):
    name: str
    score: int
    comment: str


class QuestionFeedbackView(BaseModel):
    question_id: UUID
    score: int
    feedback: str


class SummaryView(BaseModel):
    id: UUID
    overall_score: int
    readiness: str
    competencies: list[CompetencyView]
    strengths: list[str]
    improvements: list[str]
    per_question: list[QuestionFeedbackView]
    summary_text: str
    created_at: datetime


class InterviewResponse(BaseModel):
    session_id: UUID
    status: str
    config: InterviewConfigRequest
    questions: list[QuestionView]
    messages: list[MessageView]
    current_question: QuestionView | None
    progress: ProgressView
    summary: SummaryView | None = None
    action: Literal["created", "follow_up", "next_question", "skipped", "end_interview"] | None = None
    done: bool = False


class InterviewListItem(BaseModel):
    session_id: UUID
    status: str
    config: InterviewConfigRequest
    progress: ProgressView
    message_count: int
    overall_score: int | None
    readiness: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class InterviewListResponse(BaseModel):
    items: list[InterviewListItem]
    total: int
    limit: int
    offset: int

class ArchiveInterviewRequest(BaseModel):
    archived: bool


class ArchiveInterviewResponse(BaseModel):
    session_id: UUID
    archived_at: datetime | None


class InterviewModeRequest(BaseModel):
    mode: InterviewMode


class AnswerRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    question_id: UUID
    client_message_id: str = Field(min_length=8, max_length=100)
