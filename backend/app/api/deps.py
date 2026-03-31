from fastapi import Depends, HTTPException, Query, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import is_key_expired
from app.db.session import get_db
from app.models.api_key import ApiKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_DEV_API_KEY_OBJ = ApiKey(is_active=True, expires_at=None)


async def verify_api_key(
    header_key: str = Security(api_key_header),
    query_key: str | None = Query(default=None, alias="api_key"),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """X-API-Key 헤더 또는 ?api_key= 쿼리 파라미터로 인증.
    다운로드 링크처럼 헤더를 붙이기 어려운 경우 쿼리 파라미터를 사용한다.
    """
    raw_key = header_key or query_key

    if not raw_key:
        raise HTTPException(status_code=401, detail="API 키가 필요합니다.")

    # 개발용 고정 키
    if settings.dev_api_key and raw_key == settings.dev_api_key:
        return _DEV_API_KEY_OBJ

    import hashlib
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 API 키입니다.")

    if is_key_expired(api_key.expires_at):
        raise HTTPException(status_code=401, detail="만료된 API 키입니다.")

    from datetime import datetime, timezone
    api_key.last_used_at = datetime.now(tz=timezone.utc)

    return api_key


# ── IP 기반 일일 사용량 제한 ──────────────────────────────────

import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_rate_limit(request: Request, category: str = "convert") -> None:
    """IP 기반 일일 사용 횟수 제한.

    category: "convert" (변환, 5회) 또는 "ai" (초안/검색/교정, 3회)
    Redis 키: rate_limit:{category}:{ip}  (TTL: 자정까지 남은 초)
    """
    if category == "ai":
        limit = settings.rate_limit_ai_daily
    else:
        limit = settings.rate_limit_daily
    if limit <= 0:
        return

    # X-Forwarded-For 스푸핑 방지: 직접 연결 IP 사용
    client_ip = request.client.host if request.client else "unknown"

    r = await _get_redis()
    key = f"rate_limit:{category}:{client_ip}"

    try:
        count = await r.get(key)
        current = int(count) if count else 0

        label = "AI 기능" if category == "ai" else "변환"
        if current >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"일일 {label} 한도({limit}회)를 초과했습니다. 내일 다시 시도해주세요.",
            )

        pipe = r.pipeline()
        pipe.incr(key)
        if current == 0:
            from datetime import datetime, timedelta, timezone, time

            now = datetime.now(tz=timezone(timedelta(hours=9)))
            midnight = datetime.combine(now.date() + timedelta(days=1), time.min,
                                        tzinfo=timezone(timedelta(hours=9)))
            ttl = int((midnight - now).total_seconds())
            pipe.expire(key, ttl)
        await pipe.execute()
    except HTTPException:
        raise
    except Exception:
        pass
