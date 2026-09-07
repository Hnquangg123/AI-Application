import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.models.interview import (
    CompetencyScore,
    Evaluation,
    InterviewSession,
    InterviewTurn,
    Message,
    MessageRole,
    QuestionFeedback,
    QuestionStatus,
    SessionQuestion,
    SessionStatus,
    TurnStatus,
)
from app.models.schemas import (
    AnswerRequest,
    ArchiveInterviewResponse,
    CompetencyView,
    InterviewConfigRequest,
    InterviewModeRequest,
    InterviewListItem,
    InterviewListResponse,
    InterviewResponse,
    MessageView,
    ProgressView,
    QuestionFeedbackView,
    QuestionView,
    SummaryView,
)
from app.services.interview_ai_service import InterviewAIService
from app.services.conversation_graph import run_conversation_turn
from app.services.project_service import get_project, retrieve_project_context

logger = logging.getLogger(__name__)


class InterviewService:
    def __init__(self, db: Session, ai: InterviewAIService) -> None:
        self.db = db
        self.ai = ai
        self._session_factory = sessionmaker(
            bind=db.get_bind(), expire_on_commit=False
        )

    def create(
        self,
        config: InterviewConfigRequest,
        background_tasks: BackgroundTasks | None = None,
    ) -> InterviewResponse:
        project = None
        try:
            if config.project_id:
                project = get_project(self.db, config.project_id)
            # The initial plan never waits for RAG retrieval. A project-specific
            # question is prepared independently and remains last in the plan.
            plan_config = config.model_copy(update={"project_id": None})
            plan = self.ai.generate_plan(plan_config)
        except Exception as exc:
            logger.exception("Interview plan generation failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to generate the interview plan. Please try again.",
            ) from exc

        session = InterviewSession(
            status=SessionStatus.IN_PROGRESS,
            # JSON columns cannot serialize UUID objects. JSON mode converts
            # project_id (and any future rich Pydantic types) to wire values.
            config=config.model_dump(mode="json"),
            current_question_index=0,
        )
        for index, item in enumerate(plan.questions):
            session.questions.append(
                SessionQuestion(
                    position=index,
                    title=item.title,
                    text=item.text,
                    skill_tag=item.skill_tag,
                    question_type=item.type,
                    status=QuestionStatus.CURRENT if index == 0 else QuestionStatus.PENDING,
                )
            )
        project_question = None
        if project is not None:
            project_question = SessionQuestion(
                position=len(plan.questions),
                title="Project deep dive" if config.language == "en" else "Phân tích dự án",
                text=(
                    f"Walk me through {project.name} and explain one important architecture decision and its trade-offs."
                    if config.language == "en"
                    else f"Hãy trình bày về {project.name} và giải thích một quyết định kiến trúc quan trọng cùng các đánh đổi."
                ),
                skill_tag=None,
                question_type="system_design",
                status=QuestionStatus.PENDING,
            )
            session.questions.append(project_question)

        self.db.add(session)
        self.db.flush()
        first = session.questions[0]
        greeting = "Xin chào!" if config.language == "vi" else "Hi! I’ll be your interview coach today."
        session.messages.append(
            Message(
                role=MessageRole.ASSISTANT,
                question_id=first.id,
                content=f"{greeting} {first.text}",
            )
        )
        self.db.commit()
        if background_tasks is not None and project_question is not None:
            background_tasks.add_task(
                self._prepare_project_question,
                session.id,
                project_question.id,
            )
        return self._to_response(self._load(session.id), action="created")

    def _prepare_project_question(
        self,
        session_id: UUID,
        question_id: UUID,
    ) -> None:
        """Retrieve project context and enrich the final question off the request path."""
        db = self._session_factory()
        try:
            session = db.get(InterviewSession, session_id)
            question = db.get(SessionQuestion, question_id)
            if session is None or question is None or question.status != QuestionStatus.PENDING:
                return
            config = InterviewConfigRequest.model_validate(session.config)
            if config.project_id is None:
                return
            project = get_project(db, config.project_id)
            context = [project.description.strip()] if project.description.strip() else []
            context.extend(
                retrieve_project_context(
                    db,
                    config.project_id,
                    f"{config.job_role} {' '.join(config.skills)} project architecture interview",
                )
            )
            if not context:
                return
            generated = self.ai.generate_project_question(
                config,
                project_name=project.name,
                project_context=context,
            )
            question.title = generated.title
            question.text = generated.text
            question.skill_tag = generated.skill_tag
            question.question_type = generated.type
            db.commit()
        except Exception:
            logger.exception(
                "Background project question generation failed",
                extra={"session_id": str(session_id)},
            )
            db.rollback()
        finally:
            db.close()

    def get(self, session_id: UUID) -> InterviewResponse:
        return self._to_response(self._load(session_id))

    def list_sessions(self, limit: int, offset: int, archived: bool = False) -> InterviewListResponse:
        archive_filter = (
            InterviewSession.archived_at.is_not(None)
            if archived
            else InterviewSession.archived_at.is_(None)
        )
        total = self.db.scalar(
            select(func.count(InterviewSession.id)).where(archive_filter)
        ) or 0
        statement = (
            select(InterviewSession)
            .where(archive_filter)
            .options(
                selectinload(InterviewSession.questions),
                selectinload(InterviewSession.messages),
                selectinload(InterviewSession.evaluations),
            )
            .order_by(InterviewSession.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        sessions = list(self.db.scalars(statement).unique())
        items: list[InterviewListItem] = []
        for session in sessions:
            answered = sum(question.status == QuestionStatus.ANSWERED for question in session.questions)
            completed = sum(
                question.status in (
                    QuestionStatus.ANSWERED,
                    QuestionStatus.SKIPPED,
                    QuestionStatus.NOT_ATTEMPTED,
                )
                for question in session.questions
            )
            evaluation = max(session.evaluations, key=lambda item: item.version, default=None)
            items.append(
                InterviewListItem(
                    session_id=session.id,
                    status=session.status.value,
                    config=InterviewConfigRequest.model_validate(session.config),
                    progress=ProgressView(answered=answered, completed=completed, total=len(session.questions)),
                    message_count=sum(
                        message.role in (MessageRole.ASSISTANT, MessageRole.USER)
                        for message in session.messages
                    ),
                    overall_score=evaluation.overall_score if evaluation else None,
                    readiness=evaluation.readiness if evaluation else None,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    archived_at=session.archived_at,
                )
            )
        return InterviewListResponse(items=items, total=total, limit=limit, offset=offset)

    def archive(self, session_id: UUID, archived: bool) -> ArchiveInterviewResponse:
        session = self._load(session_id)
        session.archived_at = datetime.now(timezone.utc) if archived else None
        session.version += 1
        self.db.commit()
        return ArchiveInterviewResponse(session_id=session.id, archived_at=session.archived_at)

    def delete(self, session_id: UUID) -> None:
        session = self._load(session_id)
        self.db.delete(session)
        self.db.commit()

    def set_mode(self, session_id: UUID, payload: InterviewModeRequest) -> InterviewResponse:
        session = self._load(session_id)
        self._ensure_in_progress(session)
        config = InterviewConfigRequest.model_validate(session.config)
        session.config = config.model_copy(update={"mode": payload.mode}).model_dump(mode="json")
        session.version += 1
        self.db.commit()
        return self._to_response(self._load(session.id))

    def answer(
        self, session_id: UUID, payload: AnswerRequest) -> InterviewResponse:
        session = self._load(session_id)
        self._ensure_in_progress(session)
        question = self._current_question(session)
        if question is None or question.id != payload.question_id:
            raise HTTPException(status_code=409, detail="The answer does not match the current question.")

        existing = self.db.scalar(
            select(InterviewTurn).where(
                InterviewTurn.session_id == session.id,
                InterviewTurn.client_message_id == payload.client_message_id,
            )
        )
        if existing is not None:
            action = existing.decision.get("action") if existing.decision else None
            return self._to_response(self._load(session.id), action=action)

        user_message = Message(
            session_id=session.id,
            question_id=question.id,
            role=MessageRole.USER,
            content=payload.message,
            client_message_id=payload.client_message_id,
        )
        turn = InterviewTurn(
            session_id=session.id,
            question_id=question.id,
            client_message_id=payload.client_message_id,
            status=TurnStatus.PROCESSING,
        )
        self.db.add_all([user_message, turn])
        self.db.commit()

        session = self._load(session.id)
        question = self._current_question(session)
        assert question is not None
        recent = [
            {"role": message.role.value, "content": message.content}
            for message in session.messages[-12:]
            if message.role in (MessageRole.ASSISTANT, MessageRole.USER)
        ]
        try:
            question_payload = {
                "id": str(question.id),
                "text": question.text,
                "type": question.question_type,
            }
            if session.config.get("mode") == "conversation":
                decision, _project_context = run_conversation_turn(
                    db=self.db,
                    ai=self.ai,
                    config=session.config,
                    question=question_payload,
                    recent_messages=recent,
                    follow_up_count=question.follow_up_count,
                )
            else:
                decision = self.ai.decide_turn(
                    config=session.config,
                    question=question_payload,
                    recent_messages=recent,
                    follow_up_count=question.follow_up_count,
                )
        except Exception as exc:
            logger.exception("Interview turn generation failed", extra={"session_id": str(session.id)})
            turn = self.db.get(InterviewTurn, turn.id)
            assert turn is not None
            turn.status = TurnStatus.FAILED
            turn.error_code = "model_error"
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Your answer was saved, but the coach could not respond. Retry with the same answer.",
            ) from exc

        action = decision.action
        if action == "follow_up" and question.follow_up_count >= 1:
            action = "next_question"

        reply = decision.reply.strip()
        reply_question_id = question.id
        done = False
        if action == "follow_up":
            question.follow_up_count += 1
        elif action == "end_interview":
            session.status = SessionStatus.ENDING
            done = True
        else:
            question.status = QuestionStatus.ANSWERED
            question.score = decision.score if decision.score is not None else 3
            question.score_note = decision.note
            next_question = self._next_pending(session)
            if next_question is None:
                session.status = SessionStatus.ENDING
                reply = f"{reply} We’ve covered the full question plan."
                done = True
                action = "end_interview"
            else:
                next_question.status = QuestionStatus.CURRENT
                session.current_question_index = next_question.position
                reply_question_id = next_question.id
                reply = f"{reply} {next_question.text}"
                action = "next_question"

        self.db.add(
            Message(
                session_id=session.id,
                question_id=reply_question_id,
                role=MessageRole.ASSISTANT,
                content=reply,
            )
        )
        turn = self.db.get(InterviewTurn, turn.id)
        assert turn is not None
        turn.status = TurnStatus.COMPLETED
        turn.decision = {
            "action": action,
            "reply": reply,
            "score": decision.score,
            "note": decision.note,
        }
        turn.completed_at = datetime.now(timezone.utc)
        session.version += 1
        self.db.commit()
        return self._to_response(self._load(session.id), action=action, done=done)

    def skip(self, session_id: UUID) -> InterviewResponse:
        session = self._load(session_id)
        self._ensure_in_progress(session)
        question = self._current_question(session)
        if question is None:
            raise HTTPException(status_code=409, detail="There is no current question to skip.")

        question.status = QuestionStatus.SKIPPED
        next_question = self._next_pending(session)
        if next_question is None:
            session.status = SessionStatus.ENDING
            content = "No problem. That completes the planned questions."
            action = "end_interview"
            done = True
            message_question_id = question.id
        else:
            next_question.status = QuestionStatus.CURRENT
            session.current_question_index = next_question.position
            content = f"No problem, let’s move on. {next_question.text}"
            action = "skipped"
            done = False
            message_question_id = next_question.id

        self.db.add(
            Message(
                session_id=session.id,
                question_id=message_question_id,
                role=MessageRole.ASSISTANT,
                content=content,
            )
        )
        session.version += 1
        self.db.commit()
        return self._to_response(self._load(session.id), action=action, done=done)

    def end(self, session_id: UUID) -> InterviewResponse:
        session = self._load(session_id)
        if session.status == SessionStatus.SUMMARIZED:
            return self._to_response(session, action="end_interview", done=True)
        if session.status == SessionStatus.CANCELLED:
            raise HTTPException(status_code=409, detail="This interview was cancelled.")

        for question in session.questions:
            if question.status in (QuestionStatus.PENDING, QuestionStatus.CURRENT):
                question.status = QuestionStatus.NOT_ATTEMPTED
        session.status = SessionStatus.EVALUATING
        self.db.commit()

        session = self._load(session.id)
        question_payload = [
            {
                "id": str(question.id),
                "title": question.title,
                "text": question.text,
                "status": question.status.value,
                "progressive_score": question.score,
                "score_note": question.score_note,
            }
            for question in session.questions
        ]
        message_payload = [
            {"role": message.role.value, "question_id": str(message.question_id), "content": message.content}
            for message in session.messages
            if message.role in (MessageRole.ASSISTANT, MessageRole.USER)
        ]
        try:
            result = self.ai.evaluate(session.config, question_payload, message_payload)
        except Exception as exc:
            logger.exception("Interview evaluation failed", extra={"session_id": str(session.id)})
            session.status = SessionStatus.FAILED
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The interview ended, but feedback generation failed. Please try again.",
            ) from exc

        evaluation = Evaluation(
            session_id=session.id,
            version=len(session.evaluations) + 1,
            overall_score=result.overall_score,
            readiness=result.readiness,
            strengths=result.strengths,
            improvements=result.improvements,
            summary_text=result.summary_text,
            model_metadata={"model": self.ai.model},
        )
        for competency in result.competencies:
            evaluation.competencies.append(
                CompetencyScore(name=competency.name, score=competency.score, comment=competency.comment)
            )

        feedback_by_id = {item.question_id: item for item in result.per_question}
        for question in session.questions:
            item = feedback_by_id.get(str(question.id))
            evaluation.question_feedback.append(
                QuestionFeedback(
                    question_id=question.id,
                    score=item.score if item else (question.score or 0),
                    feedback=item.feedback if item else "Not enough evidence was available for detailed feedback.",
                )
            )

        session.evaluations.append(evaluation)
        session.status = SessionStatus.SUMMARIZED
        session.version += 1
        self.db.commit()
        return self._to_response(self._load(session.id), action="end_interview", done=True)

    def summary(self, session_id: UUID) -> SummaryView:
        session = self._load(session_id)
        summary = self._summary_view(session)
        if summary is None:
            raise HTTPException(status_code=404, detail="Feedback is not available yet.")
        return summary

    def _load(self, session_id: UUID) -> InterviewSession:
        statement = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(
                selectinload(InterviewSession.questions),
                selectinload(InterviewSession.messages),
                selectinload(InterviewSession.evaluations).selectinload(Evaluation.competencies),
                selectinload(InterviewSession.evaluations).selectinload(Evaluation.question_feedback),
            )
            .execution_options(populate_existing=True)
        )
        session = self.db.scalar(statement)
        if session is None:
            raise HTTPException(status_code=404, detail="Interview session not found.")
        return session

    @staticmethod
    def _ensure_in_progress(session: InterviewSession) -> None:
        if session.status != SessionStatus.IN_PROGRESS:
            raise HTTPException(status_code=409, detail="This interview is not accepting answers.")

    @staticmethod
    def _current_question(session: InterviewSession) -> SessionQuestion | None:
        return next((question for question in session.questions if question.status == QuestionStatus.CURRENT), None)

    @staticmethod
    def _next_pending(session: InterviewSession) -> SessionQuestion | None:
        return next((question for question in session.questions if question.status == QuestionStatus.PENDING), None)

    def _to_response(
        self,
        session: InterviewSession,
        action: str | None = None,
        done: bool | None = None,
    ) -> InterviewResponse:
        question_views = [self._question_view(question) for question in session.questions]
        current = next((question for question in question_views if question.status == "current"), None)
        answered = sum(question.status == "answered" for question in question_views)
        completed = sum(question.status in ("answered", "skipped", "not_attempted") for question in question_views)
        return InterviewResponse(
            session_id=session.id,
            status=session.status.value,
            config=InterviewConfigRequest.model_validate(session.config),
            questions=question_views,
            messages=[
                MessageView(
                    id=message.id,
                    role=message.role.value,
                    content=message.content,
                    question_id=message.question_id,
                    created_at=message.created_at,
                )
                for message in session.messages
                if message.role in (MessageRole.ASSISTANT, MessageRole.USER)
            ],
            current_question=current,
            progress=ProgressView(answered=answered, completed=completed, total=len(question_views)),
            summary=self._summary_view(session),
            action=action,
            done=done if done is not None else session.status != SessionStatus.IN_PROGRESS,
        )

    @staticmethod
    def _question_view(question: SessionQuestion) -> QuestionView:
        return QuestionView(
            id=question.id,
            index=question.position,
            text=question.text,
            title=question.title,
            skill_tag=question.skill_tag,
            type=question.question_type,
            status=question.status.value,
            score=question.score,
            follow_up_count=question.follow_up_count,
        )

    @staticmethod
    def _summary_view(session: InterviewSession) -> SummaryView | None:
        if not session.evaluations:
            return None
        evaluation = max(session.evaluations, key=lambda item: item.version)
        return SummaryView(
            id=evaluation.id,
            overall_score=evaluation.overall_score,
            readiness=evaluation.readiness,
            competencies=[
                CompetencyView(name=item.name, score=item.score, comment=item.comment)
                for item in evaluation.competencies
            ],
            strengths=evaluation.strengths,
            improvements=evaluation.improvements,
            per_question=[
                QuestionFeedbackView(
                    question_id=item.question_id,
                    score=item.score,
                    feedback=item.feedback,
                )
                for item in evaluation.question_feedback
            ],
            summary_text=evaluation.summary_text,
            created_at=evaluation.created_at,
        )
