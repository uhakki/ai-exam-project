"""
extractor.py
Gemini API를 사용하여 페이지별 이미지에서 국어 시험 데이터를 추출하는 모듈
- Tenacity를 활용한 강력한 재시도 로직 적용
- json_repair를 통한 깨진 JSON 자동 복구
- 페이지 단위 처리로 안정성 확보
"""

import time
import json
import google.generativeai as genai
from pathlib import Path
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import logging

# json_repair: 깨진 JSON을 자동 복구하는 라이브러리
try:
    import json_repair
except ImportError:
    json_repair = None
    # 경고는 로거를 통해 한 번만 출력 (모듈 로드 시)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 시스템 프롬프트 정의 (페이지 단위 처리용)
SYSTEM_PROMPT = """
당신은 한국어 수능 및 모의고사 시험지 데이터 추출 전문가입니다.
주어지는 시험지 이미지(1페이지)를 분석하여 '지문'과 '문항'을 구조화된 JSON 데이터로 출력해야 합니다.

[중요: 작업의 성격]
이 작업은 교육 목적의 단순 텍스트 추출(OCR) 작업입니다.
- 사용자가 소유한 시험지 PDF에서 텍스트를 구조화하는 데이터 변환 작업입니다.
- 저작권이 있는 새로운 콘텐츠를 생성하는 것이 아닙니다.
- 이미지에 있는 텍스트를 그대로 읽어서 JSON 형식으로 정리하는 것입니다.
- 교육 자료 관리 시스템을 위한 정당한 텍스트 추출입니다.

[처리 규칙]
1. 시험지는 다단(Multi-column)으로 되어 있으니 문맥을 파악하여 올바른 순서로 텍스트를 읽으십시오.
2. [지문]은 문항들이 공통으로 참고하는 텍스트입니다. (예: [1~3] 다음 글을 읽고...)
3. [문항]은 발문, 보기(박스), 선지(1~5)로 구성됩니다.
4. <보기>나 [자료] 같은 박스형 내용은 'reference_box' 필드에 텍스트로 추출하십시오.
5. 독립 문항(지문 없이 단독으로 존재하는 문항)의 경우 passage_content를 빈 문자열로 설정하십시오.
6. 페이지가 잘려서 지문이나 문항이 불완전하게 보이면, **보이는 내용만 추출**하십시오.
7. 출력은 반드시 정해진 JSON 스키마를 따르십시오. (Markdown backticks 없이 순수 JSON만 출력)

[★★★ 중요: 페이지 연결 판단 기준 ★★★]
지문이 페이지에 걸쳐 있는지 판단하여 플래그를 정확히 설정하세요:

"is_continued_from_prev": true 로 설정해야 하는 경우:
- 페이지 맨 위에서 지문이 문장 중간부터 시작하는 경우
- "[1~3] 다음 글을 읽고..." 같은 지문 시작 표시 없이 본문이 바로 시작되는 경우
- 첫 문장이 문맥상 불완전하거나 앞 내용이 있어야 이해되는 경우
- 이전 페이지에서 넘어온 문제의 선지가 이 페이지에서 계속되는 경우

"continues_to_next": true 로 설정해야 하는 경우:
- 페이지 맨 아래에서 문장이 끝나지 않고 잘린 경우
- 지문이 끝나지 않았는데 페이지가 끝난 경우
- 문제의 선지가 다 나오지 않고 페이지가 끝난 경우 (예: ①②③만 있고 ④⑤가 없음)

두 플래그 모두 false인 경우:
- 지문이 이 페이지에서 시작하고 이 페이지에서 완전히 끝나는 경우

[영역 분류 기준]
- 화법과작문: 대화, 토론, 발표, 작문 관련 지문
- 문법: 문법 규칙, 형태소, 음운 등 언어 규칙 관련
- 독서: 인문, 사회, 과학, 기술, 예술 등 비문학 지문
- 문학: 현대시, 고전시가, 현대소설, 고전소설, 수필 등

[JSON Output Schema]
출력은 반드시 아래 형식의 JSON 배열이어야 합니다:
[
  {
    "category": "영역 (화법과작문/문법/독서/문학 중 하나, 세부 분류 가능)",
    "passage_content": "지문 내용 전체 텍스트 (이 페이지에 보이는 부분만)",
    "is_continued_from_prev": false,
    "continues_to_next": false,
    "related_questions": [
      {
        "q_num": 1,
        "q_stem": "문제의 발문 (예: 윗글에 대한 설명으로 적절한 것은?)",
        "reference_box": "<보기> 내용 (없으면 빈 문자열)",
        "choice_1": "① 선지 내용",
        "choice_2": "② 선지 내용",
        "choice_3": "③ 선지 내용",
        "choice_4": "④ 선지 내용",
        "choice_5": "⑤ 선지 내용"
      }
    ]
  }
]

[주의사항]
- 이미지에 지문이나 문항이 전혀 없으면 빈 배열 []을 반환하십시오.
- 표지, 안내문, 답안지 등 문제가 아닌 페이지도 빈 배열 []을 반환하십시오.
- 선지가 불완전하게 잘린 경우에도 보이는 내용까지만 추출하고, continues_to_next를 true로 설정하십시오.
"""

