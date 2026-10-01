"""The one place that calls the runtime language model (plan §4.3, §4.4, §7.4).

Two clients share one interface, chosen by LLM_PROVIDER: `anthropic` calls Claude (for
example Claude Sonnet 5.5) through the Anthropic SDK (`claude_model.py`); `openai_compatible`
is the official OpenAI SDK pointed at `LLM_BASE_URL`, for a gateway speaking the OpenAI
chat-completions format such as the organizers' GPT-4o mini.

Each stage asks for JSON matching a Pydantic model. When the gateway supports it the reply
is constrained to that schema; either way it is validated here, and a stage gets at most one
repair call when validation fails. Every call counts against the run's call budget and
deadline. Provider errors become `ModelError`; automatic mode switches to an explicitly
labelled local evidence review, while required mode fails the run. An unchecked scenario
never becomes compliant because of a technical failure.
"""

import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal, Protocol, cast

import openai
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from app.config import get_settings

# Stage replies are a few thousand tokens at most. A lower cap also keeps a shared gateway
# quota from reserving tokens a reply will never use.
MAX_OUTPUT_TOKENS = 4096
# A reply cut off at the output cap is continued with follow-up requests, at most this many.
# The organizers' gateway caps each reply at 500 tokens; an analysis reply can need ~1,000.
MAX_CONTINUATIONS = 3
CONTINUE_PROMPT = (
    "Your reply was cut off by the length limit. Continue it from exactly where it stopped: "
    "output only the remaining characters, repeating nothing and adding no code fences."
)
# Shorter shared text at a seam is left alone: it could be a legitimate repeat.
MIN_OVERLAP = 8


def join_continuation(text: str, more: str) -> str:
    """Appends a continuation, dropping code fences and any text it repeats from the end of
    `text` (GPT-4o mini often restarts the line it was cut off in)."""
    more = more.strip("\n")
    if more.startswith("```"):
        more = more.split("\n", 1)[1] if "\n" in more else ""
    if more.rstrip().endswith("```"):
        more = more.rstrip()[:-3].rstrip("\n")
    for k in range(min(len(text), len(more)), MIN_OVERLAP - 1, -1):
        if text.endswith(more[:k]):
            return text + more[k:]
    return text + more


SETUP_HINT = (
    "Set LLM_PROVIDER, LLM_MODEL and LLM_API_KEY on the server "
    "(and LLM_BASE_URL for an OpenAI-compatible gateway)."
)

JsonMode = Literal["json_schema", "json_object", "json"]


class ModelError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass
class ModelReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    # The model the gateway reports having used, which may differ from the requested alias.
    served_model: str | None = None
    # HTTP requests behind this reply: 1, plus any continuations of a cut-off reply.
    requests: int = 1


class ModelClient(Protocol):
    name: str

    def complete(
        self, *, stage: str, system: str, prompt: str, schema: dict[str, Any], timeout: float
    ) -> ModelReply: ...


