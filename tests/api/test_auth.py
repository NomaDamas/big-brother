from __future__ import annotations

from fastapi.testclient import TestClient

from big_brother.api.app import ApiSettings, create_app

HTTP_UNAUTHORIZED = 401


def test_non_dev_mode_requires_admin_token_for_review_actions() -> None:
    client = TestClient(
        create_app(
            settings=ApiSettings(
                dev_mode=False,
                admin_token="-".join(("test", "admin", "token")),
            ),
        ),
    )

    response = client.post(
        "/v1/reviews/review_1/override",
        json={"decision": "allowed", "reason": "false positive"},
    )

    assert response.status_code == HTTP_UNAUTHORIZED
    assert response.json()["error_code"] == "admin_token_required"
