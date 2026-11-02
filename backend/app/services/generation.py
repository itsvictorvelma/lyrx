"""Turn one learner message into a lyric draft."""

import json

from app.contracts import GenerationResponse, LyricDraft
from app.errors import DomainError
from app.generation import completion_body, confirmation
from app.groq_client import GroqClient
from app.lyrics import draft_from_model


class GenerationService:
    def __init__(self, client: GroqClient, model: str) -> None:
        self._client = client
        self._model = model

    def generate(self, instruction: str, draft: LyricDraft | None) -> GenerationResponse:
        body = completion_body(self._model, instruction, draft)
        payload = self._client.complete(body)
        parsed = draft_from_model(_content(payload))
        return GenerationResponse(message=confirmation(parsed), draft=parsed)


def _content(payload: dict[str, object]) -> object:
    status = payload.get("status_code", 200)
    data = payload.get("data")
    error = data.get("error") if isinstance(data, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if status in {429, 413} or code == "rate_limit_exceeded":
        raise DomainError("groq_rate_limited", "The lyric request hit the token limit. Wait a minute and send again.")
    if status in {401, 403}:
        raise DomainError("groq_unauthorized", "The lyric model is not connected.")
    if status == 400 or code == "json_validate_failed":
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    if status != 200:
        raise DomainError("groq_unavailable", "The lyric request failed. Send again.")
    try:
        content = data["choices"][0]["message"]["content"]  # type: ignore[index]
    except (KeyError, IndexError, TypeError) as exc:
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.") from exc
    if not isinstance(content, str):
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise DomainError("generation_invalid", "The lyrics came back in a shape that could not be used. Send again.") from exc
