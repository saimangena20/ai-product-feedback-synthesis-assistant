import json
import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.feedback import router as feedback_router
from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = ("request_id", "ingest_id", "action", "outcome", "error_code")
        return json.dumps({key: getattr(record, key, None) for key in fields} | {"message": record.getMessage()})


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
app_logger = logging.getLogger("app.api")
app_logger.handlers = [handler]
app_logger.setLevel(logging.INFO)
app_logger.propagate = False

app = FastAPI(title=settings.project_name, version=settings.api_version, description="Feedback ingestion and deterministic theme analytics API.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost", "http://localhost:3000", "http://localhost:5173", "http://127.0.0.1", "http://127.0.0.1:3000", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(feedback_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "AI Product Feedback Synthesis Assistant API"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.project_name}
