from time import monotonic
from typing import cast

import httpx

from domain.entities.step import ActionResult, HttpAction, JsonValue


class HttpxActionRunner:
    def run(self, action: HttpAction) -> ActionResult:
        started_at = monotonic()
        response = httpx.request(
            method=action.method.value,
            url=action.url,
            headers=action.headers,
            json=action.body,
            timeout=action.timeout_seconds,
        )
        latency_ms = (monotonic() - started_at) * 1_000
        try:
            body = cast(JsonValue, response.json())
        except ValueError:
            body = response.text
        return ActionResult(
            status_code=response.status_code,
            latency_ms=latency_ms,
            headers=dict(response.headers),
            body=body,
        )
