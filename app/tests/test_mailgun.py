"""MailgunTransport (UPS-073): request shape, batching, unsubscribe headers and safe errors.

Every call goes through httpx.MockTransport with the UPS-071 fixtures: no network, no .env.
"""

import base64
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from app.config import Settings
from app.services import mailgun
from app.services.mailer import MailMessage, MailRecipientVars
from app.services.mailgun import MailgunTransport

FIXTURES = Path(__file__).parent / "fixtures" / "mailgun"
API_KEY = "key-test-not-a-real-secret-0123456789"
MESSAGE_ID = "20260203192638.000be97f99f8cea1@mg.upiixsol.com"


def fixture_response(name: str) -> httpx.Response:
    data = json.loads((FIXTURES / name).read_text())
    body = data["body"]
    if isinstance(body, str):
        return httpx.Response(data["status"], text=body, headers={"content-type": data["content_type"]})
    return httpx.Response(data["status"], json=body)


def make_settings(**overrides) -> Settings:
    values = {
        "mail_backend": "mailgun",
        "mailgun_api_key": API_KEY,
        "mailgun_domain": "mg.upiixsol.com",
        "mailgun_api_base": "https://api.mailgun.net",
        "mail_from": "UpiixSol <avisos@mg.upiixsol.com>",
        "mail_reply_to": "",
        "mailgun_test_mode": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class Recorder:
    """Records each request (form fields parsed) and answers with a fixture or a callable."""

    def __init__(self, respond=None):
        self.requests: list[httpx.Request] = []
        self.forms: list[dict[str, list[str]]] = []
        self.respond = respond or (lambda request: fixture_response("messages_200.json"))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.forms.append(parse_qs(request.content.decode(), keep_blank_values=True))
        return self.respond(request)


def make_transport(recorder: Recorder, **settings) -> MailgunTransport:
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    return MailgunTransport(settings=make_settings(**settings), client=client)


def make_message(campaign_id: int | None = 42) -> MailMessage:
    return MailMessage(
        subject="Hola %recipient.name%", html="<p>Hola</p>", text="Hola", campaign_id=campaign_id
    )


def make_recipients(count: int, start: int = 1) -> list[MailRecipientVars]:
    return [
        MailRecipientVars(
            recipient_id=i,
            email=f"user{i}@example.com",
            name=f"Persona {i}",
            unsubscribe_url=f"https://www.upiixsol.com/api/mail/unsubscribe?t=tok{i}",
        )
        for i in range(start, start + count)
    ]


def test_one_call_per_batch_of_at_most_1000():
    recorder = Recorder()
    recipients = make_recipients(2500)
    result = make_transport(recorder).send_batch(make_message(), recipients)

    assert [len(form["to"]) for form in recorder.forms] == [1000, 1000, 500]
    sent = [address for form in recorder.forms for address in form["to"]]
    assert sent == [r.email for r in recipients]  # ordered batches, nobody twice
    assert len(result.accepted) == 2500
    assert result.failed == {}
    assert set(result.accepted.values()) == {MESSAGE_ID}  # stored without <>


def test_each_recipient_gets_only_their_address():
    # Below the fallback threshold: one call per recipient, a single `to` each.
    recorder = Recorder()
    small = make_recipients(3)
    make_transport(recorder).send_batch(make_message(), small)
    assert [form["to"] for form in recorder.forms] == [[r.email] for r in small]

    # Above it: one batch call, each `to` is one plain address and recipient-variables keys match them,
    # so Mailgun sends one message per address.
    recorder = Recorder()
    big = make_recipients(150)
    make_transport(recorder).send_batch(make_message(), big)
    assert len(recorder.forms) == 1
    form = recorder.forms[0]
    assert form["to"] == [r.email for r in big]
    assert all("," not in to and "<" not in to for to in form["to"])
    assert set(json.loads(form["recipient-variables"][0])) == set(form["to"])


def test_recipient_variables_carry_name_and_unsubscribe_url():
    for count in (2, 150):
        recorder = Recorder()
        recipients = make_recipients(count)
        make_transport(recorder).send_batch(make_message(), recipients)
        merged = {}
        for form in recorder.forms:
            merged.update(json.loads(form["recipient-variables"][0]))
        assert merged == {r.email: {"name": r.name, "unsubscribe_url": r.unsubscribe_url} for r in recipients}


def test_list_unsubscribe_headers_are_sent(monkeypatch):
    # Default (spike §3 unverified): per-recipient calls carry the real URL in the header.
    recorder = Recorder()
    recipients = make_recipients(2)
    make_transport(recorder).send_batch(make_message(), recipients)
    for form, recipient in zip(recorder.forms, recipients, strict=True):
        assert form["h:List-Unsubscribe"] == [f"<{recipient.unsubscribe_url}>"]
        assert form["h:List-Unsubscribe-Post"] == ["List-Unsubscribe=One-Click"]

    # Large fallback: no custom header with a literal variable; Mailgun's own unsubscribe applies.
    recorder = Recorder()
    make_transport(recorder).send_batch(make_message(), make_recipients(150))
    assert "h:List-Unsubscribe" not in recorder.forms[0]
    assert "h:List-Unsubscribe-Post" not in recorder.forms[0]

    # Once verified, a single switch batches everything with the recipient variable in the header.
    monkeypatch.setattr(mailgun, "UNSUBSCRIBE_HEADER_IN_BATCH", True)
    recorder = Recorder()
    make_transport(recorder).send_batch(make_message(), make_recipients(2))
    assert len(recorder.forms) == 1
    assert recorder.forms[0]["h:List-Unsubscribe"] == ["<%recipient.unsubscribe_url%>"]
    assert recorder.forms[0]["h:List-Unsubscribe-Post"] == ["List-Unsubscribe=One-Click"]


def test_tracking_off_and_campaign_id_variable():
    recorder = Recorder()
    make_transport(recorder, mail_reply_to="club@upiixsol.com").send_batch(
        make_message(42), make_recipients(1)
    )
    form = recorder.forms[0]
    assert form["o:tracking"] == ["no"]
    assert form["v:campaign_id"] == ["42"]
    assert form["from"] == ["UpiixSol <avisos@mg.upiixsol.com>"]
    assert form["h:Reply-To"] == ["club@upiixsol.com"]
    assert form["subject"] == ["Hola %recipient.name%"]
    assert form["html"] == ["<p>Hola</p>"]
    assert form["text"] == ["Hola"]

    recorder = Recorder()
    make_transport(recorder).send_batch(make_message(None), make_recipients(1))
    assert "v:campaign_id" not in recorder.forms[0]
    assert "h:Reply-To" not in recorder.forms[0]


def test_test_mode_flag_sets_o_testmode():
    recorder = Recorder()
    make_transport(recorder, mailgun_test_mode=True).send_batch(make_message(), make_recipients(1))
    assert recorder.forms[0]["o:testmode"] == ["yes"]

    recorder = Recorder()
    make_transport(recorder).send_batch(make_message(), make_recipients(1))
    assert "o:testmode" not in recorder.forms[0]


def test_us_and_eu_base_urls():
    for base in ("https://api.mailgun.net", "https://api.eu.mailgun.net/"):
        recorder = Recorder()
        make_transport(recorder, mailgun_api_base=base).send_batch(make_message(), make_recipients(1))
        request = recorder.requests[0]
        assert request.method == "POST"
        assert str(request.url) == f"{base.rstrip('/')}/v3/mg.upiixsol.com/messages"
        expected = base64.b64encode(f"api:{API_KEY}".encode()).decode()
        assert request.headers["authorization"] == f"Basic {expected}"


@pytest.mark.parametrize(
    ("respond", "code"),
    [
        (lambda request: fixture_response("messages_400.json"), "rejected"),
        (lambda request: fixture_response("messages_401.json"), "auth"),
        (lambda request: httpx.Response(403, text="Forbidden"), "auth"),
        (lambda request: httpx.Response(429, json={"message": "Too many requests"}), "rate_limited"),
        (lambda request: httpx.Response(502, text="Bad gateway"), "provider_error"),
        (lambda request: httpx.Response(200, text="not json"), "bad_response"),
        (lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)), "timeout"),
    ],
)
def test_4xx_and_timeout_become_failed_batch_without_secrets(respond, code):
    recipients = make_recipients(2)
    result = make_transport(Recorder(respond)).send_batch(make_message(), recipients)
    assert result.accepted == {}
    assert result.failed == {r.recipient_id: code for r in recipients}
    assert all(len(value) <= 20 for value in result.failed.values())


