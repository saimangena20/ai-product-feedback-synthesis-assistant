from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.feedback import router as feedback_router
from app.core.config import settings
from app.database.session import engine
from app.database.base import Base

app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    description="Initial FastAPI application for the AI Product Feedback Synthesis Assistant backend.",
)

localhost_origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=localhost_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feedback_router)

@app.on_event("startup")
def startup_database_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ Connected to MySQL successfully!")

        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "AI Product Feedback Synthesis Assistant API"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "AI Product Feedback Synthesis Assistant",
    }
