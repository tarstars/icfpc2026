"""Small, deterministic client for the documented ICFPC 2026 API."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx
from typing_extensions import Self

DEFAULT_BASE_URL = "https://icfpcontest2026.com/api/v1"
MAX_PROGRAM_BYTES = 10_000_000
TERMINAL_SUBMISSION_STATUSES = frozenset({"done", "failed"})
USER_AGENT = "icfpc2026-tools/0.1 (+contest team)"


class ContestApiError(RuntimeError):
    """A structured error returned by the contest API."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
    ) -> None:
        super().__init__(f"{status_code} {code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message


class MissingApiKeyError(RuntimeError):
    """An authenticated operation was requested without a bearer key."""


class ContestApiClient:
    """Access public problems and the current team's submissions.

    The bearer key is attached only to submission endpoints. Public requests
    deliberately omit it.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def list_problems(self) -> list[dict[str, Any]]:
        """Return every released problem."""

        document = self._request("GET", "public/problems")
        if not isinstance(document, list):
            raise ContestApiError(
                status_code=200,
                code="invalid_response",
                message="problem list was not a JSON array",
            )
        return document

    def get_problem(self, slug: str) -> dict[str, Any]:
        """Return one released problem and its public tests."""

        return self._request_object(
            "GET",
            f"public/problems/{quote(slug, safe='')}",
        )

    def get_contest_clock(self) -> dict[str, Any]:
        """Return the live contest clock and freeze state."""

        return self._request_object("GET", "public/contest-clock")

    def submit(self, *, problem_id: str, program: str) -> dict[str, Any]:
        """Create exactly one submission.

        This method never retries: an ambiguous network failure must not create
        duplicate contest submissions.
        """

        program_bytes = len(program.encode("utf-8"))
        if program_bytes > MAX_PROGRAM_BYTES:
            raise ValueError(
                f"program is {program_bytes} UTF-8 bytes; limit is {MAX_PROGRAM_BYTES}"
            )
        return self._request_object(
            "POST",
            "submissions",
            authenticated=True,
            json={"problemId": problem_id, "program": program},
        )

    def get_submission(self, submission_id: str) -> dict[str, Any]:
        """Return one submission owned by the authenticated team."""

        return self._request_object(
            "GET",
            f"submissions/{quote(submission_id, safe='')}",
            authenticated=True,
        )

    def wait_for_submission(
        self,
        submission_id: str,
        *,
        poll_interval: float = 2.5,
        timeout: float = 600.0,
        on_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Poll until a submission is done or failed."""

        if poll_interval < 0:
            raise ValueError("poll_interval must be non-negative")
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        deadline = time.monotonic() + timeout
        previous_status: object = object()
        while True:
            result = self.get_submission(submission_id)
            status = result.get("status")
            if status != previous_status and on_update is not None:
                on_update(result)
            previous_status = status
            if status in TERMINAL_SUBMISSION_STATUSES:
                return result
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"submission {submission_id!r} did not finish "
                    f"within {timeout:g} seconds"
                )
            time.sleep(min(poll_interval, remaining))

    def _request_object(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = False,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document = self._request(
            method,
            path,
            authenticated=authenticated,
            json=json,
        )
        if not isinstance(document, dict):
            raise ContestApiError(
                status_code=200,
                code="invalid_response",
                message="response was not a JSON object",
            )
        return document

    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = False,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers: dict[str, str] = {}
        if authenticated:
            if not self.api_key:
                raise MissingApiKeyError(
                    "ICFPC2026_API_KEY is required for submission operations"
                )
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = self._client.request(
                method,
                path,
                headers=headers,
                json=json,
            )
        except httpx.HTTPError as error:
            raise RuntimeError(f"contest API request failed: {error}") from error

        try:
            document = response.json()
        except ValueError as error:
            raise ContestApiError(
                status_code=response.status_code,
                code="invalid_response",
                message="response was not valid JSON",
            ) from error

        if response.is_success:
            return document

        error_document = document.get("error") if isinstance(document, dict) else None
        if isinstance(error_document, dict):
            code = str(error_document.get("code") or "request_failed")
            message = str(error_document.get("message") or response.reason_phrase)
        else:
            code = "request_failed"
            message = response.reason_phrase
        raise ContestApiError(
            status_code=response.status_code,
            code=code,
            message=message,
        )
