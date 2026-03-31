"""
migrate_to_firebase.py
기존 로컬 데이터를 Firebase로 마이그레이션하는 1회성 스크립트

사용법:
    python migrate_to_firebase.py

사전 조건:
    - firebase_credentials.json이 프로젝트 루트에 존재
    - 기존 database.json, inputs/, outputs/, logs/ 디렉토리가 존재
"""

import json
import os
from pathlib import Path

# Firebase 모듈 임포트
from firebase_config import get_firestore_client, get_storage_bucket
from storage_backend import upload_file, save_entry

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "database.json"
INPUT_DIR = BASE_DIR / "inputs"
OUTPUT_JSON_DIR = BASE_DIR / "outputs" / "json"
OUTPUT_EXCEL_DIR = BASE_DIR / "outputs" / "excel"
LOG_DIR = BASE_DIR / "logs"


def migrate_database():
    """database.json → Firestore 마이그레이션"""
    if not DB_PATH.exists():
        print("[SKIP] database.json이 없습니다.")
        return

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    print(f"[INFO] {len(db)}개 항목 마이그레이션 시작...")

    for item in db:
        file_id = item["file_id"]

        # filepath를 Storage 경로로 변환
        old_path = item.get("filepath", "")
        if old_path:
            filename = os.path.basename(old_path)
            item["filepath"] = f"inputs/{filename}"

        # excel_path를 Storage 경로로 변환
        old_excel = item.get("excel_path", "")
        if old_excel:
            excel_name = os.path.basename(old_excel)
            item["excel_path"] = f"outputs/excel/{excel_name}"

        save_entry(item)
        print(f"  [OK] {file_id}: {item.get('filename', '?')}")

    print(f"[DONE] Firestore 마이그레이션 완료: {len(db)}개 항목")


def migrate_files():
    """로컬 파일 → Firebase Storage 업로드"""

    # 1) inputs/ 폴더
    if INPUT_DIR.exists():
        files = list(INPUT_DIR.glob("*"))
        print(f"\n[INFO] inputs/ 폴더: {len(files)}개 파일")
        for f in files:
            storage_path = f"inputs/{f.name}"
            upload_file(str(f), storage_path)
            print(f"  [OK] {storage_path}")
    else:
        print("[SKIP] inputs/ 폴더가 없습니다.")

    # 2) outputs/json/ 폴더
    if OUTPUT_JSON_DIR.exists():
        files = list(OUTPUT_JSON_DIR.glob("*"))
        print(f"\n[INFO] outputs/json/ 폴더: {len(files)}개 파일")
        for f in files:
            storage_path = f"outputs/json/{f.name}"
            upload_file(str(f), storage_path)
            print(f"  [OK] {storage_path}")
    else:
        print("[SKIP] outputs/json/ 폴더가 없습니다.")

    # 3) outputs/excel/ 폴더
    if OUTPUT_EXCEL_DIR.exists():
        files = list(OUTPUT_EXCEL_DIR.glob("*"))
        print(f"\n[INFO] outputs/excel/ 폴더: {len(files)}개 파일")
        for f in files:
            storage_path = f"outputs/excel/{f.name}"
            upload_file(str(f), storage_path)
            print(f"  [OK] {storage_path}")
    else:
        print("[SKIP] outputs/excel/ 폴더가 없습니다.")

    # 4) logs/ 폴더
    if LOG_DIR.exists():
        files = list(LOG_DIR.glob("*.log"))
        print(f"\n[INFO] logs/ 폴더: {len(files)}개 파일")
        for f in files:
            storage_path = f"logs/{f.name}"
            upload_file(str(f), storage_path)
            print(f"  [OK] {storage_path}")
    else:
        print("[SKIP] logs/ 폴더가 없습니다.")

    print("\n[DONE] 파일 마이그레이션 완료")


def main():
    print("=" * 60)
    print("Firebase 마이그레이션 시작")
    print("=" * 60)

    # 1단계: Firestore에 데이터베이스 마이그레이션
    print("\n--- 1단계: Firestore 마이그레이션 ---")
    migrate_database()

    # 2단계: Firebase Storage에 파일 업로드
    print("\n--- 2단계: Storage 파일 업로드 ---")
    migrate_files()

    print("\n" + "=" * 60)
    print("마이그레이션 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
