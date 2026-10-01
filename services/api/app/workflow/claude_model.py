"""Claude through the Anthropic API (LLM_PROVIDER=anthropic), e.g. Claude Sonnet 5.5.

Implements the same `ModelClient` interface as the gateway client in `llm.py`: one request
per call, the reply constrained to the stage's JSON schema with structured outputs
(`output_config.format`), and provider errors mapped to `ModelError`. `CallBudget` still
validates every reply against the stage's Pydantic model.

Claude Sonnet 5.5 thinks before replying (adaptive thinking, its default), and `effort`
(LLM_EFFORT) sets how much. Thinking tokens count against `max_tokens`, hence the larger
cap here; only tokens actually generated are billed.
"""

import json
from typing import Any

import anthropic
from anthropic.types import Message, OutputConfigParam
from pydantic import BaseModel, ValidationError

from app.config import Effort
from app.workflow.llm import ModelError, ModelReply, strict_schema

# Room for thinking plus a stage reply of a few thousand tokens.
MAX_OUTPUT_TOKENS = 16000


class ClaudeModel:
    def __init__(
        self, *, model: str, api_key: str, base_url: str | None = None, effort: Effort | None = None
    ) -> None:
        self.name = f"anthropic:{model}"
        self.model = model
        self.effort = effort
        # Each budgeted call is exactly one request. Hidden SDK retries would exceed
        # both the recorded call count and the attempt's remaining timeout.
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url, max_retries=0)

    def complete(
        self, *, stage: str, system: str, prompt: str, schema: dict[str, Any], timeout: float
    ) -> ModelReply:
        output_config: OutputConfigParam = {
            "format": {"type": "json_schema", "schema": strict_schema(schema)}
        }
        if self.effort:
            output_config["effort"] = self.effort
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_config=output_config,
                timeout=timeout,
            )
        except anthropic.APITimeoutError as exc:
            raise ModelError(
                "model_timeout", "The language model did not answer in time.", retryable=True
            ) from exc
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise ModelError(
                "model_auth", "The Anthropic API rejected the configured key."
            ) from exc
        except anthropic.NotFoundError as exc:
            raise ModelError(
                "model_not_found",
                f"The Anthropic API did not find the model {self.model!r}. Check LLM_MODEL.",
            ) from exc
        except anthropic.RateLimitError as exc:
            raise ModelError(
                "model_rate_limited", "The Anthropic API is rate limiting requests.", retryable=True
            ) from exc
        except anthropic.BadRequestError as exc:
            raise ModelError(
                "model_bad_request", f"The Anthropic API rejected the request: {exc.message}"
            ) from exc
        except anthropic.APIStatusError as exc:
            raise ModelError(
                "model_error",
                f"The Anthropic API returned an error ({exc.status_code}).",
                retryable=exc.status_code >= 500,
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ModelError(
                "model_unreachable", "The Anthropic API could not be reached.", retryable=True
            ) from exc
        except (anthropic.APIError, json.JSONDecodeError) as exc:
            raise ModelError(
                "invalid_model_output", "The Anthropic API returned an unusable response."
            ) from exc
        try:
            response = Message.model_validate(
                response.model_dump(warnings=False) if isinstance(response, BaseModel) else response
            )
        except ValidationError as exc:
            raise ModelError(
                "invalid_model_output", "The Anthropic API returned an unusable response."
            ) from exc
        if response.stop_reason == "refusal":
            raise ModelError("model_refused", "The language model declined this request.")
        if response.stop_reason == "max_tokens":
            raise ModelError("model_truncated", "The language model reply was cut off.")
        text = next((b.text for b in response.content if b.type == "text"), "")
        return ModelReply(
            text,
            response.usage.input_tokens,
            response.usage.output_tokens,
            response.model or None,
        )
