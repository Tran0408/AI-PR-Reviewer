import json
import logging
import re

import httpx
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.review.base import SYSTEM_PROMPT, ReviewProvider, build_user_prompt
from app.services.review.schema import ReviewOutput, ReviewRequest

log = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_FIRST_JSON_OBJ_RE = re.compile(r"(\{.*\})", re.DOTALL)


class LLMParseError(Exception):
    pass


class OpenRouterProvider(ReviewProvider):
    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 90.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(1, max_retries)

    async def review(self, req: ReviewRequest) -> ReviewOutput:
        return await self._review_with_retries(req)

    async def _review_with_retries(self, req: ReviewRequest) -> ReviewOutput:
        attempts = 0
        last_err: Exception | None = None
        while attempts < self.max_retries:
            attempts += 1
            try:
                raw = await self._call_llm(req, strict_reminder=attempts > 1)
                parsed = _extract_json(raw)
                return ReviewOutput.model_validate(parsed)
            except (LLMParseError, ValidationError, json.JSONDecodeError) as e:
                last_err = e
                log.warning("LLM parse failed (attempt %d/%d): %s", attempts, self.max_retries, e)
        raise RuntimeError(f"LLM review failed after {self.max_retries} attempts: {last_err}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _call_llm(self, req: ReviewRequest, *, strict_reminder: bool) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(req)},
        ]
        if strict_reminder:
            messages.append(
                {
                    "role": "user",
                    "content": "Your previous response was not valid JSON. Return ONLY a single JSON object matching the schema. No prose, no markdown.",
                }
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pr-reviewer",
            "X-Title": "AI PR Reviewer",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                raise LLMParseError(f"Unexpected LLM response shape: {data}") from e


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_BLOCK_RE.search(text)
    if m:
        return json.loads(m.group(1))
    m = _FIRST_JSON_OBJ_RE.search(text)
    if m:
        return json.loads(m.group(1))
    raise LLMParseError("Could not locate JSON object in LLM response")
