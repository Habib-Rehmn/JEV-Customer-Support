import copy
import json

import httpx
import pytest

from app.models.enums import SupportAction
from app.services.jev_service import (
    JevAuthError,
    JevInvalidResponse,
    JevService,
    JevUnavailable,
    parse_response,
)
from tests.conftest import load_fixture

REAL = load_fixture("jev_replacement_response.json")
CONTEXT = {"customer_message": {"subject": "Damaged", "body": "Arrived broken"}}


def make_service(handler, sleeps=None, api_key="test-key"):
    async def fake_sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)

    return JevService(api_key=api_key, model="jev-test", transport=httpx.MockTransport(handler), sleep=fake_sleep)


def test_parses_real_response():
    decision = parse_response(REAL)
    assert decision.action == SupportAction.REPLACEMENT
    assert decision.confidence == 1
    assert decision.probabilities[SupportAction.REPLACEMENT] == 1
    assert decision.item_damaged == 0.92
    assert decision.billing_dispute == 0.07


@pytest.mark.parametrize("mutate", [
    lambda b: b["answers"]["support_action"].update(choice="cancel_order"),
    lambda b: b["answers"]["support_action"]["probabilities"].pop("billing"),
    lambda b: b["answers"]["support_action"]["probabilities"].update(refund=0.5),
    lambda b: b["answers"]["support_action"]["probabilities"].update(refund="high"),
    lambda b: b["answers"]["support_action"].update(confidence="high"),
    lambda b: b["answers"].pop("support_action"),
    lambda b: b.pop("answers"),
])
def test_rejects_malformed_response(mutate):
    body = copy.deepcopy(REAL)
    mutate(body)
    with pytest.raises(JevInvalidResponse):
        parse_response(body)


async def test_sends_expected_request():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=REAL)

    decision = await make_service(handler).classify_ticket(CONTEXT)
    assert decision.action == SupportAction.REPLACEMENT
    assert seen["url"].endswith("/v1/systemone")
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "jev-test"
    assert seen["body"]["state"] == CONTEXT
    assert set(seen["body"]["questions"]["support_action"]["criteria"]) == {a.value for a in SupportAction}


async def test_missing_api_key_fails_without_calling_api():
    def handler(request):
        raise AssertionError("should not be called")

    with pytest.raises(JevAuthError):
        await make_service(handler, api_key="").classify_ticket(CONTEXT)


@pytest.mark.parametrize("code", [401, 403])
async def test_auth_errors_are_not_retried(code):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(code)

    with pytest.raises(JevAuthError):
        await make_service(handler).classify_ticket(CONTEXT)
    assert len(calls) == 1


async def test_rate_limit_waits_for_retry_after_then_succeeds():
    responses = iter([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json=REAL)])
    sleeps = []
    decision = await make_service(lambda r: next(responses), sleeps).classify_ticket(CONTEXT)
    assert decision.action == SupportAction.REPLACEMENT
    assert sleeps == [7.0]


async def test_rate_limit_gives_up_after_retries():
    calls, sleeps = [], []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"Retry-After": "999"})

    with pytest.raises(JevUnavailable):
        await make_service(handler, sleeps).classify_ticket(CONTEXT)
    assert len(calls) == 3
    assert sleeps == [65.0, 65.0]  # capped


async def test_server_error_is_unavailable():
    with pytest.raises(JevUnavailable):
        await make_service(lambda r: httpx.Response(502)).classify_ticket(CONTEXT)


async def test_timeout_is_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(JevUnavailable):
        await make_service(handler).classify_ticket(CONTEXT)


async def test_non_json_body_is_invalid():
    with pytest.raises(JevInvalidResponse):
        await make_service(lambda r: httpx.Response(200, text="<html>")).classify_ticket(CONTEXT)
