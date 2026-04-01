"""
batch_upload.py
시험지 PDF 일괄 업로드 + AI 추출 스크립트
- exam_db 폴더의 PDF를 파싱하여 Firebase에 업로드
- 파일명/폴더 경로에서 메타데이터 자동 추출
- 업로드 후 Gemini AI 추출까지 자동 실행
"""

import os
import re
import sys
import uuid
import time
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Firebase 초기화 (Streamlit 없이)
os.environ.setdefault("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

from firebase_config import get_firestore_client, get_storage_bucket
from storage_backend import (
    save_entry, upload_file, get_db, write_log, save_json_data,
    append_jsonl, load_jsonl, get_processed_pages, upload_bytes,
    get_item_by_id, update_db_status
)


def parse_exam_metadata(filepath: str) -> dict:
    """파일 경로 + 파일명에서 메타데이터를 추출"""
    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]
    dirpath = filepath.replace("\\", "/")

    meta = {
        "year": "",
        "semester": "",
        "exam_type": "",
        "grade": "",
        "school": "",
        "school_level": "",  # 중등 / 고등
        "subject": "국어",
    }

    # --- 연도 추출 ---
    year_match = re.search(r'(20\d{2})', name_no_ext)
    if year_match:
        meta["year"] = year_match.group(1)
    else:
        # 폴더에서 추출
        year_match = re.search(r'(20\d{2})', dirpath)
        if year_match:
            meta["year"] = year_match.group(1)

    # --- 학교급 추출 (폴더 기반) ---
    if "중등" in dirpath or "중학" in dirpath:
        meta["school_level"] = "중등"
    elif "고등" in dirpath or "고교" in dirpath:
        meta["school_level"] = "고등"

    # --- 학기 추출 ---
    sem_match = re.search(r'([12])학기', name_no_ext) or re.search(r'([12])학기', dirpath)
    if sem_match:
        meta["semester"] = f"{sem_match.group(1)}학기"

    # --- 시험유형 추출 ---
    if "중간" in name_no_ext or "중간" in dirpath:
        meta["exam_type"] = "중간고사"
    elif "기말" in name_no_ext or "기말" in dirpath:
        meta["exam_type"] = "기말고사"
    elif "모의" in name_no_ext or "모의" in dirpath:
        meta["exam_type"] = "모의고사"
    elif "수능" in name_no_ext or "수능" in dirpath:
        meta["exam_type"] = "수능"

    # --- 학년 추출 ---
    # 파일명에서: "2학년", "3학년" 등 (단, "2024학년" 같은 연도 패턴 제외)
    grade_match = re.search(r'(?<!\d)(\d)학년', name_no_ext)
    if grade_match:
        g = grade_match.group(1)
        if meta["school_level"] == "중등":
            meta["grade"] = f"중{g}"
        elif meta["school_level"] == "고등":
            meta["grade"] = f"고{g}"
        else:
            meta["grade"] = f"{g}학년"
    else:
        # 폴더명에서: "중2", "중3", "고1" 등
        folder_grade = re.search(r'[/\\](중|고)(\d)[/\\]?', dirpath)
        if folder_grade:
            prefix = folder_grade.group(1)
            num = folder_grade.group(2)
            meta["grade"] = f"{prefix}{num}"
            if prefix == "중":
                meta["school_level"] = "중등"
            else:
                meta["school_level"] = "고등"

    # --- 학교명 추출 ---
    # 패턴1: "2025년 1학기 중간고사 [학교명] 3학년"
    school_match = re.search(
        r'(?:중간고사|기말고사|모의고사)\s+(.+?)\s+\d학년', name_no_ext
    )
    if school_match:
        meta["school"] = school_match.group(1).strip()
    else:
        # 패턴2: "2023년 1학기 [학교명] 2학년 중간고사 시험지"
        school_match2 = re.search(
            r'\d학기\s+(.+?)\s+\d학년', name_no_ext
        )
        if school_match2:
            school_name = school_match2.group(1).strip()
            # "중간고사" 등이 포함된 경우 제거
            school_name = re.sub(r'(중간고사|기말고사|모의고사|수능)', '', school_name).strip()
            if school_name:
                meta["school"] = school_name

    # 패턴3: 파일명이 "학교명 기출시험지.pdf" 같은 간단한 형태
    if not meta["school"]:
        simple_match = re.search(r'^(.+?)(중|여중|고)\s*(기출|시험)', name_no_ext)
        if simple_match:
            meta["school"] = simple_match.group(1).strip() + simple_match.group(2)

    return meta


