from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import download, extract, health
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Extract identity data from PDF files and export to Excel",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(extract.router, prefix="/api", tags=["extract"])
app.include_router(download.router, prefix="/api", tags=["download"])


@app.get("/")
async def root():
    return {"message": settings.app_name, "status": "running"}
