"""
storage_backend.py
Firebase 기반 스토리지 백엔드
- Firestore: database.json 대체 (documents 컬렉션)
- Firebase Storage: 로컬 파일 시스템 대체 (inputs/, outputs/, logs/)
"""

import json
import tempfile
import os
from datetime import datetime
from typing import Optional
from firebase_config import get_firestore_client, get_storage_bucket

# Firestore 컬렉션 이름
COLLECTION = "documents"


# =============================================================================
# Firestore DB 함수 (database.json 대체)
# =============================================================================

def get_db() -> list:
    """데이터베이스 전체 조회 (database.json 대체)"""
    db = get_firestore_client()
    docs = db.collection(COLLECTION).stream()
    return [doc.to_dict() for doc in docs]


def get_item_by_id(file_id: str) -> Optional[dict]:
    """ID로 단일 문서 조회"""
    db = get_firestore_client()
    doc = db.collection(COLLECTION).document(file_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


def save_entry(entry: dict) -> None:
    """새 문서 추가"""
    db = get_firestore_client()
    file_id = entry["file_id"]
    db.collection(COLLECTION).document(file_id).set(entry)


def update_db_status(
    file_id: str,
    status: str,
    progress: int = None,
    ai_verified: bool = None,
    current_page: int = None,
    total_pages: int = None,
    error_msg: str = None,
    **kwargs
) -> None:
    """DB 상태 업데이트 (atomic)"""
    db = get_firestore_client()
    updates = {
        "status": status,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if progress is not None:
        updates["progress"] = progress
    if ai_verified is not None:
        updates["ai_verified"] = ai_verified
    if current_page is not None:
        updates["current_page"] = current_page
    if total_pages is not None:
        updates["total_pages"] = total_pages
    if error_msg is not None:
        updates["error_msg"] = error_msg
    updates.update(kwargs)

    db.collection(COLLECTION).document(file_id).update(updates)


def update_db_fields(file_id: str, **fields) -> None:
    """DB 임의 필드 업데이트"""
    db = get_firestore_client()
    db.collection(COLLECTION).document(file_id).update(fields)


def delete_document(file_id: str) -> None:
    """Firestore 문서 삭제"""
    db = get_firestore_client()
    db.collection(COLLECTION).document(file_id).delete()


# =============================================================================
# Firebase Storage 파일 함수 (로컬 파일 시스템 대체)
# =============================================================================

def upload_file(local_path: str, storage_path: str) -> str:
    """로컬 파일을 Firebase Storage에 업로드"""
    bucket = get_storage_bucket()
    blob = bucket.blob(storage_path)
    blob.upload_from_filename(local_path)
    return storage_path


def upload_bytes(data: bytes, storage_path: str, content_type: str = None) -> str:
    """바이트 데이터를 Firebase Storage에 업로드"""
    bucket = get_storage_bucket()
    blob = bucket.blob(storage_path)
    blob.upload_from_string(data, content_type=content_type)
    return storage_path


def download_file(storage_path: str, local_path: str) -> str:
    """Firebase Storage에서 로컬로 다운로드"""
    bucket = get_storage_bucket()
    blob = bucket.blob(storage_path)
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    blob.download_to_filename(local_path)
    return local_path


def download_to_bytes(storage_path: str) -> bytes:
    """Firebase Storage에서 메모리로 다운로드"""
    bucket = get_storage_bucket()
    blob = bucket.blob(storage_path)
    return blob.download_as_bytes()


def file_exists(storage_path: str) -> bool:
    """Storage 파일 존재 여부 확인"""
    bucket = get_storage_bucket()
    blob = bucket.blob(storage_path)
    return blob.exists()


def delete_file(storage_path: str) -> None:
    """Storage 파일 삭제"""
    bucket = get_storage_bucket()
    blob = bucket.blob(storage_path)
    if blob.exists():
        blob.delete()


def delete_files_with_prefix(prefix: str) -> int:
    """특정 접두어로 시작하는 파일 모두 삭제"""
    bucket = get_storage_bucket()
    blobs = list(bucket.list_blobs(prefix=prefix))
    count = 0
    for blob in blobs:
        blob.delete()
        count += 1
    return count


# =============================================================================
# 로그 함수 (logs/{file_id}.log 대체)
# =============================================================================

def write_log(file_id: str, message: str) -> None:
    """실시간 로그 기록 (Storage에 append)"""
    storage_path = f"logs/{file_id}.log"
    timestamp = datetime.now().strftime("%H:%M:%S")
    new_line = f"[{timestamp}] {message}\n"

    # 기존 로그 읽기 + append
    try:
        existing = download_to_bytes(storage_path).decode("utf-8")
    except Exception:
        existing = ""

    updated = existing + new_line
    upload_bytes(updated.encode("utf-8"), storage_path, content_type="text/plain")


def read_log(file_id: str) -> str:
    """로그 읽기"""
    storage_path = f"logs/{file_id}.log"
    try:
        return download_to_bytes(storage_path).decode("utf-8")
    except Exception:
        return "로그 없음"


# =============================================================================
# JSON 데이터 함수 (outputs/json/{file_id}.json 대체)
# =============================================================================

def save_json_data(file_id: str, data: dict) -> str:
    """JSON 데이터 저장"""
    storage_path = f"outputs/json/{file_id}.json"
    content = json.dumps(data, indent=2, ensure_ascii=False)
    upload_bytes(content.encode("utf-8"), storage_path, content_type="application/json")
    return storage_path


def load_json_data(file_id: str) -> Optional[dict]:
    """JSON 데이터 로드"""
    storage_path = f"outputs/json/{file_id}.json"
    try:
        content = download_to_bytes(storage_path).decode("utf-8")
        return json.loads(content)
    except Exception:
        return None


# =============================================================================
# JSONL 체크포인트 함수 (outputs/json/{file_id}_log.jsonl 대체)
# =============================================================================

def append_jsonl(file_id: str, entry: dict) -> None:
    """JSONL 파일에 항목 추가 (체크포인트용)"""
    storage_path = f"outputs/json/{file_id}_log.jsonl"
    new_line = json.dumps(entry, ensure_ascii=False) + "\n"

    try:
        existing = download_to_bytes(storage_path).decode("utf-8")
    except Exception:
        existing = ""

    updated = existing + new_line
    upload_bytes(updated.encode("utf-8"), storage_path, content_type="application/jsonl")


def load_jsonl(file_id: str) -> list:
    """JSONL 파일 로드"""
    storage_path = f"outputs/json/{file_id}_log.jsonl"
    try:
        content = download_to_bytes(storage_path).decode("utf-8")
        entries = []
        for line in content.strip().split("\n"):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    except Exception:
        return []


def get_processed_pages(file_id: str, pdf_name: str) -> set:
    """이미 처리된 페이지 번호 목록 반환"""
    entries = load_jsonl(file_id)
    processed = set()
    for entry in entries:
        if entry.get("pdf_name") == pdf_name:
            processed.add(entry.get("page_num"))
    return processed


# =============================================================================
# 임시 파일 헬퍼
# =============================================================================

def get_temp_dir(subfolder: str = "") -> str:
    """임시 디렉토리 경로 반환"""
    base = tempfile.mkdtemp()
    if subfolder:
        path = os.path.join(base, subfolder)
        os.makedirs(path, exist_ok=True)
        return path
    return base
