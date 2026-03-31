"""API 키 발급 스크립트.
사용법: docker compose exec backend python scripts/create_api_key.py
"""
import asyncio
import hashlib
import secrets
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from sqlalchemy import text
from app.db.session import AsyncSessionLocal, engine


async def main() -> None:
    # 1. pgvector extension + 테이블 확인
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    async with AsyncSessionLocal() as session:
        # 2. 시스템 유저 upsert
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        await session.execute(text("""
            INSERT INTO users (id, email, hashed_password, organization, is_active, is_admin)
            VALUES (:id, 'admin@hwpconverter.local', 'n/a', '시스템', true, true)
            ON CONFLICT (id) DO NOTHING
        """), {"id": str(user_id)})

        # 3. API 키 생성
        raw_key = "hwp_" + secrets.token_hex(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]

        await session.execute(text("""
            INSERT INTO api_keys (id, user_id, name, key_hash, key_prefix, is_active)
            VALUES (:id, :user_id, :name, :key_hash, :key_prefix, true)
        """), {
            "id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "name": "default",
            "key_hash": key_hash,
            "key_prefix": key_prefix,
        })
        await session.commit()

    print("\n✅ API 키 발급 완료")
    print("=" * 60)
    print(f"  {raw_key}")
    print("=" * 60)
    print("→ http://localhost:3002/settings 에서 위 키를 입력하세요.\n")


asyncio.run(main())
