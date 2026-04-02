"""
backend.py
AI 시험지 관리 시스템 - 백엔드 로직
- Firebase Firestore/Storage 기반 데이터 관리
- AI 추출 작업 (기존 extractor.py 활용)
- 멀티모달 검증
- 작업 제어 (중단/재개/초기화)
"""

import os
import json
import time
import threading
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

# 기존 모듈 임포트
from pdf_processor import pdf_to_images, get_page_count
from extractor import configure_api, extract_page_data_with_fallback

# Firebase 스토리지 백엔드 임포트
from storage_backend import (
    get_db, get_item_by_id, update_db_status, update_db_fields,
    write_log, read_log,
    save_json_data, load_json_data,
    append_jsonl, load_jsonl, get_processed_pages,
    upload_file, download_file, download_to_bytes, file_exists,
    delete_file, delete_files_with_prefix,
    get_temp_dir,
)

# 스레드 안전성을 위한 Lock
_file_lock = threading.Lock()


# --- 유틸리티 함수 ---

def check_stop_signal(file_id: str) -> bool:
    """DB에서 중단 신호(Stopping) 확인"""
    item = get_item_by_id(file_id)
    return item and item.get('status') == 'Stopping'


def load_api_key() -> Optional[str]:
    """API 키 로드: st.secrets 우선, .env 폴백"""
    # 1) Streamlit secrets
    try:
        import streamlit as st
        key = st.secrets.get("GOOGLE_API_KEY")
        if key:
            return key
    except Exception:
        pass

    # 2) .env 파일
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("GOOGLE_API_KEY")


# --- 핵심 작업 함수들 ---

