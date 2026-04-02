"""
smart_review.py
자기 개선형 스마트 검증 시스템

- AI가 추출된 시험지 데이터를 지능적으로 검증
- 발견된 오류 패턴을 Firestore에 축적 (self-improving)
- 축적된 패턴을 다음 검증 시 AI에게 컨텍스트로 제공
- 추출 완료 후 자동 검증 지원
"""

import json
import time
from datetime import datetime
from typing import Optional
from collections import Counter

from firebase_config import get_firestore_client
from storage_backend import load_json_data, get_item_by_id, update_db_fields

# Firestore 컬렉션
PATTERNS_COLLECTION = "review_patterns"
REVIEW_LOGS_COLLECTION = "review_logs"


# =============================================================================
# 1. 오류 패턴 DB (self-improving 기반)
# =============================================================================

def get_error_patterns(limit: int = 30) -> list:
    """축적된 오류 패턴 조회 (빈도순)"""
    db = get_firestore_client()
    docs = db.collection(PATTERNS_COLLECTION).order_by(
        "count", direction="DESCENDING"
    ).limit(limit).stream()
    return [doc.to_dict() for doc in docs]


def record_pattern(pattern_type: str, description: str, example: str = ""):
    """새 오류 패턴 기록 또는 기존 패턴 카운트 증가"""
    db = get_firestore_client()
    # 패턴 ID: type + description의 해시
    import hashlib
    pattern_id = hashlib.md5(f"{pattern_type}:{description}".encode()).hexdigest()[:12]

    doc_ref = db.collection(PATTERNS_COLLECTION).document(pattern_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        doc_ref.update({
            "count": data.get("count", 0) + 1,
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "examples": (data.get("examples", []) + [example])[-5:],  # 최근 5개 예시만 유지
        })
    else:
        doc_ref.set({
            "pattern_id": pattern_id,
            "type": pattern_type,
            "description": description,
            "count": 1,
            "examples": [example] if example else [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "resolved": False,
        })


def save_review_log(file_id: str, issues: list, summary: str):
    """검증 결과를 로그로 저장"""
    db = get_firestore_client()
    log_id = f"{file_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db.collection(REVIEW_LOGS_COLLECTION).document(log_id).set({
        "file_id": file_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "issue_count": len(issues),
        "summary": summary,
        "issues": issues[:50],  # 최대 50개
    })


# =============================================================================
# 2. AI 기반 지능형 검증
# =============================================================================

def build_review_prompt(doc_name: str, questions: list, passages: list, known_patterns: list) -> str:
    """과거 패턴을 포함한 검증 프롬프트 생성"""

    # 문항 요약 (AI에게 보낼 데이터)
    q_data = []
    for q in questions:
        choices = []
        for i in range(1, 6):
            c = q.get(f"choice_{i}", "") or ""
            if c.strip():
                choices.append(c.strip()[:60])
        q_data.append({
            "번호": q.get("q_num"),
            "발문": (q.get("q_stem", "") or "")[:120],
            "보기유무": "O" if (q.get("reference_box") or "").strip() else "X",
            "선지수": len(choices),
            "선지": choices,
            "지문ID": q.get("passage_id"),
            "배점": q.get("score") or q.get("points"),
        })

    p_data = []
    for p in passages:
        content = (p.get("passage_content", "") or "")
        p_data.append({
            "ID": p.get("passage_id"),
            "미리보기": content[:100],
            "길이": len(content),
        })

    # 과거 오류 패턴 컨텍스트
    pattern_context = ""
    if known_patterns:
        pattern_lines = []
        for pat in known_patterns[:15]:
            freq = pat.get("count", 1)
            desc = pat.get("description", "")
            examples = pat.get("examples", [])
            ex_str = f" (예: {examples[0][:50]})" if examples else ""
            pattern_lines.append(f"- [{freq}회 발생] {desc}{ex_str}")
        pattern_context = "\n".join(pattern_lines)

    prompt = f"""당신은 국어 시험지 데이터 품질 검수 전문가입니다.
AI OCR로 추출된 시험지 데이터를 검증하여 문제점을 찾아주세요.

## 검증 대상: {doc_name}

## 문항 데이터 ({len(questions)}개):
{json.dumps(q_data, ensure_ascii=False, indent=1)}

## 지문 데이터 ({len(passages)}개):
{json.dumps(p_data, ensure_ascii=False, indent=1)}

"""

    if pattern_context:
        prompt += f"""## 과거에 자주 발견된 오류 패턴 (우선 확인):
{pattern_context}

위 패턴들을 특히 주의해서 확인해주세요.

"""

    prompt += """## 검증 관점:
1. **선지 누락**: 객관식인데 5개 미만이거나, 서술형인데 선지가 있는 경우
2. **발문 불완전**: 잘려있거나 의미 없는 텍스트 ("None", 깨진 문자 등)
3. **보기 누락**: 발문에 "<보기>", "보기를 참고" 등이 있는데 보기 데이터가 없는 경우
4. **문항번호 이상**: 번호 중복, 순서 건너뜀, 서술형 분류 오류
5. **지문 연결 오류**: passage_id가 있는데 해당 지문이 없거나, 지문 내용이 비어있는 경우
6. **텍스트 품질**: OCR 깨짐, 의미 없는 문자열, 불완전한 문장
7. **중복 문항**: 같은 내용의 문항이 반복된 경우

## 응답 형식 (JSON 배열):
각 이슈를 다음 형식으로 작성:
{{"q_num": "해당 문항번호 또는 '-'", "issue_type": "카테고리", "severity": "critical|warning|info", "description": "구체적 설명", "pattern": "이 오류의 일반적인 패턴 설명 (향후 패턴 DB에 축적)"}}

문제가 없으면 빈 배열 []을 반환하세요.
critical: 데이터 사용 불가 수준 / warning: 확인 필요 / info: 참고"""

    return prompt


