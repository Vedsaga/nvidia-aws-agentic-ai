import os
from typing import Dict, List, Optional, Union

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
app = FastAPI(title="NVIDIA Embedding Shim")


def build_embedding_kwargs(
  model: str,
  input_payload: Union[str, List[str]],
  encoding_format: Optional[str],
  input_type: Optional[str],
  extra_body: Optional[Dict],
):
  kwargs: Dict = {"model": model, "input": input_payload}
  if encoding_format:
    kwargs["encoding_format"] = encoding_format

  payload_extra: Dict = {}
  if input_type:
    payload_extra["input_type"] = input_type
  if extra_body:
    payload_extra.update(extra_body)
  if payload_extra:
    kwargs["extra_body"] = payload_extra

  return kwargs


@app.post("/v1/embeddings")
async def create_embeddings(request_body: Dict):
  try:
    model = request_body["model"]
    input_payload = request_body["input"]
  except KeyError as missing:
    raise HTTPException(status_code=400, detail=f"Missing field: {missing.args[0]}") from missing

  kwargs = build_embedding_kwargs(
    model=model,
    input_payload=input_payload,
    encoding_format=request_body.get("encoding_format"),
    input_type=request_body.get("input_type"),
    extra_body=request_body.get("extra_body"),
  )

  try:
    response = client.embeddings.create(**kwargs)
  except Exception as err:  # pragma: no cover - surfaced for operator visibility
    raise HTTPException(status_code=502, detail=str(err)) from err

  return JSONResponse(content=response.model_dump())


@app.get("/healthz")
async def healthcheck():
  return {"status": "ok"}


def run():
  host = os.getenv("EMBED_SHIM_HOST", "0.0.0.0")
  port = int(os.getenv("EMBED_SHIM_PORT", "8001"))

  import uvicorn

  uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
  run()
