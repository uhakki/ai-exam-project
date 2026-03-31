"""
kice_importer.py
KICE_slayer_AI_Korean 데이터를 시스템 JSON 스키마로 변환하여 Firebase에 저장
"""

import json
import uuid
import subprocess
import tempfile
import os
from datetime import datetime
from typing import Optional


# KICE type → 시스템 category 매핑
TYPE_TO_CATEGORY = {
    0: "독서",       # 비문학
    1: "문학",       # 문학
    2: "화법과작문",  # 화법과 작문
    3: "문법",       # 문법
}

# 수능 연도 → 시행 정보
EXAM_INFO = {
    "exam_type": "수능",
    "subject": "국어",
    "grade": "고3",
}

# GitHub raw URL 패턴
GITHUB_API_URL = "https://api.github.com/repos/NomaDamas/KICE_slayer_AI_Korean/contents/data"

# 선지 번호 기호
CHOICE_SYMBOLS = ["①", "②", "③", "④", "⑤"]


def fetch_available_files() -> list[dict]:
    """GitHub에서 사용 가능한 KICE 데이터 파일 목록 조회"""
    try:
        result = subprocess.run(
            ["gh", "api", GITHUB_API_URL, "--jq",
             '[.[] | select(.name | endswith(".json")) | {name: .name, download_url: .download_url, size: .size}]'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


def download_kice_file(filename: str) -> Optional[list]:
    """GitHub API를 통해 KICE JSON 파일 다운로드"""
    try:
        result = subprocess.run(
            ["gh", "api", f"{GITHUB_API_URL}/{filename}",
             "--jq", ".content"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            import base64
            content = base64.b64decode(result.stdout.strip())
            return json.loads(content.decode("utf-8"))
    except Exception:
        pass
    return None


def parse_year_from_filename(filename: str) -> str:
    """파일명에서 연도 추출: 2023_11_KICE.json → 2023"""
    return filename.split("_")[0]


def parse_month_from_filename(filename: str) -> str:
    """파일명에서 월 추출: 2023_11_KICE.json → 11"""
    parts = filename.split("_")
    return parts[1] if len(parts) > 1 else ""


def convert_kice_to_system(kice_data: list, filename: str) -> dict:
    """
    KICE_slayer JSON → 시스템 JSON 스키마 변환

    KICE 구조:
    [
      {
        "id": "2023_11_KICE_1-3",
        "paragraph": "지문 텍스트...",
        "type": 0,
        "problems": [
          {
            "question": "발문",
            "choices": ["선지1", ...],
            "answer": 1,
            "score": 2,
            "question_plus": "보기 텍스트",  (optional)
            "no_paragraph": true  (optional)
          }
        ]
      }
    ]

    시스템 구조:
    {
      "meta": {...},
      "passages": [{passage_id, page_num, category, passage_content, ...}],
      "questions": [{passage_id, page_num, q_num, q_stem, choice_1~5, ...}]
    }
    """
    year = parse_year_from_filename(filename)
    month = parse_month_from_filename(filename)
    file_id = uuid.uuid4().hex[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    meta = {
        "file_id": file_id,
        "subject": EXAM_INFO["subject"],
        "year": year,
        "exam_type": EXAM_INFO["exam_type"],
        "grade": EXAM_INFO["grade"],
        "month": month,
        "semester": "",
        "school": "",
        "author": "KICE (한국교육과정평가원)",
        "desc": f"{year}학년도 대학수학능력시험 국어영역",
        "created_at": now,
        "source": "KICE_slayer_AI_Korean",
    }

    passages = []
    questions = []
    passage_counter = 0
    q_num_counter = 0  # 실제 문항번호 추적

    for section in kice_data:
        section_id = section.get("id", "")
        paragraph = section.get("paragraph", "")
        section_type = section.get("type", 0)
        problems = section.get("problems", [])
        category = TYPE_TO_CATEGORY.get(section_type, "독서")

        # 문항 번호 범위 파싱 (예: "2023_11_KICE_1-3" → 1~3)
        q_range_start = q_num_counter + 1
        if "-" in section_id.split("_")[-1]:
            try:
                parts = section_id.split("_")[-1].split("-")
                q_range_start = int(parts[0])
            except ValueError:
                pass
        elif section_id.split("_")[-1].isdigit():
            q_range_start = int(section_id.split("_")[-1])

        # passage 생성 (paragraph가 있는 경우)
        passage_id = None
        if paragraph.strip():
            passage_counter += 1
            passage_id = f"P{passage_counter:03d}"
            passages.append({
                "passage_id": passage_id,
                "page_num": passage_counter,  # 가상 페이지 번호
                "category": category,
                "passage_content": paragraph.strip(),
                "is_continued_from_prev": False,
                "continues_to_next": False,
            })

        # 문항 변환
        for i, prob in enumerate(problems):
            q_num_counter = q_range_start + i
            prob_type = prob.get("type", section_type)
            prob_category = TYPE_TO_CATEGORY.get(prob_type, category)

            # no_paragraph인 경우 passage 연결 안 함
            q_passage_id = None if prob.get("no_paragraph") else passage_id

            # 선지 변환
            choices = prob.get("choices", [])
            choice_fields = {}
            for j in range(5):
                if j < len(choices) and choices[j]:
                    choice_fields[f"choice_{j+1}"] = f"{CHOICE_SYMBOLS[j]} {choices[j]}"
                else:
                    choice_fields[f"choice_{j+1}"] = ""

            question = {
                "passage_id": q_passage_id,
                "page_num": passage_counter if passage_id else 0,
                "q_num": q_num_counter,
                "category": prob_category,
                "q_stem": prob.get("question", ""),
                "reference_box": prob.get("question_plus", ""),
                "answer": prob.get("answer"),
                "score": prob.get("score"),
                **choice_fields,
            }
            questions.append(question)

    return {
        "meta": meta,
        "passages": passages,
        "questions": questions,
        "file_id": file_id,
    }


def save_to_firebase(converted: dict) -> str:
    """변환된 데이터를 Firebase에 저장"""
    from storage_backend import save_json_data, save_entry

    file_id = converted["file_id"]
    data = {
        "meta": converted["meta"],
        "passages": converted["passages"],
        "questions": converted["questions"],
    }

    # JSON 데이터 저장
    save_json_data(file_id, data)

    # Firestore 문서 등록
    entry = {
        "file_id": file_id,
        "filename": f"{converted['meta']['year']}_{converted['meta']['month']}_KICE.json",
        "filepath": f"outputs/json/{file_id}.json",
        "subject": converted["meta"]["subject"],
        "year": converted["meta"]["year"],
        "exam_type": converted["meta"]["exam_type"],
        "grade": converted["meta"]["grade"],
        "month": converted["meta"]["month"],
        "semester": "",
        "school": "",
        "author": converted["meta"]["author"],
        "desc": converted["meta"]["desc"],
        "status": "Extracted",
        "progress": 100,
        "current_page": 0,
        "total_pages": 0,
        "ai_verified": False,
        "error_msg": "",
        "last_updated": converted["meta"]["created_at"],
        "source": "KICE_slayer_AI_Korean",
    }
    save_entry(entry)

    return file_id


def import_kice_exam(filename: str) -> dict:
    """KICE 시험 데이터 가져오기 (다운로드 → 변환 → 저장) 통합 함수"""
    # 1) 다운로드
    kice_data = download_kice_file(filename)
    if not kice_data:
        return {"success": False, "error": f"파일 다운로드 실패: {filename}"}

    # 2) 변환
    converted = convert_kice_to_system(kice_data, filename)

    # 3) 통계
    stats = {
        "passages": len(converted["passages"]),
        "questions": len(converted["questions"]),
        "total_score": sum(q.get("score", 0) for q in converted["questions"]),
        "categories": list(set(q["category"] for q in converted["questions"])),
    }

    # 4) Firebase 저장
    try:
        file_id = save_to_firebase(converted)
        return {
            "success": True,
            "file_id": file_id,
            "stats": stats,
            "meta": converted["meta"],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "stats": stats}


def import_from_local_json(json_data: list, filename: str) -> dict:
    """로컬 JSON 데이터에서 직접 변환 (파일 업로드용)"""
    converted = convert_kice_to_system(json_data, filename)
    stats = {
        "passages": len(converted["passages"]),
        "questions": len(converted["questions"]),
        "total_score": sum(q.get("score", 0) for q in converted["questions"]),
        "categories": list(set(q["category"] for q in converted["questions"])),
    }
    try:
        file_id = save_to_firebase(converted)
        return {
            "success": True,
            "file_id": file_id,
            "stats": stats,
            "meta": converted["meta"],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "stats": stats}


# 테스트용
if __name__ == "__main__":
    # 로컬 테스트: temp_kice_2023.json이 있다면
    test_file = "temp_kice_2023.json"
    if os.path.exists(test_file):
        with open(test_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        converted = convert_kice_to_system(data, "2023_11_KICE.json")
        print(f"Meta: {converted['meta']['desc']}")
        print(f"Passages: {len(converted['passages'])}")
        print(f"Questions: {len(converted['questions'])}")
        print(f"Total score: {sum(q.get('score', 0) for q in converted['questions'])}")

        # 첫 번째 passage 출력
        if converted["passages"]:
            p = converted["passages"][0]
            print(f"\n--- 첫 지문 (P001) ---")
            print(f"Category: {p['category']}")
            print(f"Content: {p['passage_content'][:100]}...")

        # 첫 번째 question 출력
        if converted["questions"]:
            q = converted["questions"][0]
            print(f"\n--- 첫 문항 ---")
            print(f"Q{q['q_num']}. {q['q_stem'][:80]}...")
            print(f"Passage: {q['passage_id']}, Answer: {q['answer']}, Score: {q['score']}")
            for i in range(1, 6):
                c = q.get(f"choice_{i}", "")
                if c:
                    print(f"  {c[:60]}...")
    else:
        print("테스트 파일 없음. GitHub에서 가져오기:")
        files = fetch_available_files()
        for f in files:
            print(f"  {f['name']} ({f['size']} bytes)")
