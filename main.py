import functools
import json
import logging

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tg_token: str = ""
    tg_server_url: str = "https://api.telegram.org"
    rollbar_token: str = ""
    rollbar_environment: str = "development"
    # FIXME 30 на время, пока не удается выделить chat_id из request без его обнуления
    per_chat_requests_per_second_limit: int = 30
    requests_per_second_limit: int = 30


app = FastAPI()
settings = Settings()
logger = logging.getLogger(__name__)


def log_request(func):
    @functools.wraps(func)
    async def func_wrapped(*args, **kwargs):
        logger.info(f"Request in. {args!r} {kwargs!r}")
        try:
            return await func(*args, **kwargs)
        finally:
            logger.info(f"Request out. {args!r} {kwargs!r}")

    return func_wrapped


@app.post("/bot{tg_token}/{endpoint_method}")
@log_request
async def proxy_common_telegram_request(
    endpoint_method: str, tg_token: str, request: Request
):
    telegram_url = f"{settings.tg_server_url}/bot{tg_token}/{endpoint_method}"

    data = await request.body()

    headers = {}
    if "Content-Type" in request.headers:
        headers["Content-Type"] = request.headers["Content-Type"]

        if "application/json" in headers["Content-Type"]:  # asend_message
            data_json = json.loads(data.decode("utf-8"))
            chat_id = data_json.get("chat_id", "")
            logger.info(f"chat_id: {chat_id}, endpoint_method: {endpoint_method}")
        elif "multipart/form-data" in headers["Content-Type"]:  # asend_photo
            # Разбиваем строку по нужным разделителям
            parts = data.split(
                b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            )

            # Получаем вторую часть, содержащую значение chat_id
            chat_id_bytes = parts[1].split(b"\r\n")[0]

            # Декодируем значение chat_id из байтов в строку
            chat_id = chat_id_bytes.decode("utf-8")
            logger.info(f"chat_id: {chat_id}, endpoint_method: {endpoint_method}")

    async with httpx.AsyncClient() as client:
        response = await client.request(
            request.method,
            telegram_url,
            headers=headers,
            params=request.query_params,
            data=data,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail="Telegram API request failed"
        )

    return response.json()


if __name__ == "__main__":
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    uvicorn.run("main:app", port=5000)
