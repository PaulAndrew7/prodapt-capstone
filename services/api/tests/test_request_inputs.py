import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.contracts import NewCaseRequest, NewMessageRequest, SearchRequest


@pytest.mark.parametrize("text", [" " * 30, "\t\n" * 15, "\u2003" * 30, " " * 20 + "short"])
def test_scenario_length_is_checked_after_trimming(text: str) -> None:
    with pytest.raises(ValidationError):
        NewCaseRequest(text=text, business_area="Sales", as_of="2026-09-27")


def test_business_area_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        NewCaseRequest(
            text="A sufficiently detailed scenario", business_area=" \t ", as_of="2026-09-27"
        )


@pytest.mark.parametrize("text", [" ", "\r\n\t", "\u2003"])
def test_follow_up_cannot_be_blank(text: str) -> None:
    with pytest.raises(ValidationError):
        NewMessageRequest(text=text)


@pytest.mark.parametrize("text", ["  ", "\r\n\t", "  x  "])
def test_question_length_is_checked_after_trimming(text: str) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(question=text)


def test_nonblank_inputs_are_normalized() -> None:
    case = NewCaseRequest(
        text="  A sufficiently detailed scenario  ", business_area=" Sales ", as_of="2026-09-27"
    )
    assert case.text == "A sufficiently detailed scenario" and case.business_area == "Sales"
    assert NewMessageRequest(text="  No approval yet. \n").text == "No approval yet."
    assert SearchRequest(question="  Who approves? \t").question == "Who approves?"


@pytest.mark.db
@pytest.mark.parametrize("route", ["search", "lookup"])
def test_blank_questions_are_rejected_before_model_or_retrieval(
    client: TestClient, route: str
) -> None:
    response = client.post(f"/api/v1/{route}", json={"question": "   "})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