USER_PROMPT = """
첨부된 이미지는 고등학교 국어 모의고사 시험지의 한 페이지입니다.
이 페이지에 보이는 모든 지문과 문항을 추출해 주세요.

다음 사항을 반드시 준수해 주세요:
1. 이 페이지에 보이는 지문과 문항만 추출 (이전/다음 페이지 내용은 추측하지 마세요)
2. 각 문항의 선지(①~⑤)를 정확하게 추출
3. <보기>나 [자료] 박스가 있는 경우 reference_box에 포함
4. JSON 형식으로만 응답 (다른 텍스트 없이)
5. 문제가 없는 페이지(표지, 안내문 등)는 빈 배열 []로 응답

JSON 배열로 출력해 주세요.
"""


# API 키 저장용 전역 변수
_api_key: Optional[str] = None
_model: Optional[genai.GenerativeModel] = None


MODEL_OPTIONS = {
    "pro": "gemini-3-pro-preview",      # 고품질, 느림
    "flash": "gemini-2.0-flash",         # 빠름, 저렴 (권장)
}

DEFAULT_MODEL = "flash"


def configure_api(api_key: str, model_type: str = None) -> None:
    """Gemini API 설정. model_type: 'pro' (고품질) 또는 'flash' (고속, 기본값)"""
    global _api_key, _model
    _api_key = api_key
    genai.configure(api_key=api_key)

    model_type = model_type or DEFAULT_MODEL
    model_name = MODEL_OPTIONS.get(model_type, MODEL_OPTIONS[DEFAULT_MODEL])

    _model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT,
        generation_config={
            "temperature": 0,
            "response_mime_type": "application/json"
        }
    )


def get_model() -> genai.GenerativeModel:
    """설정된 모델 반환"""
    if _model is None:
        raise RuntimeError("API가 설정되지 않았습니다. configure_api()를 먼저 호출하세요.")
    return _model


def parse_json_with_repair(text: str) -> list:
    """
    JSON 파싱 시도, 실패하면 json_repair로 복구 후 재시도

    Args:
        text: JSON 문자열

    Returns:
        파싱된 데이터
    """
    # 1차 시도: 표준 json 파서
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"[WARN] 표준 JSON 파싱 실패, json_repair로 복구 시도: {e}")

    # 2차 시도: json_repair로 복구
    if json_repair is not None:
        try:
            repaired = json_repair.loads(text)
            logger.info("[OK] json_repair로 JSON 복구 성공")
            return repaired
        except Exception as repair_error:
            logger.error(f"[ERR] json_repair도 실패: {repair_error}")
            raise

    # json_repair가 없으면 원래 에러 발생
    raise json.JSONDecodeError("JSON 파싱 실패", text, 0)


# 재시도 가능한 예외 타입들
RETRYABLE_EXCEPTIONS = (
    Exception,  # 일반적인 예외도 포함 (네트워크 오류 등)
)