def run_smart_review(file_ids: list, model_type: str = "flash") -> dict:
    """
    지능형 스마트 검증 실행
    - AI가 데이터를 분석하고 이슈를 찾음
    - 발견된 패턴을 DB에 축적 (self-improving)
    - 결과를 review_logs에 저장
    """
    import google.generativeai as genai
    import json_repair
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            pass

    if not api_key:
        return {"error": "API 키를 찾을 수 없습니다."}

    genai.configure(api_key=api_key)

    model_name = "gemini-2.5-flash" if model_type == "flash" else "gemini-2.5-pro"
    model = genai.GenerativeModel(
        model_name,
        generation_config={"temperature": 0, "response_mime_type": "application/json"}
    )

    # 과거 오류 패턴 로드
    known_patterns = get_error_patterns(limit=20)

    results = {}

    for file_id in file_ids:
        data = load_json_data(file_id)
        if not data:
            results[file_id] = {
                "issues": [{"severity": "critical", "description": "JSON 데이터 없음", "q_num": "-", "issue_type": "데이터없음"}],
                "summary": "데이터 없음",
                "doc_name": file_id,
            }
            continue

        questions = data.get("questions", [])
        passages = data.get("passages", [])
        item = get_item_by_id(file_id)
        doc_name = item.get("filename", file_id) if item else file_id

        issues = []

        try:
            prompt = build_review_prompt(doc_name, questions, passages, known_patterns)
            response = model.generate_content(prompt)

            if response and response.text:
                ai_issues = json_repair.loads(response.text)
                if isinstance(ai_issues, list):
                    for ai_issue in ai_issues:
                        issue = {
                            "q_num": str(ai_issue.get("q_num", "-")),
                            "issue_type": ai_issue.get("issue_type", "기타"),
                            "severity": ai_issue.get("severity", "info"),
                            "description": ai_issue.get("description", ""),
                            "pattern": ai_issue.get("pattern", ""),
                        }
                        issues.append(issue)

                        # 패턴 DB에 축적 (self-improving)
                        if issue["pattern"]:
                            record_pattern(
                                pattern_type=issue["issue_type"],
                                description=issue["pattern"],
                                example=f"{doc_name} - {issue['q_num']}번: {issue['description'][:80]}"
                            )

        except Exception as e:
            issues.append({
                "q_num": "-",
                "issue_type": "시스템오류",
                "severity": "info",
                "description": f"AI 검증 실행 불가: {str(e)[:100]}",
                "pattern": "",
            })

        # 요약 생성
        critical = sum(1 for i in issues if i.get("severity") == "critical")
        warning = sum(1 for i in issues if i.get("severity") == "warning")
        info = sum(1 for i in issues if i.get("severity") == "info")

        if critical > 0:
            summary = f"심각 {critical}건, 경고 {warning}건, 참고 {info}건"
        elif warning > 0:
            summary = f"경고 {warning}건, 참고 {info}건"
        elif info > 0:
            summary = f"참고 {info}건"
        else:
            summary = "이상 없음"

        result = {
            "issues": issues,
            "summary": summary,
            "doc_name": doc_name,
            "q_count": len(questions),
            "p_count": len(passages),
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        results[file_id] = result

        # 검증 로그 저장
        save_review_log(file_id, issues, summary)

        # Firestore 문서에 검증 결과 마킹
        update_db_fields(file_id, smart_reviewed=True, smart_review_summary=summary)

        # API rate limit
        time.sleep(1)

    return results


def auto_review_after_extraction(file_id: str):
    """추출 완료 후 자동 스마트 검증 (backend에서 호출)"""
    try:
        result = run_smart_review([file_id], model_type="flash")
        return result.get(file_id, {})
    except Exception:
        return {}


def get_pattern_stats() -> dict:
    """오류 패턴 통계"""
    patterns = get_error_patterns(limit=50)
    if not patterns:
        return {"total": 0, "top_types": [], "patterns": []}

    type_counts = Counter(p.get("type", "기타") for p in patterns)
    total = sum(p.get("count", 0) for p in patterns)

    return {
        "total_patterns": len(patterns),
        "total_occurrences": total,
        "top_types": type_counts.most_common(5),
        "patterns": patterns,
    }
