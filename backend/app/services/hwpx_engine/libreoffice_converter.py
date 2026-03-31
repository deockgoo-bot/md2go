"""LibreOffice 헤드리스 변환 — HWPX → 구버전 HWP 바이너리."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def _lo_bin() -> str:
    """LibreOffice 실행 파일 경로 반환."""
    for candidate in ("libreoffice", "soffice", "/usr/bin/libreoffice", "/usr/bin/soffice"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError("LibreOffice가 설치되지 않았습니다.")


def hwpx_to_hwp_legacy(hwpx_path: Path, output_path: Path) -> Path:
    """HWPX 파일을 구버전 HWP 바이너리로 변환.

    LibreOffice headless 모드로 변환한다.
    한글 97 / 2002 / 2005 등 구버전에서 열 수 있는 .hwp 파일을 생성.
    """
    lo = _lo_bin()

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = subprocess.run(
            [
                lo,
                "--headless",
                "--norestore",
                "--nofirststartwizard",
                "--convert-to", "hwp",
                "--outdir", tmp_dir,
                str(hwpx_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice 변환 실패: {result.stderr[:300]}")

        # LibreOffice는 입력 파일명 기반으로 출력 파일 생성
        converted = Path(tmp_dir) / (hwpx_path.stem + ".hwp")
        if not converted.exists():
            # 파일명이 다를 수 있으므로 .hwp 파일 탐색
            candidates = list(Path(tmp_dir).glob("*.hwp"))
            if not candidates:
                raise RuntimeError("LibreOffice 변환 후 출력 파일을 찾을 수 없습니다.")
            converted = candidates[0]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(converted), str(output_path))

    return output_path
