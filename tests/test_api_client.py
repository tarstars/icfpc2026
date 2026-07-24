from __future__ import annotations

import json

import httpx
import pytest

from icfpc_api import (
    MAX_PROGRAM_BYTES,
    ContestApiClient,
    ContestApiError,
    MissingApiKeyError,
)


def test_public_problem_list_omits_bearer_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/public/problems"
        assert "authorization" not in request.headers
        assert request.headers["user-agent"].startswith("icfpc2026-tools/")
        return httpx.Response(200, json=[{"id": "p1", "slug": "echo"}])

    with ContestApiClient(
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.list_problems() == [{"id": "p1", "slug": "echo"}]


def test_submit_sends_exact_program_and_bearer_key():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/submissions"
        assert request.headers["authorization"] == "Bearer secret-key"
        assert json.loads(request.content) == {
            "problemId": "p1",
            "program": "@1\n",
        }
        return httpx.Response(202, json={"id": "s1", "status": "pending"})

    with ContestApiClient(
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        assert client.submit(problem_id="p1", program="@1\n") == {
            "id": "s1",
            "status": "pending",
        }


def test_authenticated_operation_requires_key_without_request():
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    with (
        ContestApiClient(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(MissingApiKeyError),
    ):
        client.get_submission("s1")
    assert not called


def test_submit_rejects_oversized_program_without_request():
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    with (
        ContestApiClient(
            api_key="secret-key",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(ValueError, match="limit"),
    ):
        client.submit(problem_id="p1", program="x" * (MAX_PROGRAM_BYTES + 1))
    assert not called


def test_structured_api_error_is_preserved():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={
                "error": {
                    "code": "too_many_requests",
                    "message": "wait for a submission",
                }
            },
        )

    with (
        ContestApiClient(
            api_key="secret-key",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(ContestApiError) as raised,
    ):
        client.get_submission("s1")
    assert raised.value.status_code == 429
    assert raised.value.code == "too_many_requests"


def test_wait_stops_on_terminal_status():
    statuses = iter(["pending", "running", "done"])

    def handler(_: httpx.Request) -> httpx.Response:
        status = next(statuses)
        return httpx.Response(200, json={"id": "s1", "status": status})

    updates = []
    with ContestApiClient(
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.wait_for_submission(
            "s1",
            poll_interval=0,
            timeout=1,
            on_update=lambda document: updates.append(document["status"]),
        )
    assert result["status"] == "done"
    assert updates == ["pending", "running", "done"]
