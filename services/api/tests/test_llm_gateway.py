"""The gateway client against a local stub server speaking the OpenAI chat-completions format.
No real gateway or key is involved; these check what goes over the wire and how replies and
errors are mapped."""

import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from app.workflow.analysis import AnalysisOutput
from app.workflow.llm import (
    MAX_CONTINUATIONS,
    CallBudget,
    GatewayModel,
    ModelError,
    join_continuation,
    strict_schema,
)
from app.workflow.validation import ValidationOutput
from tests.scripted import ScriptedModel


def test_failed_request_consumes_budget() -> None:
    model = ScriptedModel(validation=[ModelError("model_error", "Unavailable")])
    budget = CallBudget(model, max_calls=1, deadline_seconds=30)
    with pytest.raises(ModelError, match="Unavailable"):
        budget.structured("validation", "system", "prompt", ValidationOutput)
    assert budget.calls == 1
    with pytest.raises(ModelError) as exc:
        budget.structured("validation", "system", "prompt", ValidationOutput)
    assert exc.value.code == "budget_exhausted"
    assert len(model.calls) == 1


def test_late_valid_reply_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [100.0]
    monkeypatch.setattr("app.workflow.llm.time.monotonic", lambda: clock[0])

    def late_reply(_: str) -> dict[str, Any]:
        clock[0] = 131.0
        return {"checks": []}

    model = ScriptedModel(validation=[late_reply])
    budget = CallBudget(model, max_calls=2, deadline_seconds=30, started=clock[0])
    with pytest.raises(ModelError) as exc:
        budget.structured("validation", "system", "prompt", ValidationOutput)
    assert exc.value.code == "deadline_exceeded"
    assert budget.calls == 1 and budget.input_tokens == 100


def test_per_call_timeout_is_capped_and_a_late_reply_cannot_be_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [100.0]
    monkeypatch.setattr("app.workflow.llm.time.monotonic", lambda: clock[0])

    class SlowModel:
        name = "slow:test"

        def complete(self, **kwargs: Any) -> Any:
            assert kwargs["timeout"] == 20
            clock[0] += 21
            from app.workflow.llm import ModelReply

            return ModelReply('{"checks": []}')

    budget = CallBudget(SlowModel(), 2, 120, started=clock[0], call_timeout_seconds=20)
    with pytest.raises(ModelError) as exc:
        budget.structured("validation", "system", "prompt", ValidationOutput)
    assert exc.value.code == "model_timeout" and budget.calls == 1


Handler = Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]


def completion(content: str, *, finish: str = "stop", refusal: str | None = None) -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o-mini-2024-07-18",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
    }


class Stub:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.handler: Handler = lambda _: (200, completion('{"checks": []}'))
        self.delay = 0.0


@pytest.fixture
def stub() -> Iterator[tuple[Stub, str]]:
    state = Stub()

    class RequestHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            headers = {k.lower(): v for k, v in self.headers.items()}
            request = {"path": self.path, "headers": headers, "body": body}
            state.requests.append(request)
            time.sleep(state.delay)
            status, payload = state.handler(request)
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("retry-after-ms", "1")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), RequestHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield state, f"http://127.0.0.1:{server.server_address[1]}/gateway/v1"
    server.shutdown()
    server.server_close()


def gateway(base_url: str, **kwargs: Any) -> GatewayModel:
    return GatewayModel(base_url=base_url, model="gpt-4o-mini", api_key="test-key", **kwargs)


def call(model: GatewayModel, timeout: float = 5) -> Any:
    return model.complete(
        stage="validation",
        system="You check evidence.",
        prompt="Check these findings.",
        schema=ValidationOutput.model_json_schema(),
        timeout=timeout,
    )


@pytest.mark.parametrize("payload", [{}, {**completion("{}"), "choices": "bad"}])
def test_malformed_success_envelope_is_a_model_error(
    stub: tuple[Stub, str], payload: dict[str, Any]
) -> None:
    state, url = stub
    state.handler = lambda _: (200, payload)
    with pytest.raises(ModelError) as exc:
        call(gateway(url))
    assert exc.value.code == "invalid_model_output"
    assert "bad" not in exc.value.message


