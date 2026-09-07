import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def enum_values(enum_type: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_type]


class SessionStatus(str, enum.Enum):
    CREATING = "creating"
    IN_PROGRESS = "in_progress"
    ENDING = "ending"
    EVALUATING = "evaluating"
    SUMMARIZED = "summarized"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QuestionStatus(str, enum.Enum):
    PENDING = "pending"
    CURRENT = "current"
    ANSWERED = "answered"
    SKIPPED = "skipped"
    NOT_ATTEMPTED = "not_attempted"


class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    TOOL = "tool"


class TurnStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, values_callable=enum_values, native_enum=False, length=32),
        default=SessionStatus.CREATING,
        nullable=False,
        index=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rolling_summary: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    questions: Mapped[list["SessionQuestion"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SessionQuestion.position"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    turns: Mapped[list["InterviewTurn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class SessionQuestion(Base):
    __tablename__ = "session_questions"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_session_question_position"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 5)", name="ck_question_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    skill_tag: Mapped[str | None] = mapped_column(String(100))
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(
        Enum(QuestionStatus, values_callable=enum_values, native_enum=False, length=32), nullable=False
    )
    score: Mapped[int | None] = mapped_column(SmallInteger)
    score_note: Mapped[str | None] = mapped_column(Text)
    follow_up_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    session: Mapped[InterviewSession] = relationship(back_populates="questions")
    messages: Mapped[list["Message"]] = relationship(back_populates="question")
    feedback: Mapped[list["QuestionFeedback"]] = relationship(back_populates="question")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
        UniqueConstraint("session_id", "client_message_id", name="uq_message_client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("session_questions.id", ondelete="SET NULL")
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, values_callable=enum_values, native_enum=False, length=16), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_message_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[InterviewSession] = relationship(back_populates="messages")
    question: Mapped[SessionQuestion | None] = relationship(back_populates="messages")


class InterviewTurn(Base):
    __tablename__ = "interview_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "client_message_id", name="uq_turn_client_message"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_questions.id", ondelete="CASCADE"), nullable=False
    )
    client_message_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[TurnStatus] = mapped_column(
        Enum(TurnStatus, values_callable=enum_values, native_enum=False, length=16), default=TurnStatus.RECEIVED, nullable=False
    )
    decision: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[InterviewSession] = relationship(back_populates="turns")


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint("session_id", "version", name="uq_evaluation_session_version"),
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="ck_overall_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    overall_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    readiness: Mapped[str] = mapped_column(String(32), nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    improvements: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[InterviewSession] = relationship(back_populates="evaluations")
    competencies: Mapped[list["CompetencyScore"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    question_feedback: Mapped[list["QuestionFeedback"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class CompetencyScore(Base):
    __tablename__ = "competency_scores"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 5", name="ck_competency_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="competencies")


class QuestionFeedback(Base):
    __tablename__ = "question_feedback"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "question_id", name="uq_feedback_question"),
        CheckConstraint("score >= 0 AND score <= 5", name="ck_feedback_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="question_feedback")
    question: Mapped[SessionQuestion] = relationship(back_populates="feedback")