"""Tests for `lang_tools.exercises.conversational_tutor`."""

from lang_tools.exercises.conversational_tutor import ConversationalTutorExercise
from lang_tools.exercises.conversational_tutor import TutorMessage


def _fake_chain(_user_text: str, _history: list[TutorMessage]) -> TutorMessage:
    return TutorMessage(role="tutor", content="Que bom!", translation="How nice!")


def test_session_appends_user_and_tutor_messages() -> None:
    ex = ConversationalTutorExercise(chain=_fake_chain, topic="travel")
    round_ = ex.start(
        greeting=TutorMessage(role="tutor", content="Oi!", translation="Hi!"),
    )
    result = ex.submit(round_, "Oi tudo bem")
    assert result.correct is True  # no correction returned
    # greeting + user + tutor reply
    assert len(ex.history) == 3
    assert ex.history[1].role == "user"
    assert ex.history[2].role == "tutor"


def test_correction_marks_round_incorrect() -> None:
    def chain(_user_text: str, _history: list[TutorMessage]) -> TutorMessage:
        return TutorMessage(
            role="tutor",
            content="ok",
            translation="ok",
            correction="say tudo bem instead",
        )

    ex = ConversationalTutorExercise(chain=chain, topic="t")
    round_ = ex.start()
    result = ex.submit(round_, "tudo bom")
    assert result.correct is False
    assert result.feedback == "say tudo bem instead"
