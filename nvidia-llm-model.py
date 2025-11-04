import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY") or os.getenv("APP_NVIDIA_API_KEY")
if not API_KEY:
  raise RuntimeError("NVIDIA_API_KEY environment variable is required")

BASE_URL = os.getenv("NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
app = FastAPI(title="NVIDIA LLM Shim")


def extract_extra_body(request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
  extra_body: Dict[str, Any] = {}
  for key in ("extra_body", "response_format"):
    value = request_body.get(key)
    if value is not None:
      if key == "extra_body" and isinstance(value, dict):
        extra_body.update(value)
      else:
        extra_body[key] = value
  return extra_body or None


def build_completion_kwargs(request_body: Dict[str, Any]) -> Dict[str, Any]:
  kwargs: Dict[str, Any] = {
    "model": request_body["model"],
    "messages": request_body["messages"],
  }

  optional_fields = [
    "temperature",
    "top_p",
    "max_tokens",
    "frequency_penalty",
    "presence_penalty",
    "stop",
    "tools",
    "tool_choice",
    "logprobs",
    "top_logprobs",
  ]
  for field in optional_fields:
    if field in request_body:
      kwargs[field] = request_body[field]

  extra_body = extract_extra_body(request_body)
  if extra_body:
    kwargs["extra_body"] = extra_body

  # Streaming requests are aggregated into a single non-streaming response.
  kwargs["stream"] = False
  return kwargs


@app.post("/v1/chat/completions")
async def create_chat_completion(request_body: Dict[str, Any]):
  try:
    if "model" not in request_body or "messages" not in request_body:
      raise KeyError("model" if "model" not in request_body else "messages")
    kwargs = build_completion_kwargs(request_body)
    response = client.chat.completions.create(**kwargs)
  except KeyError as missing:
    raise HTTPException(status_code=400, detail=f"Missing field: {missing.args[0]}") from missing
  except Exception as err:  # pragma: no cover - surfaced for operator visibility
    raise HTTPException(status_code=502, detail=str(err)) from err

  return JSONResponse(content=response.model_dump())


@app.get("/healthz")
async def healthcheck():
  return {"status": "ok"}


def run():
  host = os.getenv("LLM_SHIM_HOST", "0.0.0.0")
  port = int(os.getenv("LLM_SHIM_PORT", "8000"))

  import uvicorn

  uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
  run()