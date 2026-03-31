import pytest
import pytest_asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from app.main import app


FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest_asyncio.fixture
async def client():
    """FastAPI 테스트 클라이언트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-api-key"},
    ) as ac:
        yield ac


@pytest.fixture
def sample_hwpx_bytes() -> bytes:
    """최소한의 유효한 HWPX ZIP 파일 바이트 (테스트용)."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        zf.writestr(
            "Contents/header.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<HWPML xmlns="http://www.hancom.co.kr/hwpml/2012/document">'
            "<HEAD><DOCSUMMARY><TITLE>테스트 문서</TITLE></DOCSUMMARY></HEAD>"
            "</HWPML>",
        )
        zf.writestr(
            "Contents/section0.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<HWPML xmlns="http://www.hancom.co.kr/hwpml/2012/section">'
            "<BODY><P><RUN><CHAR>안녕하세요</CHAR></RUN></P></BODY>"
            "</HWPML>",
        )
    return buf.getvalue()