def test_strict_schema_closes_every_object() -> None:
    schema = strict_schema(AnalysisOutput.model_json_schema())
    objects = [schema, *schema["$defs"].values()]
    for obj in objects:
        assert obj["additionalProperties"] is False
        assert obj["required"] == list(obj["properties"])
    text = json.dumps(strict_schema(ValidationOutput.model_json_schema()))
    assert '"const"' not in text and '"enum": ["unknown"]' in text


def test_request_uses_base_url_bearer_key_and_json_schema(stub: tuple[Stub, str]) -> None:
    state, url = stub
    reply = call(gateway(url, temperature=0))
    request = state.requests[0]
    assert request["path"] == "/gateway/v1/chat/completions"
    assert request["headers"]["authorization"] == "Bearer test-key"
    body = request["body"]
    assert body["model"] == "gpt-4o-mini"
    assert body["temperature"] == 0
    assert body["messages"][0] == {"role": "system", "content": "You check evidence."}
    fmt = body["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "validation" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["schema"]["additionalProperties"] is False
    assert reply.text == '{"checks": []}'
    assert (reply.input_tokens, reply.output_tokens) == (120, 30)
    assert reply.served_model == "gpt-4o-mini-2024-07-18"


def test_model_is_not_sent_when_the_gateway_chooses_it(stub: tuple[Stub, str]) -> None:
    state, url = stub
    model = GatewayModel(base_url=url, model=None, api_key="test-key")
    reply = call(model)
    assert "model" not in state.requests[0]["body"]
    assert model.name == "gateway:server-default"
    assert reply.served_model == "gpt-4o-mini-2024-07-18"


def test_temperature_is_omitted_unless_configured(stub: tuple[Stub, str]) -> None:
    state, url = stub
    call(gateway(url))
    assert "temperature" not in state.requests[0]["body"]


def test_named_key_header_replaces_bearer(stub: tuple[Stub, str]) -> None:
    state, url = stub
    call(gateway(url, api_key_header="api-key"))
    headers = state.requests[0]["headers"]
    assert headers["api-key"] == "test-key"
    assert "authorization" not in headers


def test_json_object_mode_puts_schema_in_system_message(stub: tuple[Stub, str]) -> None:
    state, url = stub
    call(gateway(url, json_mode="json_object"))
    body = state.requests[0]["body"]
    assert body["response_format"] == {"type": "json_object"}
    system = body["messages"][0]["content"]
    assert system.startswith("You check evidence.") and '"finding_id"' in system


def test_json_mode_sends_the_plain_string_form(stub: tuple[Stub, str]) -> None:
    """The organizers' gateway accepts only `"json"` or `"text"` and at most 500 tokens."""
    state, url = stub
    call(gateway(url, json_mode="json", max_output_tokens=500))
    body = state.requests[0]["body"]
    assert body["response_format"] == "json" and body["max_tokens"] == 500
    assert '"finding_id"' in body["messages"][0]["content"]


def test_cut_off_reply_is_continued_and_joined(stub: tuple[Stub, str]) -> None:
    state, url = stub
    parts = iter([completion('{"checks": [', finish="length"), completion("]}")])
    state.handler = lambda _: (200, next(parts))
    budget = CallBudget(gateway(url, json_mode="json"), max_calls=4, deadline_seconds=30)
    out = budget.structured("validation", "system", "prompt", ValidationOutput)
    assert out.checks == []
    second = state.requests[1]["body"]
    assert second["response_format"] == "text"
    assert second["messages"][2] == {"role": "assistant", "content": '{"checks": ['}
    assert "Continue it from exactly where it stopped" in second["messages"][3]["content"]
    usage = budget.usage()
    assert (usage["model_calls"], usage["model_requests"]) == (1, 2)
    assert (usage["input_tokens"], usage["output_tokens"]) == (240, 60)


def test_continuation_resumes_at_the_last_complete_line(stub: tuple[Stub, str]) -> None:
    """Seen on the organizers' gateway: cut mid-line, the model rewrites that line whole."""
    state, url = stub
    first = '{\n  "checks": [],\n  "note": "cut o'
    parts = iter([completion(first, finish="length"), completion('  "note": "cut off"\n}')])
    state.handler = lambda _: (200, next(parts))
    reply = call(gateway(url, json_mode="json"))
    assert state.requests[1]["body"]["messages"][2]["content"] == '{\n  "checks": [],\n'
    assert json.loads(reply.text) == {"checks": [], "note": "cut off"}


@pytest.mark.parametrize(
    ("text", "more", "joined"),
    [
        ('{"a": 1, ', '"b": 2}', '{"a": 1, "b": 2}'),  # a clean continuation
        ('{"a": 1, "long_key": ', '"long_key": 2}', '{"a": 1, "long_key": 2}'),  # a repeat
        ('{"a": 1, ', '```json\n"b": 2}\n```', '{"a": 1, "b": 2}'),  # a code fence
    ],
)
def test_join_continuation_drops_repeats_and_fences(text: str, more: str, joined: str) -> None:
    assert join_continuation(text, more) == joined


def test_budget_records_served_model_and_validates(stub: tuple[Stub, str]) -> None:
    state, url = stub
    state.handler = lambda _: (200, completion('{"checks": []}'))
    budget = CallBudget(gateway(url), max_calls=4, deadline_seconds=30)
    out = budget.structured("validation", "system", "prompt", ValidationOutput)
    assert out.checks == []
    assert budget.usage()["served_model"] == "gpt-4o-mini-2024-07-18"
    assert budget.usage()["model"] == "gateway:gpt-4o-mini"


@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (401, "model_auth", False),
        (403, "model_auth", False),
        (404, "model_not_found", False),
        (429, "model_rate_limited", True),
        (400, "model_bad_request", False),
        (422, "model_bad_request", False),
        (500, "model_error", True),
    ],
)
def test_http_errors_become_model_errors(
    stub: tuple[Stub, str], status: int, code: str, retryable: bool
) -> None:
    state, url = stub
    state.handler = lambda _: (status, {"error": {"message": "nope", "type": "x"}})
    with pytest.raises(ModelError) as exc:
        call(gateway(url))
    assert (exc.value.code, exc.value.retryable) == (code, retryable)
    assert "test-key" not in exc.value.message
    if status == 400:
        assert "LLM_JSON_MODE=json_object" in exc.value.message


