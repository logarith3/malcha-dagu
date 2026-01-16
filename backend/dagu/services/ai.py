"""
AI Description Service for MALCHA-DAGU.

Generates instrument descriptions using OpenAI API with
prompt engineering to prevent hallucinations.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIDescriptionService:
    """
    AI 악기 설명 생성 서비스.
    할루시네이션 방지를 위한 프롬프트 엔지니어링 적용.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = 'https://api.openai.com/v1/chat/completions'

    def generate_description(
        self,
        model_name: str,
        brand: str,
        category: str
    ) -> dict[str, str]:
        """
        악기 설명 생성 (할루시네이션 방지 적용).

        Returns:
            {'summary': str, 'check_point': str}
        """
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return {
                'summary': f'{brand} {model_name} - 믿을 수 있는 선택',
                'check_point': '',
            }

        # 할루시네이션 방지 프롬프트
        system_prompt = """너는 악기 전문가이자 팩트 체크에 엄격한 에디터다.
사용자가 요청한 악기에 대한 '한 줄 평'과 '구매 가이드'를 작성하라.

# Rules (Strict)
1. **No Hallucination:** Input Data와 너의 지식 베이스가 100% 일치하는 팩트만 서술하라.
   출시 연도나 세부 스펙이 확실하지 않으면 절대 언급하지 말고 톤/음색 특징 위주로 서술하라.
2. **Tone:** "이 악기는~" 처럼 지루하게 시작하지 마라.
   "따뜻한 배음이 매력적입니다", "입문용으로 최고의 선택입니다" 같이 핵심부터 찌르는 간결한 문체를 써라.
3. **Structure:**
   - [summary]: 20자 이내 임팩트 있는 문구.
   - [check_point]: 중고 거래 시 반드시 확인해야 할 고질병(노브 잡음, 넥 휨 등) 1가지. 모르면 빈 문자열.

JSON 형식으로 { "summary": "...", "check_point": "..." } 만 출력하라."""

        user_prompt = f"""# Input Data
- 모델명: {model_name}
- 브랜드: {brand}
- 카테고리: {category}"""

        try:
            import json
            response = requests.post(
                self.api_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt},
                    ],
                    'temperature': 0.2,  # 창의성 낮춤 (팩트 위주)
                    'max_tokens': 200,
                },
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            content = data['choices'][0]['message']['content']

            # JSON 파싱
            result = json.loads(content)
            return {
                'summary': result.get('summary', ''),
                'check_point': result.get('check_point', ''),
            }

        except Exception as e:
            logger.exception(f"AI description generation error: {e}")
            return {
                'summary': f'{brand} {model_name}',
                'check_point': '',
            }
