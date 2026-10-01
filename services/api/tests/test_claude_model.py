"""The Claude client against a local stub server speaking the Anthropic Messages format.
No real API or key is involved; these check what goes over the wire and how replies and
errors are mapped."""

import json
import socket
from typing import Any

import pytest

from app.workflow.claude_model import ClaudeModel
from app.workflow.llm import CallBudget, ModelError
from app.workflow.validation import ValidationOutput
from tests.test_llm_gateway import Stub, stub  # noqa: F401  (the stub server fixture)


def message(text: str, *, stop: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-haiku-4-5-20251001",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": {"input_tokens": 120, "output_tokens": 30},
    }


def claude(url: str) -> ClaudeModel:
    return ClaudeModel(model="claude-haiku-4-5", api_key="test-key", base_url=url)


def call(model: ClaudeModel, timeout: float = 5) -> Any:
    return model.complete(
        stage="validation",
        system="You check evidence.",
        prompt="Check these findings.",
        schema=ValidationOutput.model_json_schema(),
        timeout=timeout,
    )


def serve(state: Stub, status: int, payload: dict[str, Any]) -> None:
    state.handler = lambda _: (status, payload)


@pytest.mark.parametrize("payload", [{}, {**message("{}"), "content": "bad"}])
def test_malformed_success_envelope_is_a_model_error(
    stub: tuple[Stub, str],  # noqa: F811
    payload: dict[str, Any],
) -> None:
    state, url = stub
    serve(state, 200, payload)
    with pytest.raises(ModelError) as exc:
        call(claude(url))
    assert exc.value.code == "invalid_model_output"
    assert "bad" not in exc.value.message


def test_request_uses_messages_api_key_and_json_schema(stub: tuple[Stub, str]) -> None:  # noqa: F811
    state, url = stub
    serve(state, 200, message('{"checks": []}'))
    reply = call(claude(url))
    request = state.requests[0]
    assert request["path"] == "/gateway/v1/v1/messages"
    assert request["headers"]["x-api-key"] == "test-key"
    body = request["body"]
    assert body["model"] == "claude-haiku-4-5"
    assert body["system"] == "You check evidence."
    assert body["messages"] == [{"role": "user", "content": "Check these findings."}]
    fmt = body["output_config"]["format"]
    assert fmt["type"] == "json_schema" and fmt["schema"]["additionalProperties"] is False
    assert "thinking" not in body and "temperature" not in body
    assert reply.text == '{"checks": []}'
    assert (reply.input_tokens, reply.output_tokens) == (120, 30)
    assert reply.served_model == "claude-haiku-4-5-20251001"


def test_effort_is_sent_and_thinking_blocks_are_skipped(stub: tuple[Stub, str]) -> None:  # noqa: F811
    state, url = stub
    reply_with_thinking = message('{"checks": []}')
    reply_with_thinking["content"].insert(0, {"type": "thinking", "thinking": "", "signature": "s"})
    serve(state, 200, reply_with_thinking)
    model = ClaudeModel(model="claude-sonnet-5-5", api_key="test-key", base_url=url, effort="low")
    reply = call(model)
    body = state.requests[0]["body"]
    assert body["output_config"]["effort"] == "low"
    assert body["max_tokens"] == 16000
    assert "thinking" not in body  # adaptive thinking is the model's default
    assert reply.text == '{"checks": []}'


def test_no_effort_is_sent_unless_configured(stub: tuple[Stub, str]) -> None:  # noqa: F811
    state, url = stub
    serve(state, 200, message('{"checks": []}'))
    call(claude(url))
    assert "effort" not in state.requests[0]["body"]["output_config"]


def test_budget_validates_the_reply(stub: tuple[Stub, str]) -> None:  # noqa: F811
    state, url = stub
    serve(state, 200, message('{"checks": []}'))
    budget = CallBudget(claude(url), max_calls=2, deadline_seconds=30)
    assert budget.structured("validation", "system", "prompt", ValidationOutput).checks == []
    assert budget.usage()["model"] == "anthropic:claude-haiku-4-5"


@pytest.mark.parametrize(
    ("status", "kind", "code", "retryable"),
    [
        (401, "authentication_error", "model_auth", False),
        (403, "permission_error", "model_auth", False),
        (404, "not_found_error", "model_not_found", False),
        (429, "rate_limit_error", "model_rate_limited", True),
        (400, "invalid_request_error", "model_bad_request", False),
        (529, "overloaded_error", "model_error", True),
    ],
)
def test_http_errors_become_model_errors(
    stub: tuple[Stub, str],  # noqa: F811
    status: int,
    kind: str,
    code: str,
    retryable: bool,
) -> None:
    state, url = stub
    serve(state, status, {"type": "error", "error": {"type": kind, "message": "nope"}})
    with pytest.raises(ModelError) as exc:
        call(claude(url))
    assert (exc.value.code, exc.value.retryable) == (code, retryable)
    assert "test-key" not in exc.value.message
    assert len(state.requests) == 1  # no hidden SDK retries


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        (message('{"checks": [', stop="max_tokens"), "model_truncated"),
        (message("", stop="refusal"), "model_refused"),
    ],
)
def test_unusable_replies_fail_clearly(
    stub: tuple[Stub, str],  # noqa: F811
    reply: dict[str, Any],
    code: str,
) -> None:
    state, url = stub
    serve(state, 200, reply)
    with pytest.raises(ModelError) as exc:
        call(claude(url))
    assert exc.value.code == code


def test_timeout_and_unreachable_are_reported(stub: tuple[Stub, str]) -> None:  # noqa: F811
    state, url = stub
    serve(state, 200, message("{}"))
    state.delay = 1.0
    with pytest.raises(ModelError) as exc:
        call(claude(url), timeout=0.2)
    assert exc.value.code == "model_timeout" and exc.value.retryable
    with socket.socket() as probe:  # a port with nothing listening
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(ModelError) as exc:
        call(claude(f"http://127.0.0.1:{port}"), timeout=20)
    assert exc.value.code == "model_unreachable" and exc.value.retryable


def test_schema_sent_is_closed_everywhere(stub: tuple[Stub, str]) -> None:  # noqa: F811
    state, url = stub
    serve(state, 200, message('{"checks": []}'))
    call(claude(url))
    schema = json.dumps(state.requests[0]["body"]["output_config"]["format"]["schema"])
    assert '"const"' not in schema and '"additionalProperties": true' not in schema