def test_rate_limit_does_not_make_hidden_requests(stub: tuple[Stub, str]) -> None:
    state, url = stub
    state.handler = lambda _: (429, {"error": {"message": "slow down"}})
    with pytest.raises(ModelError):
        call(gateway(url))
    assert len(state.requests) == 1


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        (completion('{"checks": [', finish="length"), "model_truncated"),
        (completion("", refusal="I can't help with that."), "model_refused"),
        (completion("", finish="content_filter"), "model_refused"),
    ],
)
def test_unusable_replies_fail_clearly(
    stub: tuple[Stub, str], reply: dict[str, Any], code: str
) -> None:
    state, url = stub
    state.handler = lambda _: (200, reply)
    with pytest.raises(ModelError) as exc:
        call(gateway(url))
    assert exc.value.code == code
    # Only a cut-off reply is continued, and only a bounded number of times.
    assert len(state.requests) == (1 + MAX_CONTINUATIONS if code == "model_truncated" else 1)


def test_timeout_is_reported(stub: tuple[Stub, str]) -> None:
    state, url = stub
    state.delay = 1.0
    with pytest.raises(ModelError) as exc:
        call(gateway(url), timeout=0.2)
    assert exc.value.code == "model_timeout" and exc.value.retryable


def test_unreachable_gateway_is_reported() -> None:
    with socket.socket() as probe:  # a port with nothing listening
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with pytest.raises(ModelError) as exc:
        call(gateway(f"http://127.0.0.1:{port}/v1"), timeout=20)
    assert exc.value.code == "model_unreachable" and exc.value.retryable
