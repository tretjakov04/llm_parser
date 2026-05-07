from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers.parser_router import router as parser_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SPIL Matrix Parser API",
        description="API для динамического парсинга Excel файлов с помощью LLM",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(parser_router, prefix="/api/v1")

    @app.get("/")
    def health_check():
        return {"status": "ok", "message": "SPIL Parser API is running!"}

    return app
