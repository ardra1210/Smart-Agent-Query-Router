import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api
from app.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="Smart Agent Query Router",
    description="Routes natural-language questions to the agent that can answer them.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(api)
