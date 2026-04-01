"""
batch_extract.py
Firebase에 업로드된 Ready 상태 문서들의 AI 추출을 일괄 실행
"""

import os
import sys
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

from storage_backend import get_db, get_item_by_id, update_db_status
from backend import task_extract_json


def batch_extract(model_type: str = "flash", filters: dict = None, limit: int = 0):
    """Ready 상태 문서들을 일괄 추출"""
    print("=" * 60)
    print("AI 추출 일괄 실행")
    print(f"  모델: {model_type}")
    print(f"  필터: {filters}")
    print("=" * 60)

    db = get_db()

    # Ready 상태만 필터
    targets = [doc for doc in db if doc.get("status") == "Ready"]

    # 추가 필터 적용
    if filters:
        for key, val in filters.items():
            if val:
                targets = [doc for doc in targets if val in doc.get(key, "")]

    if limit > 0:
        targets = targets[:limit]

    print(f"\n추출 대상: {len(targets)}개 문서\n")

    if not targets:
        print("추출할 문서가 없습니다.")
        return

    success = 0
    fail = 0

    for i, doc in enumerate(targets, 1):
        file_id = doc["file_id"]
        filepath = doc.get("filepath", "")
        display = doc.get("filename", file_id)
        metadata = {**doc, "model_type": model_type}

        print(f"  [{i}/{len(targets)}] {display} ({file_id})")

        try:
            task_extract_json(file_id, filepath, metadata)

            # 추출 후 상태 확인
            updated = get_item_by_id(file_id)
            status = updated.get("status", "Unknown") if updated else "Unknown"

            if status in ["Extracted", "Modified", "Done"]:
                success += 1
                print(f"    -> 완료 (상태: {status})")
            else:
                fail += 1
                error = updated.get("error_msg", "") if updated else ""
                print(f"    -> 실패 (상태: {status}, 오류: {error})")

        except Exception as e:
            fail += 1
            print(f"    -> 오류: {e}")
            traceback.print_exc()

        # API rate limit 방지
        if i < len(targets):
            time.sleep(3)

    print(f"\n{'=' * 60}")
    print(f"추출 완료: {success}개 성공, {fail}개 실패")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI 추출 일괄 실행")
    parser.add_argument("--model", default="flash", choices=["flash", "pro"])
    parser.add_argument("--school-level", default="")
    parser.add_argument("--year", default="")
    parser.add_argument("--grade", default="")
    parser.add_argument("--limit", type=int, default=0, help="최대 처리 수 (0=전체)")
    args = parser.parse_args()

    filters = {}
    if args.school_level:
        filters["school_level"] = args.school_level
    if args.year:
        filters["year"] = args.year
    if args.grade:
        filters["grade"] = args.grade

    batch_extract(
        model_type=args.model,
        filters=filters if filters else None,
        limit=args.limit,
    )