@retry(
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    wait=wait_exponential(multiplier=2, min=4, max=120),  # 4초, 8초, 16초... 최대 120초
    stop=stop_after_attempt(3),  # 최대 3회 재시도
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def _call_gemini_api(image_path: Path) -> str:
    """
    Gemini API 호출 (재시도 로직 적용)

    Args:
        image_path: 페이지 이미지 경로

    Returns:
        API 응답 텍스트
    """
    model = get_model()

    # 이미지 파일 업로드
    uploaded_file = genai.upload_file(
        path=str(image_path),
        mime_type="image/png",
        display_name=image_path.name
    )

    try:
        # 파일 처리 완료 대기
        max_wait = 60  # 최대 60초 대기
        wait_time = 0
        while uploaded_file.state.name == "PROCESSING" and wait_time < max_wait:
            time.sleep(2)
            wait_time += 2
            uploaded_file = genai.get_file(uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise RuntimeError(f"파일 처리 실패: {uploaded_file.state.name}")

        # API 호출
        response = model.generate_content(
            [uploaded_file, USER_PROMPT],
            request_options={"timeout": 300}  # 5분 타임아웃
        )

        return response.text

    finally:
        # 업로드 파일 정리
        try:
            genai.delete_file(uploaded_file.name)
        except Exception:
            pass  # 삭제 실패는 무시


def extract_page_data(
    image_path: Path,
    page_num: int,
    pdf_name: str
) -> dict:
    """
    단일 페이지 이미지에서 데이터 추출

    Args:
        image_path: 페이지 이미지 경로
        page_num: 페이지 번호
        pdf_name: 원본 PDF 파일명

    Returns:
        추출 결과 딕셔너리 (성공/실패 정보 포함)
    """
    result = {
        "pdf_name": pdf_name,
        "page_num": page_num,
        "image_path": str(image_path),
        "status": "pending",
        "data": [],
        "error": None,
        "retry_count": 0
    }

    try:
        # API 호출 (재시도 로직 적용)
        response_text = _call_gemini_api(image_path)

        # JSON 파싱 (json_repair 적용)
        parsed_data = parse_json_with_repair(response_text)

        result["status"] = "success"
        result["data"] = parsed_data

    except RetryError as e:
        # 3회 재시도 후에도 실패
        result["status"] = "failed_after_retries"
        result["error"] = f"3회 재시도 후 실패: {str(e.last_attempt.exception())}"
        result["retry_count"] = 3
        logger.error(f"[ERR] 페이지 {page_num} 처리 실패 (3회 재시도 후): {result['error']}")

    except json.JSONDecodeError as e:
        # JSON 파싱 실패 (json_repair로도 복구 불가)
        result["status"] = "json_parse_error"
        result["error"] = f"JSON 파싱 오류: {str(e)}"
        logger.error(f"[ERR] 페이지 {page_num} JSON 파싱 실패: {e}")

    except Exception as e:
        # 기타 예외
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        logger.error(f"[ERR] 페이지 {page_num} 처리 오류: {result['error']}")

    return result


def extract_page_data_with_fallback(
    image_path: Path,
    page_num: int,
    pdf_name: str,
    max_retries: int = 3
) -> dict:
    """
    단일 페이지 데이터 추출 (수동 재시도 포함)
    JSON 파싱 오류 시에도 재시도

    Args:
        image_path: 페이지 이미지 경로
        page_num: 페이지 번호
        pdf_name: 원본 PDF 파일명
        max_retries: 최대 재시도 횟수

    Returns:
        추출 결과 딕셔너리
    """
    for attempt in range(max_retries):
        result = extract_page_data(image_path, page_num, pdf_name)

        if result["status"] == "success":
            return result

        if result["status"] == "json_parse_error" and attempt < max_retries - 1:
            logger.warning(f"[WARN] 페이지 {page_num} JSON 파싱 실패, 재시도 {attempt + 2}/{max_retries}")
            time.sleep(5)  # 5초 대기 후 재시도
            continue

        # 다른 오류이거나 마지막 시도인 경우
        result["retry_count"] = attempt + 1
        break

    return result