def generate_storage_filename(meta: dict, file_id: str) -> str:
    """계층적 Firebase Storage 경로 생성"""
    year = meta.get("year", "기타")
    school_level = meta.get("school_level", "기타")
    grade = meta.get("grade", "기타")
    semester = meta.get("semester", "기타")
    exam_type = meta.get("exam_type", "기타")
    school = meta.get("school", "미상")

    # inputs/2025/중등/중2/1학기/중간고사/{file_id}_{school}.pdf
    storage_path = f"inputs/{year}/{school_level}/{grade}/{semester}/{exam_type}/{file_id}_{school}.pdf"
    return storage_path


def generate_display_name(meta: dict) -> str:
    """사람이 읽을 수 있는 표시용 파일명 생성"""
    parts = []
    if meta["year"]:
        parts.append(f"{meta['year']}년")
    if meta["semester"]:
        parts.append(meta["semester"])
    if meta["exam_type"]:
        parts.append(meta["exam_type"])
    if meta["school"]:
        parts.append(meta["school"])
    if meta["grade"]:
        parts.append(meta["grade"])

    return " ".join(parts) if parts else "시험지"


def collect_target_files(base_dir: str, filters: dict = None) -> list:
    """
    대상 PDF 파일 목록 수집
    filters: {"school_level": "중등", "semester": "1학기", "exam_type": "중간고사"}
    """
    target_files = []

    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if not f.lower().endswith('.pdf'):
                continue

            filepath = os.path.join(root, f)
            meta = parse_exam_metadata(filepath)

            # 필터 적용
            if filters:
                skip = False
                for key, val in filters.items():
                    if val and meta.get(key, "") != val:
                        # 부분 매칭 (예: "중간" in "중간고사")
                        if val not in meta.get(key, ""):
                            skip = True
                            break
                if skip:
                    continue

            target_files.append({
                "filepath": filepath,
                "filename": f,
                "meta": meta,
            })

    return target_files


def upload_single_file(file_info: dict, dry_run: bool = False) -> dict:
    """단일 파일 업로드 + Firestore 등록"""
    filepath = file_info["filepath"]
    meta = file_info["meta"]

    file_id = str(uuid.uuid4())[:8]
    display_name = generate_display_name(meta)
    storage_path = generate_storage_filename(meta, file_id)

    if dry_run:
        return {
            "file_id": file_id,
            "display_name": display_name,
            "storage_path": storage_path,
            "meta": meta,
            "status": "dry_run"
        }

    # Firebase Storage에 업로드
    upload_file(filepath, storage_path)

    # Firestore에 문서 등록
    entry = {
        "file_id": file_id,
        "filename": f"{display_name}.pdf",
        "filepath": storage_path,
        "subject": meta.get("subject", "국어"),
        "year": meta.get("year", ""),
        "exam_type": meta.get("exam_type", ""),
        "grade": meta.get("grade", ""),
        "month": "",
        "semester": meta.get("semester", ""),
        "school": meta.get("school", ""),
        "school_level": meta.get("school_level", ""),
        "author": "",
        "desc": "",
        "status": "Ready",
        "progress": 0,
        "current_page": 0,
        "total_pages": 0,
        "ai_verified": False,
        "error_msg": "",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_path": filepath,  # 원본 로컬 경로 (참고용)
    }

    save_entry(entry)

    return {
        "file_id": file_id,
        "display_name": display_name,
        "storage_path": storage_path,
        "meta": meta,
        "status": "uploaded"
    }


def extract_single_file(file_id: str, model_type: str = "flash") -> bool:
    """단일 파일 AI 추출 실행 (동기)"""
    from backend import task_extract_json
    try:
        item = get_item_by_id(file_id)
        if not item:
            print(f"  [ERROR] {file_id} 문서를 찾을 수 없습니다.")
            return False
        filepath = item["filepath"]
        metadata = {**item, "model_type": model_type}
        task_extract_json(file_id, filepath, metadata)
        return True
    except Exception as e:
        print(f"  [ERROR] {file_id} 추출 실패: {e}")
        traceback.print_exc()
        return False