def test_timeout_and_network_errors_become_failed_batch():
    def timeout(request):
        raise httpx.ReadTimeout(f"timed out for {API_KEY} user1@example.com", request=request)

    def broken(request):
        raise httpx.ConnectError("refused", request=request)

    recipients = make_recipients(150)
    result = make_transport(Recorder(timeout)).send_batch(make_message(), recipients)
    assert result.failed == {r.recipient_id: "timeout" for r in recipients}
    result = make_transport(Recorder(broken)).send_batch(make_message(), recipients)
    assert result.failed == {r.recipient_id: "network" for r in recipients}


def test_one_failed_batch_does_not_stop_the_next():
    calls = iter([httpx.Response(502, text="x"), fixture_response("messages_200.json")])
    recipients = make_recipients(1500)
    result = make_transport(Recorder(lambda request: next(calls))).send_batch(make_message(), recipients)
    assert set(result.failed) == {r.recipient_id for r in recipients[:1000]}
    assert set(result.accepted) == {r.recipient_id for r in recipients[1000:]}


def test_default_client_has_10_second_timeout_and_settings():
    transport = MailgunTransport(settings=make_settings())
    assert transport._client.timeout == httpx.Timeout(10.0)


def test_missing_api_key_fails_every_recipient_as_auth():
    recorder = Recorder()
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    transport = MailgunTransport(settings=make_settings(mailgun_api_key=None), client=client)
    result = transport.send_batch(make_message(), make_recipients(2))
    assert result.failed == {1: "auth", 2: "auth"}
    assert recorder.requests == []


