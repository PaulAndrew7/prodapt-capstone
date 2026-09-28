"""The one place that calls the runtime language model (plan §4.3, §4.4, §7.4).

The submission model is GPT-4o mini, reached through the project organizers' gateway with a
key they supply. The gateway is expected to speak the OpenAI chat-completions format, so the
client is the official OpenAI SDK pointed at `LLM_BASE_URL`; nothing here assumes the public
OpenAI endpoint.

Each stage asks for JSON matching a Pydantic model. When the gateway supports it the reply
is constrained to that schema; either way it is validated here, and a stage gets at most one
repair call when validation fails. Every call counts against the run's call budget and
deadline. Provider errors become `ModelError`, which fails the run: a technical failure is
never a compliance result.
"""

import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal, Protocol

import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from app.config import get_settings

# Stage replies are a few thousand tokens at most. A lower cap also keeps a shared gateway
# quota from reserving tokens a reply will never use.
MAX_OUTPUT_TOKENS = 4096
SETUP_HINT = "Set LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL and LLM_API_KEY on the server."

JsonMode = Literal["json_schema", "json_object"]


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
    message instead. `api_key_header` sends the key in a named header (for example `api-key`)
    rather than as `Authorization: Bearer`.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        api_key_header: str | None = None,
        json_mode: JsonMode = "json_schema",
        temperature: float | None = None,
    ) -> None:
        self.name = f"gateway:{model}"
        self.model = model
        self.json_mode = json_mode
        self.temperature = temperature
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
            "response_format": {"type": "json_object"},
        }

    def complete(
        self, *, stage: str, system: str, prompt: str, schema: dict[str, Any], timeout: float
    ) -> ModelReply:
        request = self._request(stage, system, schema)
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": request["system"]},
            {"role": "user", "content": prompt},
        ]
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=request["response_format"],
                max_tokens=MAX_OUTPUT_TOKENS,
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
                f"The gateway did not find the model {self.model!r} or its endpoint. "
                "Check LLM_BASE_URL and LLM_MODEL.",
            ) from exc
        except openai.RateLimitError as exc:
            raise ModelError(
                "model_rate_limited",
                "The model gateway is rate limiting requests.",
                retryable=True,
            ) from exc
        except openai.BadRequestError as exc:
            hint = (
                " If the gateway does not support JSON schemas, set LLM_JSON_MODE=json_object."
                if self.json_mode == "json_schema"
                else ""
            )
            raise ModelError(
                "model_bad_request", f"The model gateway rejected the request (400).{hint}"
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
        if not response.choices:
            raise ModelError("model_error", "The model gateway returned no reply.")
        choice = response.choices[0]
        if choice.message.refusal:
            raise ModelError("model_refused", "The language model declined this request.")
        if choice.finish_reason == "length":
            raise ModelError("model_truncated", "The language model reply was cut off.")
        if choice.finish_reason == "content_filter":
            raise ModelError("model_refused", "The gateway's content filter blocked the reply.")
        usage = response.usage
        return ModelReply(
            choice.message.content or "",
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
            response.model or None,
        )


@lru_cache
def get_model_client() -> ModelClient | None:
    s = get_settings()
    if s.llm_provider == "none" or not (s.llm_model and s.llm_base_url and s.llm_api_key):
        return None
    return GatewayModel(
        base_url=s.llm_base_url,
        model=s.llm_model,
        api_key=s.llm_api_key.get_secret_value(),
        api_key_header=s.llm_api_key_header,
        json_mode=s.llm_json_mode,
        temperature=s.llm_temperature,
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
    input_tokens: int = 0
    output_tokens: int = 0
    served_model: str | None = None

    def remaining_seconds(self) -> float:
        return self.deadline_seconds - (time.monotonic() - self.started)

    def usage(self) -> dict[str, Any]:
        return {
            "model": self.model.name,
            "served_model": self.served_model,
            "model_calls": self.calls,
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
            reply = self.model.complete(
                stage=stage, system=system, prompt=request, schema=schema, timeout=remaining
            )
            self.input_tokens += reply.input_tokens
            self.output_tokens += reply.output_tokens
            self.served_model = reply.served_model or self.served_model
            if self.remaining_seconds() <= 0:
                raise ModelError(
                    "deadline_exceeded",
                    f"The run exceeded its {self.deadline_seconds:.0f}-second limit.",
                    retryable=True,
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