def task_extract_json(file_id: str, filepath: str, metadata: dict) -> None:
    """
    Step 1: AI 기반 데이터 추출 (JSON 생성)
    - 기존 extractor.py의 로직을 활용
    - 페이지별 처리 + 체크포인트 지원
    """
    write_log(file_id, "=" * 50)
    write_log(file_id, "[Step 1] 데이터 추출 프로세스 시작")
    update_db_status(file_id, "Extracting", progress=0)

    try:
        # API 키 로드 및 설정
        api_key = load_api_key()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        model_type = metadata.get("model_type", "flash")
        configure_api(api_key, model_type=model_type)
        write_log(file_id, f"[OK] API 키 로드 완료 (모델: {model_type})")

        # PDF를 로컬 temp로 다운로드
        temp_dir = get_temp_dir(file_id)
        local_pdf = os.path.join(temp_dir, os.path.basename(filepath))
        download_file(filepath, local_pdf)

        pdf_path = Path(local_pdf)
        pdf_name = pdf_path.name
        total_pages = get_page_count(str(pdf_path))

        update_db_status(file_id, "Extracting", total_pages=total_pages)
        write_log(file_id, f"[INFO] 총 {total_pages} 페이지 감지")

        # 이미 처리된 페이지 확인 (체크포인트)
        processed_pages = get_processed_pages(file_id, pdf_name)
        if processed_pages:
            write_log(file_id, f"[OK] 이전 진행 상황 발견: {len(processed_pages)}개 페이지 스킵")

        # PDF를 페이지별 이미지로 변환
        pdf_temp_dir = os.path.join(temp_dir, "images")
        write_log(file_id, "[INFO] PDF를 이미지로 변환 중...")
        image_paths = pdf_to_images(str(pdf_path), pdf_temp_dir)
        write_log(file_id, f"[OK] {len(image_paths)}개 이미지 생성 완료")

        # 페이지별 처리
        success_count = 0
        failed_count = 0

        for page_num, image_path in enumerate(image_paths, start=1):
            # 중단 신호 체크
            if check_stop_signal(file_id):
                write_log(file_id, "")
                write_log(file_id, "!!! 사용자 요청에 의해 작업이 안전하게 중단됨 !!!")
                write_log(file_id, f"진행 상황: {page_num - 1}/{total_pages} 페이지 완료")
                update_db_status(
                    file_id, "Stopped",
                    progress=int((page_num - 1) / total_pages * 100),
                    current_page=page_num - 1
                )
                return

            # 이미 처리된 페이지 스킵
            if page_num in processed_pages:
                write_log(file_id, f"[SKIP] P{page_num:03d} - 이전에 처리됨")
                continue

            # 페이지 처리
            write_log(file_id, f"[PROC] P{page_num:03d}/{total_pages} - AI 분석 중...")

            result = extract_page_data_with_fallback(
                image_path=image_path,
                page_num=page_num,
                pdf_name=pdf_name,
                max_retries=3
            )

            # 결과 저장 (Firebase JSONL)
            append_jsonl(file_id, result)

            if result["status"] == "success":
                success_count += 1
                items_count = len(result.get("data", []))
                write_log(file_id, f"[OK] P{page_num:03d} - 성공 ({items_count}개 항목 추출)")
            else:
                failed_count += 1
                write_log(file_id, f"[ERR] P{page_num:03d} - 실패: {result.get('error', 'Unknown')}")

            # 진행률 업데이트
            progress = int(page_num / total_pages * 100)
            update_db_status(file_id, "Extracting", progress=progress, current_page=page_num)

        # 완료 처리
        write_log(file_id, "")
        write_log(file_id, "=" * 50)
        write_log(file_id, f"[DONE] 추출 완료: 성공 {success_count}, 실패 {failed_count}")

        # 메타데이터와 함께 최종 JSON 저장
        _save_final_json(file_id, metadata)

        write_log(file_id, f"[SAVE] JSON 데이터 저장 완료")
        update_db_status(file_id, "Extracted", progress=100)

        # 자동 스마트 검증
        try:
            write_log(file_id, "[AUTO] 스마트 검증 실행 중...")
            from smart_review import auto_review_after_extraction
            review_result = auto_review_after_extraction(file_id)
            review_summary = review_result.get("summary", "")
            issue_count = len(review_result.get("issues", []))
            write_log(file_id, f"[AUTO] 스마트 검증 완료: {review_summary} ({issue_count}건)")
        except Exception as review_err:
            write_log(file_id, f"[AUTO] 스마트 검증 스킵: {str(review_err)[:50]}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        write_log(file_id, f"[ERR] 오류 발생: {error_msg}")
        update_db_status(file_id, "Error", error_msg=error_msg)


def _reassign_passage_ids(passages: list, questions: list) -> tuple:
    """이미 평탄화된 passages/questions에 passage_id를 재부여.

    passages를 page_num 순 정렬 후 새 ID를 순차 부여.
    is_continued_from_prev인 passage는 이전 ID를 재사용.
    questions의 passage_id를 old→new 매핑에 따라 업데이트.
    """
    passages.sort(key=lambda p: p.get("page_num", 0))

    counter = 0
    last_id = None
    old_to_new = {}  # old_passage_id → new_passage_id

    for p in passages:
        old_id = p.get("passage_id")
        if p.get("is_continued_from_prev") and last_id:
            new_id = last_id
        else:
            counter += 1
            new_id = f"P{counter:03d}"
        last_id = new_id
        p["passage_id"] = new_id
        if old_id and old_id != new_id:
            old_to_new[old_id] = new_id

    # questions의 passage_id를 매핑에 따라 업데이트
    for q in questions:
        q_pid = q.get("passage_id")
        if q_pid and q_pid in old_to_new:
            q["passage_id"] = old_to_new[q_pid]
        elif q_pid is None:
            # passage_id가 없는 문항: page_num + category로 매칭 시도
            for p in passages:
                if p.get("page_num") == q.get("page_num") and p.get("category") == q.get("category"):
                    q["passage_id"] = p["passage_id"]
                    break

    return passages, questions


def _save_final_json(file_id: str, metadata: dict) -> None:
    """JSONL 로그를 최종 JSON으로 변환 저장 (Firebase 기반)"""
    questions = []
    passages = []

    entries = load_jsonl(file_id)
    # page_num 순으로 정렬하여 passage_id 순차 부여
    entries.sort(key=lambda e: e.get("page_num", 0))

    passage_counter = 0
    last_passage_id = None

    for entry in entries:
        try:
            if entry.get("status") == "success" and entry.get("data"):
                for item in entry["data"]:
                    current_passage_id = None

                    # 지문 정보 — passage_id 부여
                    if item.get("passage_content"):
                        if item.get("is_continued_from_prev") and last_passage_id:
                            current_passage_id = last_passage_id
                        else:
                            passage_counter += 1
                            current_passage_id = f"P{passage_counter:03d}"

                        last_passage_id = current_passage_id

                        passages.append({
                            "passage_id": current_passage_id,
                            "page_num": entry.get("page_num"),
                            "category": item.get("category", ""),
                            "passage_content": item.get("passage_content", ""),
                            "is_continued_from_prev": item.get("is_continued_from_prev", False),
                            "continues_to_next": item.get("continues_to_next", False)
                        })

                    # 문항 정보 — 같은 passage_id 연결
                    for q in item.get("related_questions", []):
                        questions.append({
                            "passage_id": current_passage_id,
                            "page_num": entry.get("page_num"),
                            "q_num": q.get("q_num"),
                            "category": item.get("category", ""),
                            "q_stem": q.get("q_stem", ""),
                            "reference_box": q.get("reference_box", ""),
                            "choice_1": q.get("choice_1", ""),
                            "choice_2": q.get("choice_2", ""),
                            "choice_3": q.get("choice_3", ""),
                            "choice_4": q.get("choice_4", ""),
                            "choice_5": q.get("choice_5", ""),
                            "ai_note": ""  # 검증용 필드
                        })
        except (json.JSONDecodeError, KeyError):
            continue

    result = {
        "meta": {
            "file_id": file_id,
            "subject": metadata.get("subject", ""),
            "year": metadata.get("year", ""),
            "exam_type": metadata.get("exam_type", ""),
            "grade": metadata.get("grade", ""),
            "month": metadata.get("month", ""),
            "semester": metadata.get("semester", ""),
            "school": metadata.get("school", ""),
            "author": metadata.get("author", ""),
            "desc": metadata.get("desc", ""),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "passages": passages,
        "questions": questions
    }

    save_json_data(file_id, result)


def task_reextract_pages(file_id: str, filepath: str, page_range: str) -> None:
    """
    특정 페이지만 재추출하여 기존 JSON에 병합

    Args:
        file_id: 파일 ID
        filepath: Storage 경로
        page_range: 재추출할 페이지 범위 (예: "14", "3,5,7", "10-12")
    """
    write_log(file_id, "")
    write_log(file_id, "=" * 50)
    write_log(file_id, f"[Step 1-R] 페이지 재추출 시작: {page_range}")
    update_db_status(file_id, "Extracting", progress=50)

    try:
        # API 키 로드
        api_key = load_api_key()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
        configure_api(api_key)

        # 기존 JSON 로드
        data = load_json_data(file_id)
        if not data:
            raise FileNotFoundError("기존 JSON 파일이 없습니다. 전체 추출을 먼저 진행하세요.")

        # 페이지 범위 파싱
        target_pages = set()
        for part in page_range.replace(" ", "").split(","):
            if "-" in part:
                try:
                    start, end = part.split("-")
                    target_pages.update(range(int(start), int(end) + 1))
                except Exception:
                    pass
            else:
                try:
                    target_pages.add(int(part))
                except Exception:
                    pass

        if not target_pages:
            raise ValueError("유효한 페이지 번호가 없습니다.")

        write_log(file_id, f"[INFO] 재추출 대상: {sorted(target_pages)} 페이지")

        # PDF를 로컬 temp로 다운로드 → 이미지 변환
        temp_dir = get_temp_dir(file_id)
        local_pdf = os.path.join(temp_dir, os.path.basename(filepath))
        download_file(filepath, local_pdf)

        pdf_path = Path(local_pdf)
        pdf_temp_dir = os.path.join(temp_dir, "images")

        write_log(file_id, "[INFO] PDF를 이미지로 변환 중...")
        pdf_to_images(str(pdf_path), pdf_temp_dir)

        image_files = sorted(Path(pdf_temp_dir).glob("*.png"))

        # 기존 데이터에서 해당 페이지 제거
        questions = data.get("questions", [])
        passages = data.get("passages", [])

        questions = [q for q in questions if q.get("page_num") not in target_pages]
        passages = [p for p in passages if p.get("page_num") not in target_pages]

        write_log(file_id, f"[INFO] 기존 데이터에서 해당 페이지 삭제됨")

        # 페이지별 재추출
        success_count = 0
        failed_count = 0

        for img_path in image_files:
            try:
                page_num = int(img_path.stem.split('_')[-1])
            except Exception:
                continue

            if page_num not in target_pages:
                continue

            if check_stop_signal(file_id):
                write_log(file_id, "!!! 작업 중단됨 !!!")
                update_db_status(file_id, "Stopped")
                return

            write_log(file_id, f"[PROC] P{page_num:03d} - AI 분석 중...")

            result = extract_page_data_with_fallback(
                image_path=img_path,
                page_num=page_num,
                pdf_name=pdf_path.name,
                max_retries=3
            )

            if result["status"] == "success" and result.get("data"):
                for item in result["data"]:
                    # 지문 정보
                    if item.get("passage_content"):
                        passages.append({
                            "passage_id": None,
                            "page_num": page_num,
                            "category": item.get("category", ""),
                            "passage_content": item.get("passage_content", ""),
                            "is_continued_from_prev": item.get("is_continued_from_prev", False),
                            "continues_to_next": item.get("continues_to_next", False)
                        })

                    # 문항 정보
                    for q in item.get("related_questions", []):
                        questions.append({
                            "passage_id": None,
                            "page_num": page_num,
                            "q_num": q.get("q_num"),
                            "category": item.get("category", ""),
                            "q_stem": q.get("q_stem", ""),
                            "reference_box": q.get("reference_box", ""),
                            "choice_1": q.get("choice_1", ""),
                            "choice_2": q.get("choice_2", ""),
                            "choice_3": q.get("choice_3", ""),
                            "choice_4": q.get("choice_4", ""),
                            "choice_5": q.get("choice_5", ""),
                            "ai_note": ""
                        })

                items_count = len(result.get("data", []))
                write_log(file_id, f"[OK] P{page_num:03d} - 성공 ({items_count}개 항목 추출)")
                success_count += 1
            else:
                write_log(file_id, f"[ERR] P{page_num:03d} - 실패: {result.get('error', 'Unknown')}")
                failed_count += 1

        # 문항 번호순으로 정렬
        questions.sort(key=lambda x: (x.get("page_num", 0), x.get("q_num", 0)))
        passages.sort(key=lambda x: x.get("page_num", 0))

        # passage_id 재부여 (병합 후 일관된 ID 부여)
        passages, questions = _reassign_passage_ids(passages, questions)

        # 저장
        data["questions"] = questions
        data["passages"] = passages
        data["meta"]["modified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        save_json_data(file_id, data)

        write_log(file_id, "")
        write_log(file_id, f"[DONE] 재추출 완료: 성공 {success_count}, 실패 {failed_count}")
        update_db_status(file_id, "Modified", progress=100)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        write_log(file_id, f"[ERR] 재추출 오류: {error_msg}")
        update_db_status(file_id, "Error", error_msg=error_msg)


def task_multimodal_verification(file_id: str, filepath: str, page_range: str = None) -> None:
    """
    Step 1.5: 멀티모달 AI 검증
    - 원본 이미지와 추출된 JSON을 비교
    - AI가 자유롭게 의견을 제시하고 verification_notes에 저장
    """
    write_log(file_id, "")
    write_log(file_id, "=" * 50)
    write_log(file_id, "[Step 1.5] 멀티모달 AI 검증 시작")
    update_db_status(file_id, "Verifying", progress=50)

    try:
        import google.generativeai as genai

        # API 키 로드
        api_key = load_api_key()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")

        genai.configure(api_key=api_key)

        # JSON 파일 로드
        data = load_json_data(file_id)
        if not data:
            raise FileNotFoundError("검증할 JSON 파일이 없습니다. 먼저 추출을 완료하세요.")

        # PDF를 로컬 temp로 다운로드 → 이미지 변환
        temp_dir = get_temp_dir(file_id)
        local_pdf = os.path.join(temp_dir, os.path.basename(filepath))
        download_file(filepath, local_pdf)

        image_dir = os.path.join(temp_dir, "images")
        write_log(file_id, "[INFO] PDF를 이미지로 변환 중...")
        pdf_to_images(local_pdf, image_dir)

        # Vision 모델 설정 (temperature=0으로 저작권 회피)
        model = genai.GenerativeModel(
            'gemini-2.5-pro',
            generation_config={"temperature": 0}
        )

        verification_prompt = """
당신은 시험지 데이터 검증 전문가입니다.

[중요: 작업의 성격]
이 작업은 교육 목적의 데이터 검증 작업입니다.
- 사용자가 소유한 시험지에서 추출된 텍스트의 정확성을 확인하는 작업입니다.
- 저작권이 있는 새로운 콘텐츠를 생성하는 것이 아닙니다.
- 이미지와 추출된 텍스트를 비교하여 누락이나 오류를 찾는 단순 검증입니다.

[작업]
이 시험지 이미지(페이지 {page_num})를 보고, 아래 추출된 JSON 데이터와 비교하여 검증해 주세요.

[검증 포인트]
1. 이 페이지에 있는 문항들이 JSON에 모두 포함되어 있는가? (누락 확인)
2. 문항 번호가 정확한가?
3. 발문(질문)이 정확히 추출되었는가?
4. 선지(보기 ①~⑤)가 정확한가?
5. 지문이나 <보기>가 누락되지 않았는가?
6. 기타 오류나 개선점이 있는가?

[이 페이지의 추출된 데이터]
{json_data}

[응답 방식]
- 문제가 없으면: "이상 없음" 이라고만 답변
- 문제가 있으면: 구체적으로 어떤 문제가 있는지 자유롭게 설명
  예) "14번 문항이 누락됨", "3번 선지 ②가 잘림", "지문 (가)가 누락됨" 등

간결하게 핵심만 답변해 주세요.
"""

        # 검증 결과 저장용
        verification_notes = []
        questions = data.get("questions", [])

        # 페이지별로 검증
        image_files = sorted(Path(image_dir).glob("*.png"))

        # 페이지 범위 파싱
        if page_range is None or page_range.strip() == "" or page_range.lower() == "all":
            sample_images = image_files
        else:
            target_pages = set()
            for part in page_range.replace(" ", "").split(","):
                if "-" in part:
                    try:
                        start, end = part.split("-")
                        target_pages.update(range(int(start), int(end) + 1))
                    except Exception:
                        pass
                else:
                    try:
                        target_pages.add(int(part))
                    except Exception:
                        pass

            sample_images = []
            for img in image_files:
                try:
                    page_num = int(img.stem.split('_')[-1])
                    if page_num in target_pages:
                        sample_images.append(img)
                except Exception:
                    pass

        write_log(file_id, f"[INFO] 검증 대상: {len(sample_images)}개 페이지")

        for img_path in sample_images:
            if check_stop_signal(file_id):
                write_log(file_id, "!!! 검증 작업 중단됨 !!!")
                update_db_status(file_id, "Stopped")
                return

            try:
                page_num = int(img_path.stem.split('_')[-1])
            except Exception:
                page_num = 0

            write_log(file_id, f"[VERIFY] P{page_num:03d} 검증 중...")

            try:
                # 해당 페이지의 문항들 (없으면 빈 리스트)
                page_questions = [q for q in questions if q.get("page_num") == page_num]

                # JSON 데이터 준비 (해당 페이지에 데이터가 없어도 검증)
                if page_questions:
                    json_str = json.dumps(page_questions, ensure_ascii=False, indent=2)
                else:
                    json_str = "(이 페이지에 대한 추출 데이터 없음)"

                # 이미지 업로드
                uploaded_file = genai.upload_file(str(img_path), mime_type="image/png")

                # 파일 처리 대기
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(1)
                    uploaded_file = genai.get_file(uploaded_file.name)

                # 검증 요청
                prompt = verification_prompt.format(page_num=page_num, json_data=json_str)
                response = model.generate_content([uploaded_file, prompt])

                # 응답 처리
                ai_response = response.text.strip() if response.text else ""

                if ai_response:
                    # "이상 없음" 류의 응답이 아니면 기록
                    if "이상 없음" not in ai_response and "이상없음" not in ai_response and "문제 없" not in ai_response:
                        verification_notes.append({
                            "page": page_num,
                            "note": ai_response
                        })
                        write_log(file_id, f"[NOTE] P{page_num:03d}: {ai_response[:100]}...")
                    else:
                        write_log(file_id, f"[OK] P{page_num:03d}: 이상 없음")
                else:
                    write_log(file_id, f"[OK] P{page_num:03d}: 응답 없음")

                # 업로드 파일 삭제
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception:
                    pass

            except Exception as e:
                error_str = str(e)
                # 저작권 관련 오류는 건너뛰기
                if "copyrighted" in error_str.lower() or "finish_reason" in error_str:
                    write_log(file_id, f"[SKIP] P{page_num:03d}: 저작권 보호로 건너뜀")
                else:
                    write_log(file_id, f"[WARN] P{page_num:03d}: {error_str[:80]}")

        # 검증 결과 저장
        data["verification_notes"] = verification_notes
        data["meta"]["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        save_json_data(file_id, data)

        write_log(file_id, "")
        if verification_notes:
            write_log(file_id, f"[DONE] 검증 완료: {len(verification_notes)}개 페이지에서 문제 발견")
            for note in verification_notes:
                write_log(file_id, f"  - P{note['page']:03d}: {note['note'][:50]}...")
        else:
            write_log(file_id, "[DONE] 검증 완료: 문제 없음")

        update_db_status(file_id, "Extracted", progress=100, ai_verified=True)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        write_log(file_id, f"[ERR] 검증 오류: {error_msg}")
        update_db_status(file_id, "Error", error_msg=error_msg)


def task_smart_review(file_ids: list, model_type: str = "flash") -> dict:
    """레거시 호환 — smart_review.py로 위임"""
    from smart_review import run_smart_review
    return run_smart_review(file_ids, model_type)


def _task_smart_review_legacy(file_ids: list, model_type: str = "flash") -> dict:
    """
    지능형 데이터 검증: 추출된 JSON 데이터를 규칙+AI로 검증
    - 규칙 검증: 선지 누락, 빈 발문, 문항번호 중복 등
    - AI 검증: 데이터 흐름, 잘림/깨짐, 내용 이상 감지
    Returns: {file_id: {issues: [...], summary: str}}
    """
    import google.generativeai as genai
    import re

    api_key = load_api_key()
    if not api_key:
        return {"error": "GOOGLE_API_KEY가 설정되지 않았습니다."}

    genai.configure(api_key=api_key)

    results = {}

    for file_id in file_ids:
        data = load_json_data(file_id)
        if not data:
            results[file_id] = {"issues": [{"type": "error", "msg": "JSON 데이터 없음"}], "summary": "데이터 없음"}
            continue

        questions = data.get("questions", [])
        passages = data.get("passages", [])
        item = get_item_by_id(file_id)
        doc_name = item.get("filename", file_id) if item else file_id

        issues = []

        # ── 1단계: 규칙 기반 검증 ──
        q_nums = []
        for q in questions:
            q_num = q.get("q_num", "?")
            q_nums.append(str(q_num))
            q_stem = q.get("q_stem", "") or ""
            is_seo = "서술" in str(q_num)

            # 발문 누락/너무 짧음
            if not q_stem.strip():
                issues.append({"type": "critical", "q_num": q_num, "msg": "발문(q_stem)이 비어 있음"})
            elif len(q_stem) < 5:
                issues.append({"type": "warning", "q_num": q_num, "msg": f"발문이 매우 짧음: '{q_stem}'"})

            # 선지 검증 (서술형이 아닌 경우)
            if not is_seo:
                choice_count = sum(1 for i in range(1, 6) if (q.get(f"choice_{i}", "") or "").strip())
                if choice_count == 0:
                    issues.append({"type": "critical", "q_num": q_num, "msg": "선지가 모두 비어 있음 (서술형이면 문항번호에 '서술형' 표기 필요)"})
                elif choice_count < 5:
                    issues.append({"type": "warning", "q_num": q_num, "msg": f"선지 {choice_count}개만 있음 (5개 중 {5-choice_count}개 누락)"})

                # 선지 번호 기호 확인
                for i in range(1, 6):
                    c = (q.get(f"choice_{i}", "") or "").strip()
                    if c and not re.match(r'^[①②③④⑤\d]', c):
                        issues.append({"type": "info", "q_num": q_num, "msg": f"선지 {i}에 번호 기호 없음: '{c[:30]}'"})

            # 지문 연결 확인
            pid = q.get("passage_id")
            if pid:
                matching = [p for p in passages if p.get("passage_id") == pid]
                if not matching:
                    issues.append({"type": "warning", "q_num": q_num, "msg": f"passage_id '{pid}' 에 해당하는 지문 없음"})

        # 문항번호 중복 확인
        from collections import Counter
        dup_nums = [num for num, cnt in Counter(q_nums).items() if cnt > 1]
        if dup_nums:
            issues.append({"type": "critical", "q_num": "-", "msg": f"문항번호 중복: {', '.join(dup_nums)}"})

        # 지문 검증
        for p in passages:
            content = p.get("passage_content", "") or ""
            if not content.strip():
                issues.append({"type": "warning", "q_num": "-", "msg": f"지문 {p.get('passage_id', '?')} 내용이 비어 있음"})
            elif len(content) < 20:
                issues.append({"type": "info", "q_num": "-", "msg": f"지문 {p.get('passage_id', '?')} 내용이 매우 짧음 ({len(content)}자)"})

        # ── 2단계: AI 리뷰 ──
        try:
            # 데이터를 간결하게 요약하여 AI에 전달
            q_summary = []
            for q in questions:
                choices = [q.get(f"choice_{i}", "") or "" for i in range(1, 6)]
                q_summary.append({
                    "번호": q.get("q_num"),
                    "발문": (q.get("q_stem", "") or "")[:100],
                    "보기": "있음" if q.get("reference_box") else "없음",
                    "선지수": sum(1 for c in choices if c.strip()),
                    "선지1": choices[0][:50] if choices[0] else "",
                    "지문ID": q.get("passage_id"),
                })

            p_summary = []
            for p in passages:
                p_summary.append({
                    "ID": p.get("passage_id"),
                    "내용미리보기": (p.get("passage_content", "") or "")[:80],
                    "길이": len(p.get("passage_content", "") or ""),
                })

            review_prompt = f"""다음은 국어 시험지에서 AI로 추출된 데이터입니다. 데이터 품질을 검수해주세요.

## 문서: {doc_name}
## 문항 ({len(questions)}개):
{json.dumps(q_summary, ensure_ascii=False, indent=1)}

## 지문 ({len(passages)}개):
{json.dumps(p_summary, ensure_ascii=False, indent=1)}

다음 관점에서 문제점을 찾아주세요:
1. 발문이 잘려있거나 불완전한 문항
2. 선지가 누락되거나 내용이 이상한 문항
3. 보기가 있어야 할 것 같은데 없는 문항 (예: "다음 <보기>를..." 발문인데 보기 없음)
4. 지문과 문항의 연결이 이상한 경우
5. 문항번호 순서가 비정상적인 경우
6. 서술형 문항인데 객관식으로 분류된 경우 또는 그 반대

JSON 배열로 답해주세요. 문제가 없으면 빈 배열 [].
각 항목: {{"q_num": "해당번호", "issue": "문제 설명"}}"""

            model = genai.GenerativeModel(
                'gemini-2.5-flash',
                generation_config={"temperature": 0, "response_mime_type": "application/json"}
            )
            response = model.generate_content(review_prompt)

            if response and response.text:
                import json_repair
                ai_issues = json_repair.loads(response.text)
                if isinstance(ai_issues, list):
                    for ai_issue in ai_issues:
                        issues.append({
                            "type": "ai",
                            "q_num": ai_issue.get("q_num", "?"),
                            "msg": ai_issue.get("issue", ""),
                        })

        except Exception as e:
            issues.append({"type": "info", "q_num": "-", "msg": f"AI 리뷰 실행 불가: {str(e)[:50]}"})

        # 요약 생성
        critical = sum(1 for i in issues if i["type"] == "critical")
        warning = sum(1 for i in issues if i["type"] == "warning")
        ai_count = sum(1 for i in issues if i["type"] == "ai")
        if critical > 0:
            summary = f"심각 {critical}건, 경고 {warning}건, AI지적 {ai_count}건"
        elif warning > 0:
            summary = f"경고 {warning}건, AI지적 {ai_count}건"
        elif ai_count > 0:
            summary = f"AI지적 {ai_count}건"
        else:
            summary = "이상 없음"

        results[file_id] = {
            "issues": issues,
            "summary": summary,
            "doc_name": doc_name,
            "q_count": len(questions),
            "p_count": len(passages),
        }

    return results


def task_generate_excel(file_id: str) -> Optional[str]:
    """
    Step 2: 엑셀 생성
    - JSON 데이터를 지문_DB, 문항_DB 시트로 변환
    """
    write_log(file_id, "")
    write_log(file_id, "=" * 50)
    write_log(file_id, "[Step 2] 엑셀 변환 작업 시작")
    update_db_status(file_id, "Converting", progress=10)

    try:
        data = load_json_data(file_id)
        if not data:
            raise FileNotFoundError("JSON 파일이 없습니다.")

        # 로컬 temp에 엑셀 생성
        temp_dir = get_temp_dir(file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"{file_id}_{timestamp}.xlsx"
        local_excel = os.path.join(temp_dir, excel_filename)

        write_log(file_id, "[PROC] 데이터프레임 생성 중...")

        # 지문 시트
        passages_df = pd.DataFrame(data.get("passages", []))

        # 문항 시트
        questions_df = pd.DataFrame(data.get("questions", []))

        # 엑셀 저장
        write_log(file_id, "[SAVE] 엑셀 파일 저장 중...")
        with pd.ExcelWriter(local_excel, engine='openpyxl') as writer:
            if not passages_df.empty:
                passages_df.to_excel(writer, sheet_name='지문_DB', index=False)
            if not questions_df.empty:
                questions_df.to_excel(writer, sheet_name='문항_DB', index=False)

            # 메타데이터 시트
            meta_df = pd.DataFrame([data.get("meta", {})])
            meta_df.to_excel(writer, sheet_name='메타정보', index=False)

        # Firebase Storage에 업로드
        storage_path = f"outputs/excel/{excel_filename}"
        upload_file(local_excel, storage_path)

        write_log(file_id, f"[OK] 엑셀 파일 생성 완료: {excel_filename}")
        update_db_status(file_id, "Done", progress=100)

        # DB에 엑셀 경로 저장 (Storage 경로)
        update_db_fields(file_id, excel_path=storage_path)

        return storage_path

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        write_log(file_id, f"[ERR] 변환 오류: {error_msg}")
        update_db_status(file_id, "Error", error_msg=error_msg)
        return None


# --- 제어 함수 ---

def request_stop(file_id: str) -> None:
    """작업 중단 요청"""
    write_log(file_id, ">>> 중단 요청 신호 수신")
    update_db_status(file_id, "Stopping")


def reset_data(file_id: str) -> None:
    """데이터 초기화 (재처리용) - Firebase 파일 삭제"""
    # Storage 파일 삭제
    delete_file(f"logs/{file_id}.log")
    delete_file(f"outputs/json/{file_id}.json")
    delete_file(f"outputs/json/{file_id}_log.jsonl")
    delete_files_with_prefix(f"outputs/excel/{file_id}")

    # DB 초기화
    update_db_status(
        file_id, "Ready",
        progress=0,
        ai_verified=False,
        current_page=0,
        error_msg=""
    )
    write_log(file_id, "[RESET] 데이터가 초기화되었습니다.")


def update_json_manual(file_id: str, questions: list, passages: list = None, meta: dict = None) -> None:
    """프론트엔드에서의 수동 수정 반영"""
    data = load_json_data(file_id)
    if not data:
        data = {"meta": {}, "questions": [], "passages": []}

    data['questions'] = questions
    if passages is not None:
        data['passages'] = passages
    if meta is not None:
        data['meta'].update(meta)
    data['meta']['modified_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_json_data(file_id, data)

    update_db_status(file_id, "Modified", progress=100)
    write_log(file_id, "[EDIT] 사용자가 데이터를 수동으로 수정했습니다.")


# --- 스레드 실행 래퍼 ---

def run_thread(target, args: tuple) -> None:
    """백그라운드 스레드 실행"""
    t = threading.Thread(target=target, args=args)
    t.daemon = True
    t.start()