def test_empty_recipient_list_makes_no_call():
    recorder = Recorder()
    assert make_transport(recorder).send_batch(make_message(), []).accepted == {}
    assert recorder.requests == []


def test_api_key_never_in_logs_or_errors(caplog):
    caplog.set_level(logging.DEBUG)
    responses = [
        lambda request: fixture_response("messages_200.json"),
        lambda request: fixture_response("messages_400.json"),
        lambda request: fixture_response("messages_401.json"),
        lambda request: httpx.Response(500, text=f"echo {API_KEY} user1@example.com"),
    ]

    def raise_timeout(request):
        raise httpx.ReadTimeout(f"{API_KEY} user1@example.com", request=request)

    responses.append(raise_timeout)
    outputs = []
    for respond in responses:
        transport = make_transport(Recorder(respond))
        result = transport.send_batch(make_message(), make_recipients(2))
        outputs.append(repr(result))
        outputs.append(repr(transport))
    outputs.append(caplog.text)
    joined = "\n".join(outputs)
    assert "mail.mailgun" in caplog.text  # the transport does log, just safely
    assert API_KEY not in joined
    assert base64.b64encode(f"api:{API_KEY}".encode()).decode() not in joined
    assert "@example.com" not in joined


def test_plain_http_base_or_bad_url_never_sends_the_key():
    recorder = Recorder()
    result = make_transport(recorder, mailgun_api_base="http://api.mailgun.net").send_batch(
        make_message(), make_recipients(1)
    )
    assert result.failed == {1: "auth"}
    assert recorder.requests == []

    result = make_transport(Recorder(), mailgun_domain="bad domain\n").send_batch(
        make_message(), make_recipients(1)
    )
    assert result.failed == {1: "network"}


def test_unsafe_address_or_url_is_rejected_without_a_call():
    recorder = Recorder()
    ok, *_ = make_recipients(1)
    bad_email = MailRecipientVars(2, "a@example.com, b@example.com", "B", "https://x/u?t=2")
    bad_url = MailRecipientVars(3, "c@example.com", "C", "https://x/u?t=3>\r\nBcc: d@example.com")
    result = make_transport(recorder).send_batch(make_message(), [ok, bad_email, bad_url])
    assert result.failed == {2: "rejected", 3: "rejected"}
    assert list(result.accepted) == [1]
    assert [form["to"] for form in recorder.forms] == [[ok.email]]
