"""AI 서비스 — Bedrock(기본) / Claude API / Ollama 지원."""
from __future__ import annotations

import logging

from tenacity import retry, stop_after_attempt, wait_exponential

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None  # type: ignore

from app.core.config import settings

logger = logging.getLogger(__name__)

# 행정안전부 공문서 규정 시스템 프롬프트
_GOV_SYSTEM_PROMPT = """당신은 대한민국 행정안전부 공문서 규정(행정업무의 효율적 운영에 관한 규정)에 정통한 공문서 작성 전문가입니다.

공문서 작성 규칙:
1. 두문: 수신자·경유·발신기관명 포함
2. 본문: 제목·내용·붙임 순서 준수
3. 결문: 발신명의·기안자·검토자·결재권자 직위·성명 기재
4. 문체: 간결하고 명확한 행정 문체 사용 (존댓말 금지, 종결어미 '-임', '-함' 사용)
5. 항목 번호: 1., 가., 1), 가), (1), (가) 순서
6. 날짜 표기: XXXX. XX. XX. 형식
7. 제목: 내용을 포괄하는 짧고 명확한 표현

반드시 위 규정을 준수하여 작성하세요."""


class AIService:
    """Bedrock / Claude API / Ollama 통합 서비스.

    우선순위: USE_OLLAMA=true → Ollama, AWS 키 있으면 → Bedrock, 아니면 → Claude API
    """

    def __init__(self) -> None:
        self._bedrock = None
        self._claude = None
        self._use_ollama = settings.use_ollama

    def _get_bedrock(self):
        if self._bedrock is None:
            if _anthropic is None:
                raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.")
            self._bedrock = _anthropic.AsyncAnthropicBedrock(
                aws_access_key=settings.aws_access_key_id,
                aws_secret_key=settings.aws_secret_access_key,
                aws_region=settings.aws_region,
            )
        return self._bedrock

    def _get_claude(self):
        if self._claude is None:
            if _anthropic is None:
                raise RuntimeError("anthropic 패키지가 설치되지 않았습니다.")
            self._claude = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._claude

    @property
    def _use_bedrock(self) -> bool:
        return bool(settings.aws_access_key_id and settings.aws_secret_access_key and not self._use_ollama)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        max_tokens: int | None = None,
    ) -> str:
        """텍스트 생성. Bedrock > Claude API > Ollama 순서."""
        if not system_prompt:
            system_prompt = _GOV_SYSTEM_PROMPT
        if self._use_ollama:
            return await self._generate_ollama(user_prompt, system_prompt)
        if self._use_bedrock:
            return await self._generate_bedrock(user_prompt, system_prompt, max_tokens)
        return await self._generate_claude(user_prompt, system_prompt, max_tokens)

    async def _generate_bedrock(
        self, user_prompt: str, system_prompt: str, max_tokens: int | None,
    ) -> str:
        client = self._get_bedrock()
        message = await client.messages.create(
            model=settings.bedrock_model_id,
            max_tokens=max_tokens or settings.claude_max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    async def _generate_claude(
        self, user_prompt: str, system_prompt: str, max_tokens: int | None,
    ) -> str:
        client = self._get_claude()
        message = await client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens or settings.claude_max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    async def _generate_ollama(self, user_prompt: str, system_prompt: str) -> str:
        import ollama as _ollama  # type: ignore

        response = await _ollama.AsyncClient(host=settings.ollama_base_url).chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response["message"]["content"]

    async def generate_draft(
        self,
        template: str,
        title: str,
        body_hint: str,
        department: str = "",
        reference_number: str = "",
    ) -> str:
        """공문서 초안 생성."""
        prompt = f"""다음 조건으로 공문서 초안을 작성하세요.

문서 종류: {template}
제목: {title}
기안 부서: {department or "(부서명 미지정)"}
문서번호: {reference_number or "(번호 미지정)"}

본문 내용 힌트:
{body_hint}

행정안전부 공문서 규정에 맞는 완성된 공문서를 Markdown 형식으로 작성하세요."""
        return await self.generate(prompt)

    async def summarize(self, text: str) -> str:
        """문서 요약."""
        prompt = f"""다음 공문서를 3~5줄로 요약하세요. 핵심 내용·수신자·요청사항을 포함해야 합니다.

{text}"""
        return await self.generate(
            prompt,
            system_prompt="당신은 공공기관 문서 요약 전문가입니다. 간결하고 정확하게 요약하세요.",
        )

    async def proofread(self, text: str) -> dict[str, str | list]:
        """맞춤법 + 행정 문체 교정. 원문과 교정문, 변경 목록 반환."""
        prompt = f"""다음 공문서를 교정하세요.

교정 기준:
1. 맞춤법·띄어쓰기 오류 수정
2. 행정 문체 준수 (종결어미 '-임', '-함' 등)
3. 불필요한 외래어·비표준어 수정
4. 어색한 문장 구조 개선

원문:
{text}

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "corrected": "교정된 전체 텍스트",
  "changes": [
    {{"type": "replace", "before": "원문 부분", "after": "교정된 부분"}},
    ...
  ]
}}"""
        import json

        raw = await self.generate(
            prompt,
            system_prompt="당신은 한국어 공문서 교정 전문가입니다. JSON 형식으로만 응답하세요.",
        )
        # JSON 파싱 (응답에 코드블록이 섞일 수 있으므로 정제)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"corrected": raw, "changes": []}
        return result


# 싱글턴
ai_service = AIService()
