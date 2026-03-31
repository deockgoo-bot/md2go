import hashlib
import secrets
from datetime import datetime, timezone

from app.core.config import settings


def generate_api_key() -> tuple[str, str, str]:
    """새 API 키를 생성한다.

    Returns:
        (raw_key, key_hash, key_prefix)
        raw_key  — 사용자에게 한 번만 보여줄 평문 키
        key_hash — DB에 저장할 SHA-256 해시
        key_prefix — 목록 표시용 앞 12자
    """
    raw_key = "hwp_" + secrets.token_hex(settings.api_key_length // 2)
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def verify_api_key_hash(raw_key: str, stored_hash: str) -> bool:
    return secrets.compare_digest(_hash_key(raw_key), stored_hash)


def is_key_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    return datetime.now(tz=timezone.utc) > expires_at
