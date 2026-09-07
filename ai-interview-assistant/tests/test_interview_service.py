"""TODO BE-L3 — unit tests for the turn decision apply-logic (with a mocked LLM).

Implement against app/services/interview_service.py. Mock llm_tools.call_with_tool to return
each action and assert the session state transitions.
"""
import pytest

pytestmark = pytest.mark.skip(reason="TODO BE-L3: implement interview turn tests")


def test_follow_up_keeps_same_question():
    ...  # TODO BE-L3


def test_next_question_advances_and_records_score():
    ...  # TODO BE-L3


def test_follow_up_cap_forces_next_question():
    ...  # TODO BE-L3


def test_end_interview_marks_session_ended():
    ...  # TODO BE-L3
