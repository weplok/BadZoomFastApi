from fastapi import FastAPI, Request
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()
SERVER_KEY = os.getenv("SERVER_KEY")


@app.post("/process_message")
async def process_message(req: Request):
    data = await req.json()
    if data.get("server_key") != SERVER_KEY:
        return {"status": "error", "reason": "invalid key"}

    message = data["message"]
    sender = data["sender"]

    # Здесь можно добавить, например, логирование, фильтрацию, ML-анализ и т.п.
    print(f"Received from {sender}: {message}")

    return {"status": "ok"}