def batch_upload_and_extract(
    base_dir: str,
    filters: dict = None,
    do_extract: bool = True,
    model_type: str = "flash",
    dry_run: bool = False
):
    """
    일괄 업로드 + 추출 메인 함수
    """
    print("=" * 60)
    print("시험지 일괄 업로드 시작")
    print(f"  대상 폴더: {base_dir}")
    print(f"  필터: {filters}")
    print(f"  AI 추출: {do_extract}")
    print(f"  모델: {model_type}")
    print(f"  Dry Run: {dry_run}")
    print("=" * 60)

    # 1. 대상 파일 수집
    files = collect_target_files(base_dir, filters)
    print(f"\n총 {len(files)}개 파일 발견\n")

    if not files:
        print("대상 파일이 없습니다.")
        return

    # 중복 체크: 이미 DB에 같은 학교+연도+학기+시험유형+학년 조합이 있으면 건너뜀
    existing_db = get_db()
    existing_keys = set()
    for doc in existing_db:
        key = f"{doc.get('year')}_{doc.get('school')}_{doc.get('grade')}_{doc.get('semester')}_{doc.get('exam_type')}"
        existing_keys.add(key)

    # 2. 업로드
    uploaded = []
    skipped = 0

    for i, file_info in enumerate(files, 1):
        meta = file_info["meta"]
        display = generate_display_name(meta)
        dup_key = f"{meta['year']}_{meta['school']}_{meta['grade']}_{meta['semester']}_{meta['exam_type']}"

        if dup_key in existing_keys and not dry_run:
            print(f"  [{i}/{len(files)}] SKIP (중복) {display}")
            skipped += 1
            continue

        print(f"  [{i}/{len(files)}] 업로드: {display}")

        try:
            result = upload_single_file(file_info, dry_run=dry_run)
            uploaded.append(result)
            existing_keys.add(dup_key)

            if dry_run:
                print(f"    -> [DRY] {result['storage_path']}")
            else:
                print(f"    -> OK: {result['file_id']} | {result['storage_path']}")
        except Exception as e:
            print(f"    -> FAIL: {e}")

    print(f"\n업로드 완료: {len(uploaded)}개 성공, {skipped}개 중복 건너뜀")

    # 3. AI 추출
    if do_extract and not dry_run and uploaded:
        print(f"\n{'=' * 60}")
        print(f"AI 추출 시작 ({len(uploaded)}개 파일)")
        print(f"{'=' * 60}")

        success = 0
        fail = 0

        for i, result in enumerate(uploaded, 1):
            file_id = result["file_id"]
            display = result["display_name"]
            print(f"\n  [{i}/{len(uploaded)}] 추출 중: {display} ({file_id})")

            ok = extract_single_file(file_id, model_type=model_type)
            if ok:
                success += 1
                print(f"    -> 추출 완료")
            else:
                fail += 1
                print(f"    -> 추출 실패")

            # API rate limit 방지
            if i < len(uploaded):
                time.sleep(2)

        print(f"\n추출 완료: {success}개 성공, {fail}개 실패")

    print(f"\n{'=' * 60}")
    print("작업 완료!")
    print(f"{'=' * 60}")

    return uploaded


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="시험지 일괄 업로드")
    parser.add_argument("--dir", default="exam_db", help="시험지 폴더 경로")
    parser.add_argument("--school-level", default="", help="학교급 필터 (중등/고등)")
    parser.add_argument("--semester", default="", help="학기 필터 (1학기/2학기)")
    parser.add_argument("--exam-type", default="", help="시험유형 필터 (중간고사/기말고사)")
    parser.add_argument("--no-extract", action="store_true", help="AI 추출 건너뜀")
    parser.add_argument("--model", default="flash", choices=["flash", "pro"], help="AI 모델")
    parser.add_argument("--dry-run", action="store_true", help="실제 업로드 없이 시뮬레이션")
    args = parser.parse_args()

    filters = {}
    if args.school_level:
        filters["school_level"] = args.school_level
    if args.semester:
        filters["semester"] = args.semester
    if args.exam_type:
        filters["exam_type"] = args.exam_type

    base_dir = os.path.join(os.path.dirname(__file__), args.dir)

    batch_upload_and_extract(
        base_dir=base_dir,
        filters=filters if filters else None,
        do_extract=not args.no_extract,
        model_type=args.model,
        dry_run=args.dry_run,
    )
