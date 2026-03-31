import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.api.routes import convert, draft, search, correct, contact
from app.db.session import init_db


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="HWP Converter AI API",
    description="공공기관 HWPX 문서 자동화 플랫폼 REST API",
    version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(convert.router, prefix="/api/v1/convert", tags=["변환"])
app.include_router(draft.router, prefix="/api/v1/draft", tags=["초안생성"])
app.include_router(search.router, prefix="/api/v1/search", tags=["검색"])
app.include_router(correct.router, prefix="/api/v1/correct", tags=["교정"])
app.include_router(contact.router, prefix="/api/v1/contact", tags=["문의"])


@app.get("/health", tags=["상태"])
async def health_check():
    return {"status": "ok", "env": settings.app_env}
