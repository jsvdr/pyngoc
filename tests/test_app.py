"""HTTP surface tests: the headers and the limits the browser depends on."""

import pytest
from flask.testing import FlaskClient

from pyngo.app import TOO_DEEP, TOO_LARGE, app


@pytest.fixture
def client() -> FlaskClient:
    return app.test_client()


def test_index_is_served_with_a_content_security_policy(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")

    policy = response.headers["Content-Security-Policy"]

    assert "default-src 'none'" in policy
    assert "script-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    # An injected inline handler must not be allowed to run.
    assert "'unsafe-inline'" not in policy


def test_static_files_are_allowed_by_the_policy(client: FlaskClient) -> None:
    script = client.get("/script.js")

    assert script.status_code == 200
    assert script.headers["Content-Security-Policy"] == client.get("/").headers["Content-Security-Policy"]


@pytest.mark.parametrize(
    "header",
    [
        "Cross-Origin-Opener-Policy",
        "Permissions-Policy",
        "Referrer-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
    ],
)
def test_every_response_carries_the_hardening_headers(client: FlaskClient, header: str) -> None:
    for path in ("/", "/healthz", "/script.js"):
        assert client.get(path).headers[header], path


def test_analysis_answers_are_not_cached(client: FlaskClient) -> None:
    response = client.post("/tokens", json={"source": "int a = 1;"})

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"


def test_missing_source_is_a_json_400(client: FlaskClient) -> None:
    response = client.post("/tokens", json={"nope": 1})

    assert response.status_code == 400
    assert response.get_json()["errors"] == ["No code was provided for analysis."]


def test_a_body_over_the_limit_is_a_json_413(client: FlaskClient) -> None:
    response = client.post("/tokens", json={"source": "a" * (64 * 1024 + 1)})

    assert response.status_code == 413
    assert response.get_json()["errors"] == [TOO_LARGE]


def test_deep_nesting_is_a_syntax_error_not_a_crash(client: FlaskClient) -> None:
    depth = 20_000
    source = "{ int a = " + "(" * depth + "1" + ")" * depth + "; }"
    response = client.post("/parser", json={"source": source})

    assert response.status_code == 200

    body = response.get_json()

    assert body["ok"] is False
    assert body["errors"][-1].endswith("The program is nested too deeply.")


def test_a_recursion_error_that_escapes_is_still_a_json_400(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(_source: str) -> None:
        raise RecursionError

    monkeypatch.setattr("pyngo.app.check_syntax", explode)

    response = client.post("/parser", json={"source": "int a = 1;"})

    assert response.status_code == 400
    assert response.get_json()["errors"] == [TOO_DEEP]
