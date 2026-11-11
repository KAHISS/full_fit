from fastapi import FastAPI

from app.config import settings
from app.modules.auth.router import router as auth_router

# uv run uvicorn app.main:app --reload
def create_app() -> FastAPI:
    app = FastAPI(title="FullFit API", version="1.0.0")

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)

    return app


app = create_app()