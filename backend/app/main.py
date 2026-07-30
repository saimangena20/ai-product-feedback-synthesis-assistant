from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
	title="AI Product Feedback Synthesis Assistant API",
	version="1.0.0",
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


@app.get("/")
async def root() -> dict[str, str]:
	return {"message": "AI Product Feedback Synthesis Assistant API"}


@app.get("/health")
async def health() -> dict[str, str]:
	return {
		"status": "healthy",
		"service": "AI Product Feedback Synthesis Assistant",
	}
