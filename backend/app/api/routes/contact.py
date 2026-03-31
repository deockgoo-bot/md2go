"""문의 접수 API — DB 저장 + 텔레그램 알림."""
import uuid
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.api.deps import check_rate_limit
from app.db.session import AsyncSessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)

_TYPE_LABELS = {
    "general": "일반 문의",
    "bug": "버그 신고",
    "feature": "기능 요청",
    "partnership": "제휴/협업",
    "pricing": "요금/Pro 플랜",
}


class ContactRequest(BaseModel):
    name: str = ""
    email: str
    type: str = "general"
    message: str


async def _send_telegram(body: ContactRequest) -> None:
    """텔레그램으로 문의 알림 전송."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    type_label = _TYPE_LABELS.get(body.type, body.type)
    text_msg = (
        f"📩 새 문의 접수\n\n"
        f"유형: {type_label}\n"
        f"이름: {body.name or '(미입력)'}\n"
        f"이메일: {body.email}\n\n"
        f"{body.message[:500]}"
    )

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": settings.telegram_chat_id, "text": text_msg},
                timeout=5,
            )
    except Exception as e:
        logger.warning("텔레그램 알림 실패: %s", e)


@router.post("", summary="문의 접수")
async def submit_contact(request: Request, body: ContactRequest):
    """문의를 접수합니다. 인증 불필요. IP당 하루 3회 제한."""
    await check_rate_limit(request, "contact")
    if not body.email or not body.message:
        raise HTTPException(status_code=400, detail="이메일과 내용은 필수입니다.")

    # DB 저장
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO contacts (id, name, email, type, message)
                    VALUES (:id, :name, :email, :type, :message)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "name": body.name,
                    "email": body.email,
                    "type": body.type,
                    "message": body.message,
                },
            )
            await db.commit()
    except Exception as e:
        logger.error("문의 저장 실패: %s", e)

    # 텔레그램 알림
    await _send_telegram(body)

    return {"status": "ok", "message": "문의가 접수되었습니다."}
