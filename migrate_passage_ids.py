"""
migrate_passage_ids.py
기존 문서에 passage_id를 일괄 부여하는 1회성 마이그레이션 스크립트.

전략:
1) JSONL이 있는 문서: 계층 구조(passage→related_questions)를 활용해 정확한 passage_id 부여
2) JSONL이 없는 문서: flat 데이터에서 page_num 순 정렬 후 ID 부여, questions는 page_num+category로 매칭
"""

import json
from storage_backend import (
    get_db, load_jsonl, load_json_data, save_json_data,
)


def assign_ids_from_jsonl(file_id: str, data: dict) -> dict:
    """JSONL 계층 구조를 활용해 passage_id 부여 (_save_final_json과 동일 알고리즘)"""
    entries = load_jsonl(file_id)
    if not entries:
        return None

    entries.sort(key=lambda e: e.get("page_num", 0))

    passages = []
    questions = []
    passage_counter = 0
    last_passage_id = None

    for entry in entries:
        if entry.get("status") != "success" or not entry.get("data"):
            continue
        for item in entry["data"]:
            current_passage_id = None

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
                    "continues_to_next": item.get("continues_to_next", False),
                })

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
                    "ai_note": q.get("ai_note", ""),
                })

    data["passages"] = passages
    data["questions"] = questions
    return data


def assign_ids_from_flat(data: dict) -> dict:
    """JSONL 없이 flat 데이터에서 passage_id 부여 (page_num 순)"""
    passages = data.get("passages", [])
    questions = data.get("questions", [])

    passages.sort(key=lambda p: p.get("page_num", 0))

    counter = 0
    last_id = None

    for p in passages:
        if p.get("is_continued_from_prev") and last_id:
            p["passage_id"] = last_id
        else:
            counter += 1
            p["passage_id"] = f"P{counter:03d}"
        last_id = p["passage_id"]

    # questions: page_num + category로 passage 매칭
    for q in questions:
        q_page = q.get("page_num")
        q_cat = q.get("category", "")
        matched_pid = None

        # 같은 page_num + category 매칭
        for p in passages:
            if p.get("page_num") == q_page and p.get("category") == q_cat:
                matched_pid = p["passage_id"]
                break

        # category 불일치시 같은 page_num 매칭
        if not matched_pid:
            for p in passages:
                if p.get("page_num") == q_page:
                    matched_pid = p["passage_id"]
                    break

        q["passage_id"] = matched_pid  # 매칭 안되면 None

    data["passages"] = passages
    data["questions"] = questions
    return data


def migrate():
    db = get_db()
    print(f"총 {len(db)}개 문서 발견")

    success = 0
    skip = 0
    fail = 0

    for item in db:
        file_id = item["file_id"]
        status = item.get("status", "")

        # 추출 완료되지 않은 문서는 건너뛰기
        if status not in ("Extracted", "Modified", "Done"):
            print(f"  [{file_id}] SKIP - 상태: {status}")
            skip += 1
            continue

        data = load_json_data(file_id)
        if not data:
            print(f"  [{file_id}] SKIP - JSON 없음")
            skip += 1
            continue

        # 이미 passage_id가 있는지 확인
        passages = data.get("passages", [])
        if passages and passages[0].get("passage_id"):
            print(f"  [{file_id}] SKIP - 이미 passage_id 존재")
            skip += 1
            continue

        try:
            # 1차: JSONL에서 재파생
            result = assign_ids_from_jsonl(file_id, data)

            if result:
                print(f"  [{file_id}] OK - JSONL 기반 (지문 {len(result['passages'])}개, 문항 {len(result['questions'])}개)")
            else:
                # 2차: flat fallback
                result = assign_ids_from_flat(data)
                print(f"  [{file_id}] OK - flat 기반 (지문 {len(result['passages'])}개, 문항 {len(result['questions'])}개)")

            save_json_data(file_id, result)
            success += 1

        except Exception as e:
            print(f"  [{file_id}] FAIL - {e}")
            fail += 1

    print(f"\n완료: 성공 {success}, 스킵 {skip}, 실패 {fail}")


if __name__ == "__main__":
    migrate()