def strict_schema(node: Any) -> Any:
    """Adapts a Pydantic JSON Schema to OpenAI strict structured outputs: every object is
    closed (`additionalProperties: false`) and lists all of its properties as required, and
    `const` is written as a one-value `enum`. The workflow models declare every field without
    a default, so requiring all of them does not change what they accept."""
    if isinstance(node, list):
        return [strict_schema(item) for item in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "default":
            continue
        if key in ("properties", "$defs"):
            out[key] = {name: strict_schema(sub) for name, sub in value.items()}
        else:
            out[key] = strict_schema(value)
    if "const" in out:
        out["enum"] = [out.pop("const")]
    if out.get("type") == "object":
        out["additionalProperties"] = False
        out["required"] = list(out.get("properties", {}))
    return out


class GatewayModel:
    """A chat-completions model behind an OpenAI-compatible gateway.

    `json_mode="json_schema"` asks the gateway to constrain replies to the stage schema;
    `"json_object"` is for gateways without schema support and puts the schema in the system
    message instead; `"json"` does the same but sends `response_format: "json"` as a plain
    string, the only form the organizers' gateway accepts. `api_key_header` sends the key in
    a named header (for example `api-key`) rather than as `Authorization: Bearer`.
    `model=None` sends no model name, for gateways that choose the model themselves (the
    organizers' gateway always serves gpt-4o-mini). A reply cut off at `max_output_tokens` is
    continued with up to `MAX_CONTINUATIONS` follow-up requests and joined.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str | None,
        api_key: str,
        api_key_header: str | None = None,
        json_mode: JsonMode = "json_schema",
        temperature: float | None = None,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
    ) -> None:
        self.name = f"gateway:{model or 'server-default'}"
        self.model = model
        self.json_mode = json_mode
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        # Each budgeted call is exactly one request. Hidden SDK retries would exceed
        # both the recorded call count and the attempt's remaining timeout.
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url, max_retries=0)
        self._headers: dict[str, Any] | None = (
            {"Authorization": openai.Omit(), api_key_header: api_key} if api_key_header else None
        )

    def _request(self, stage: str, system: str, schema: dict[str, Any]) -> dict[str, Any]:
        if self.json_mode == "json_schema":
            return {
                "system": system,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": stage, "schema": strict_schema(schema), "strict": True},
                },
            }
        return {
            "system": f"{system}\n\nReply with one JSON object that matches this JSON Schema "
            f"exactly:\n{json.dumps(schema)}",
            "response_format": "json" if self.json_mode == "json" else {"type": "json_object"},
        }

    def complete(
        self, *, stage: str, system: str, prompt: str, schema: dict[str, Any], timeout: float
    ) -> ModelReply:
        request = self._request(stage, system, schema)
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": request["system"]},
            {"role": "user", "content": prompt},
        ]
        started = time.monotonic()
        response_format = request["response_format"]
        reply = ModelReply("", requests=0)
        while True:
            response = self._send(messages, response_format, timeout - (time.monotonic() - started))
            reply.requests += 1
            if not response.choices:
                raise ModelError("model_error", "The model gateway returned no reply.")
            choice = response.choices[0]
            if choice.message.refusal:
                raise ModelError("model_refused", "The language model declined this request.")
            if choice.finish_reason == "content_filter":
                raise ModelError("model_refused", "The gateway's content filter blocked the reply.")
            usage = response.usage
            content = choice.message.content or ""
            reply.text = join_continuation(reply.text, content) if reply.requests > 1 else content
            reply.input_tokens += usage.prompt_tokens if usage else 0
            reply.output_tokens += usage.completion_tokens if usage else 0
            reply.served_model = response.model or reply.served_model
            if choice.finish_reason != "length":
                return reply
            if reply.requests > MAX_CONTINUATIONS:
                raise ModelError("model_truncated", "The language model reply was cut off.")
            if timeout - (time.monotonic() - started) <= 1:
                raise ModelError(
                    "model_timeout", "The language model did not answer in time.", retryable=True
                )
            # Resume at the last complete line: the model rewrites a cut-off line from its start
            # and can drop characters at a mid-line seam.
            line_end = reply.text.rfind("\n")
            if line_end > 0:
                reply.text = reply.text[: line_end + 1]
            # Plain text for the rest: a JSON mode would make the model start a new object.
            messages = [
                *messages[:2],
                {"role": "assistant", "content": reply.text},
                {"role": "user", "content": CONTINUE_PROMPT},
            ]
            response_format = "text" if self.json_mode == "json" else openai.omit

    def _send(
        self, messages: list[ChatCompletionMessageParam], response_format: Any, timeout: float
    ) -> Any:
        try:
            response = self._client.chat.completions.create(
                # An omitted model is stripped from the request body by the SDK.
                model=self.model or cast(str, openai.omit),
                messages=messages,
                response_format=response_format,
                max_tokens=self.max_output_tokens,
                temperature=self.temperature if self.temperature is not None else openai.omit,
                timeout=timeout,
                extra_headers=self._headers,
            )
        except openai.APITimeoutError as exc:
            raise ModelError(
                "model_timeout", "The language model did not answer in time.", retryable=True
            ) from exc
        except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
            raise ModelError(
                "model_auth", "The model gateway rejected the configured API key."
            ) from exc
        except openai.NotFoundError as exc:
            raise ModelError(
                "model_not_found",
                f"The gateway did not find the model {self.model or '(server default)'!r} or "
                "its endpoint. Check LLM_BASE_URL and LLM_MODEL.",
            ) from exc
        except openai.RateLimitError as exc:
            raise ModelError(
                "model_rate_limited",
                "The model gateway is rate limiting requests.",
                retryable=True,
            ) from exc
        except (openai.BadRequestError, openai.UnprocessableEntityError) as exc:
            hint = (
                " If the gateway does not support JSON schemas, set LLM_JSON_MODE=json_object "
                "(or json for the organizers' gateway)."
                if self.json_mode == "json_schema"
                else " Check LLM_JSON_MODE and LLM_MAX_OUTPUT_TOKENS against what it accepts."
            )
            raise ModelError(
                "model_bad_request",
                f"The model gateway rejected the request ({exc.status_code}).{hint}",
            ) from exc
        except openai.APIStatusError as exc:
            raise ModelError(
                "model_error",
                f"The model gateway returned an error ({exc.status_code}).",
                retryable=exc.status_code >= 500,
            ) from exc
        except openai.APIConnectionError as exc:
            raise ModelError(
                "model_unreachable",
                "The model gateway could not be reached.",
                retryable=True,
            ) from exc
        except (openai.APIError, json.JSONDecodeError) as exc:
            raise ModelError(
                "invalid_model_output", "The model gateway returned an unusable response."
            ) from exc
        # SDKs may construct partially populated objects for malformed 200 responses.
        # Validate the provider envelope before dereferencing fields used below.
        try:
            return ChatCompletion.model_validate(
                response.model_dump(warnings=False) if isinstance(response, BaseModel) else response
            )
        except ValidationError as exc:
            raise ModelError(
                "invalid_model_output", "The model gateway returned an unusable response."
            ) from exc


@lru_cache
def get_model_client() -> ModelClient | None:
    s = get_settings()
    if s.llm_mode == "offline" or s.llm_provider == "none" or not s.llm_api_key:
        return None
    if not s.llm_api_key.get_secret_value().strip():
        return None
    if s.llm_provider == "anthropic":
        from app.workflow.claude_model import ClaudeModel

        if not s.llm_model:
            return None
        return ClaudeModel(
            model=s.llm_model, api_key=s.llm_api_key.get_secret_value(), effort=s.llm_effort
        )
    if not s.llm_base_url:
        return None
    return GatewayModel(
        base_url=s.llm_base_url,
        model=s.llm_model or None,
        api_key=s.llm_api_key.get_secret_value(),
        api_key_header=s.llm_api_key_header,
        json_mode=s.llm_json_mode,
        temperature=s.llm_temperature,
        max_output_tokens=s.llm_max_output_tokens,
    )


def require_model(model: ModelClient | None) -> ModelClient:
    if model is None:
        raise ModelError("model_not_configured", f"No language model is configured. {SETUP_HINT}")
    return model


@dataclass
class CallBudget:
    """Counts model calls and tokens for one attempt and enforces its limits."""

    model: ModelClient
    max_calls: int
    deadline_seconds: float
    started: float = field(default_factory=time.monotonic)
    calls: int = 0
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    served_model: str | None = None
    call_timeout_seconds: float | None = None

    def remaining_seconds(self) -> float:
        return self.deadline_seconds - (time.monotonic() - self.started)

    def usage(self) -> dict[str, Any]:
        return {
            "model": self.model.name,
            "served_model": self.served_model,
            "model_calls": self.calls,
            "model_requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }

    def structured[T: BaseModel](self, stage: str, system: str, prompt: str, output: type[T]) -> T:
        schema = output.model_json_schema()
        request = prompt
        for attempt in range(2):
            if self.calls >= self.max_calls:
                raise ModelError(
                    "budget_exhausted",
                    f"The run reached its limit of {self.max_calls} model calls.",
                )
            remaining = self.remaining_seconds()
            if remaining <= 1:
                raise ModelError(
                    "deadline_exceeded",
                    f"The run exceeded its {self.deadline_seconds:.0f}-second limit.",
                    retryable=True,
                )
            self.calls += 1
            timeout = min(remaining, self.call_timeout_seconds or remaining)
            sent = time.monotonic()
            reply = self.model.complete(
                stage=stage, system=system, prompt=request, schema=schema, timeout=timeout
            )
            self.requests += reply.requests
            self.input_tokens += reply.input_tokens
            self.output_tokens += reply.output_tokens
            self.served_model = reply.served_model or self.served_model
            if self.remaining_seconds() <= 0:
                raise ModelError(
                    "deadline_exceeded",
                    f"The run exceeded its {self.deadline_seconds:.0f}-second limit.",
                    retryable=True,
                )
            if time.monotonic() - sent > timeout:
                raise ModelError(
                    "model_timeout", "The model call exceeded its time limit.", retryable=True
                )
            try:
                return output.model_validate_json(reply.text)
            except ValidationError as exc:
                if attempt == 1:
                    raise ModelError(
                        "invalid_model_output",
                        f"The {stage} stage returned output that does not match its schema.",
                    ) from exc
                problems = "; ".join(
                    f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:5]
                )
                request = (
                    f"{prompt}\n\nYour previous reply did not match the required JSON schema "
                    f"({problems}). Reply again with JSON that matches the schema exactly."
                )
        raise AssertionError("unreachable")
