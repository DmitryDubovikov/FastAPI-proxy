import json
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from main import app


def test_proxy_common_telegram_request():
    endpoint_method = "test_endpoint"
    tg_token = "test_token"
    chat_id = "test_chat_id"

    request_body = {
        "chat_id": chat_id,
        "other_key": "other_value",
    }

    client = TestClient(app)

    with patch("main.httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = httpx.Response(
            200, json={"mock_response_key": "mock_response_value"}
        )

        response = client.post(f"/bot{tg_token}/{endpoint_method}", json=request_body)

    assert response.status_code == 200
    assert mock_request.call_count == 1

    called_args, called_kwargs = mock_request.call_args
    assert called_args[0] == "POST"
    assert called_args[1] == f"https://api.telegram.org/bot{tg_token}/{endpoint_method}"

    assert "headers" in called_kwargs
    assert "params" in called_kwargs
    assert "data" in called_kwargs

    sent_data = json.loads(called_kwargs["data"].decode("utf-8"))
    assert sent_data["chat_id"] == chat_id

    # You can add more assertions based on your specific requirements and expected behavior
