"""
parser.py
추출된 JSON 데이터를 엑셀 호환 형태로 변환하는 모듈
- JSONL 로그 파일 처리 기능
- 페이지별 데이터 병합 기능
- 지문 연결(Stitching) 로직: is_continued_from_prev 플래그 기반 병합
- 지문/문항 분리 시트 출력 기능
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional


def load_jsonl_log(log_path: str) -> list[dict]:
    """JSONL 로그 파일 로드"""
    log_file = Path(log_path)
    if not log_file.exists():
        return []

    logs = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return logs


def save_to_jsonl(data: dict, log_path: str) -> None:
    """단일 데이터를 JSONL 파일에 추가 (Append Mode)"""
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


def get_processed_pages(log_path: str, pdf_name: str) -> set[int]:
    """이미 처리된 페이지 번호 목록 반환"""
    logs = load_jsonl_log(log_path)
    processed = set()

    for log in logs:
        if log.get("pdf_name") == pdf_name:
            processed.add(log.get("page_num"))

    return processed


def merge_page_data(logs: list[dict]) -> list[dict]:
    """페이지별 추출 데이터를 하나의 리스트로 병합"""
    merged = []

    # 페이지 순서대로 정렬
    sorted_logs = sorted(logs, key=lambda x: (x.get("pdf_name", ""), x.get("page_num", 0)))

    for log in sorted_logs:
        if log.get("status") == "success":
            page_data = log.get("data", [])
            merged.extend(page_data)

    return merged


def split_exam_data(data: list[dict], pdf_name: str = "") -> tuple[list[dict], list[dict]]:
    """
    데이터를 지문과 문항으로 분리 (관계형 구조)

    Args:
        data: Gemini에서 추출한 계층형 JSON 데이터
        pdf_name: PDF 파일명 (출처 표시용)

    Returns:
        (지문 리스트, 문항 리스트) 튜플
    """
    passages_list = []
    questions_list = []

    # 지문 ID 관리 변수
    current_passage_num = 0
    last_passage_id = ""
    last_category = ""
    last_passage_content = ""

    for passage_group in data:
        # 데이터 추출
        category = passage_group.get("category", "")
        content = passage_group.get("passage_content", "")
        questions = passage_group.get("related_questions", [])
        is_continued = passage_group.get("is_continued_from_prev", False)
        continues_next = passage_group.get("continues_to_next", False)

        # --- [지문 ID 및 병합 처리] ---
        if is_continued and last_passage_id:
            # 이전 페이지에서 이어지는 지문: 기존 ID 유지
            passage_id = last_passage_id
            if not category:
                category = last_category

            # 지문 내용 병합
            if content:
                if last_passage_content:
                    merged_content = last_passage_content + "\n\n[페이지 연결]\n\n" + content
                else:
                    merged_content = content
            else:
                merged_content = last_passage_content

            last_passage_content = merged_content
        else:
            # 새로운 지문
            current_passage_num += 1
            passage_id = f"P{current_passage_num:03d}"
            last_passage_id = passage_id
            last_category = category
            last_passage_content = content
            merged_content = content

        # 페이지 연결 상태
        if is_continued and continues_next:
            page_status = "중간"
        elif is_continued:
            page_status = "끝"
        elif continues_next:
            page_status = "시작"
        else:
            page_status = "단독"

        # --- [지문 데이터 추가] ---
        if content:  # 내용이 있는 경우만
            p_row = {
                "출처": pdf_name,
                "지문ID": passage_id,
                "영역": category,
                "지문내용": merged_content,
                "연결상태": page_status
            }
            passages_list.append(p_row)

        # --- [문항 데이터 추가] ---
        for q in questions:
            q_row = {
                "출처": pdf_name,
                "지문ID": passage_id,  # Foreign Key
                "문제번호": q.get("q_num", ""),
                "발문": q.get("q_stem", ""),
                "보기/자료": q.get("reference_box", ""),
                "선지1": q.get("choice_1", ""),
                "선지2": q.get("choice_2", ""),
                "선지3": q.get("choice_3", ""),
                "선지4": q.get("choice_4", ""),
                "선지5": q.get("choice_5", ""),
            }
            questions_list.append(q_row)

    return passages_list, questions_list


def flatten_exam_data(data: list[dict], pdf_name: str = "") -> list[dict]:
    """
    계층형 JSON 데이터를 평탄화 (단일 시트용, 기존 호환)
    """
    flattened = []

    current_passage_id_num = 0
    last_passage_id = ""
    last_category = ""
    last_passage_content = ""

    for passage_group in data:
        category = passage_group.get("category", "")
        passage_content = passage_group.get("passage_content", "")
        questions = passage_group.get("related_questions", [])
        is_continued = passage_group.get("is_continued_from_prev", False)
        continues_next = passage_group.get("continues_to_next", False)

        if is_continued and last_passage_id:
            passage_id = last_passage_id
            if not category:
                category = last_category
            if passage_content:
                if last_passage_content:
                    merged_content = last_passage_content + "\n\n[페이지 연결]\n\n" + passage_content
                else:
                    merged_content = passage_content
            else:
                merged_content = last_passage_content
            last_passage_content = merged_content
            display_content = merged_content
        else:
            current_passage_id_num += 1
            passage_id = f"지문_{current_passage_id_num:02d}"
            last_passage_id = passage_id
            last_category = category
            last_passage_content = passage_content
            display_content = passage_content

        if is_continued and continues_next:
            page_status = "중간"
        elif is_continued:
            page_status = "끝"
        elif continues_next:
            page_status = "시작"
        else:
            page_status = "단독"

        if not questions and passage_content:
            row = {
                "출처": pdf_name,
                "지문ID": passage_id,
                "영역": category,
                "지문내용": display_content,
                "페이지연결": page_status,
                "문제번호": "",
                "발문": "",
                "보기/자료": "",
                "선지1": "", "선지2": "", "선지3": "", "선지4": "", "선지5": "",
            }
            flattened.append(row)

        for question in questions:
            row = {
                "출처": pdf_name,
                "지문ID": passage_id,
                "영역": category,
                "지문내용": display_content,
                "페이지연결": page_status,
                "문제번호": question.get("q_num", ""),
                "발문": question.get("q_stem", ""),
                "보기/자료": question.get("reference_box", ""),
                "선지1": question.get("choice_1", ""),
                "선지2": question.get("choice_2", ""),
                "선지3": question.get("choice_3", ""),
                "선지4": question.get("choice_4", ""),
                "선지5": question.get("choice_5", ""),
            }
            flattened.append(row)

    return flattened


def create_dataframe(flattened_data: list[dict]) -> pd.DataFrame:
    """평탄화된 데이터로 DataFrame 생성"""
    columns = [
        "출처", "지문ID", "영역", "지문내용", "페이지연결",
        "문제번호", "발문", "보기/자료",
        "선지1", "선지2", "선지3", "선지4", "선지5",
    ]

    if not flattened_data:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(flattened_data, columns=columns)
    return df


def save_to_excel_relational(passages: list[dict], questions: list[dict], output_path: str) -> str:
    """
    지문/문항 분리된 관계형 엑셀 파일 저장 (2개 시트)
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # DataFrame 생성
    passage_columns = ["출처", "지문ID", "영역", "지문내용", "연결상태"]
    question_columns = ["출처", "지문ID", "문제번호", "발문", "보기/자료",
                        "선지1", "선지2", "선지3", "선지4", "선지5"]

    df_passages = pd.DataFrame(passages, columns=passage_columns) if passages else pd.DataFrame(columns=passage_columns)
    df_questions = pd.DataFrame(questions, columns=question_columns) if questions else pd.DataFrame(columns=question_columns)

    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        # 지문 시트
        df_passages.to_excel(writer, index=False, sheet_name='지문_DB')
        ws_p = writer.sheets['지문_DB']
        ws_p.column_dimensions['A'].width = 20
        ws_p.column_dimensions['B'].width = 12
        ws_p.column_dimensions['C'].width = 15
        ws_p.column_dimensions['D'].width = 100
        ws_p.column_dimensions['E'].width = 10

        # 문항 시트
        df_questions.to_excel(writer, index=False, sheet_name='문항_DB')
        ws_q = writer.sheets['문항_DB']
        ws_q.column_dimensions['A'].width = 20
        ws_q.column_dimensions['B'].width = 12
        ws_q.column_dimensions['C'].width = 10
        ws_q.column_dimensions['D'].width = 60
        ws_q.column_dimensions['E'].width = 50
        for col in ['F', 'G', 'H', 'I', 'J']:
            ws_q.column_dimensions[col].width = 40

    print(f"[SAVE] 관계형 엑셀 파일 저장 완료: {path}")
    print(f"   - 지문_DB: {len(df_passages)}행")
    print(f"   - 문항_DB: {len(df_questions)}행")
    return str(path)


def save_to_excel(df: pd.DataFrame, output_path: str) -> str:
    """DataFrame을 엑셀 파일로 저장 (단일 시트)"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='시험문항DB')

        worksheet = writer.sheets['시험문항DB']
        column_widths = {
            'A': 20, 'B': 10, 'C': 15, 'D': 80, 'E': 10,
            'F': 10, 'G': 50, 'H': 50,
            'I': 40, 'J': 40, 'K': 40, 'L': 40, 'M': 40,
        }
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width

    print(f"[SAVE] 엑셀 파일 저장 완료: {path}")
    return str(path)


def process_logs_to_excel(log_path: str, output_path: str, pdf_name: str = "", relational: bool = True) -> str:
    """
    JSONL 로그 파일을 엑셀로 변환

    Args:
        log_path: 로그 파일 경로
        output_path: 출력 엑셀 파일 경로
        pdf_name: PDF 파일명 (필터링용)
        relational: True면 지문/문항 분리 시트, False면 단일 시트

    Returns:
        저장된 파일 경로
    """
    print("[INFO] 로그 파일 로드 중...")
    logs = load_jsonl_log(log_path)

    if pdf_name:
        logs = [log for log in logs if log.get("pdf_name") == pdf_name]

    print(f"[OK] {len(logs)}개 페이지 로그 로드 완료")

    success_logs = [log for log in logs if log.get("status") == "success"]
    failed_logs = [log for log in logs if log.get("status") != "success"]

    print(f"   - 성공: {len(success_logs)}개 페이지")
    print(f"   - 실패: {len(failed_logs)}개 페이지")

    if failed_logs:
        print("   [WARN] 실패한 페이지:")
        for log in failed_logs:
            print(f"      - {log.get('pdf_name')} 페이지 {log.get('page_num')}: {log.get('error', 'Unknown')}")

    print("[PROC] 페이지 데이터 병합 중...")
    merged_data = merge_page_data(success_logs)
    print(f"[OK] {len(merged_data)}개 지문/문항 그룹 병합 완료")

    if relational:
        # 관계형 분리 저장
        print("[PROC] 지문/문항 분리 중...")
        passages, questions = split_exam_data(merged_data, pdf_name)
        print(f"[OK] 지문 {len(passages)}개, 문항 {len(questions)}개 추출")
        saved_path = save_to_excel_relational(passages, questions, output_path)
    else:
        # 단일 시트 저장
        print("[PROC] 데이터 평탄화 및 지문 연결 중...")
        flattened = flatten_exam_data(merged_data, pdf_name)
        print(f"[OK] 총 {len(flattened)}개 행 변환 완료")
        df = create_dataframe(flattened)
        saved_path = save_to_excel(df, output_path)

    return saved_path


def process_to_excel(data: list[dict], output_path: str, pdf_name: str = "") -> str:
    """JSON 데이터를 엑셀 파일로 변환"""
    print("[PROC] 데이터 평탄화 중...")
    flattened = flatten_exam_data(data, pdf_name)
    print(f"[OK] 총 {len(flattened)}개 행 변환 완료")

    print("[PROC] DataFrame 생성 중...")
    df = create_dataframe(flattened)

    print("[SAVE] 엑셀 파일 저장 중...")
    saved_path = save_to_excel(df, output_path)

    return saved_path


def preview_data(data: list[dict], max_items: int = 3) -> None:
    """추출된 데이터 미리보기 (디버깅용)"""
    print("\n" + "=" * 60)
    print("[INFO] 추출 데이터 미리보기")
    print("=" * 60)

    for i, passage_group in enumerate(data[:max_items]):
        print(f"\n[지문 그룹 {i + 1}]")
        print(f"  영역: {passage_group.get('category', 'N/A')}")

        content = passage_group.get('passage_content', '')
        if content:
            preview = content[:100] + "..." if len(content) > 100 else content
            print(f"  지문 미리보기: {preview}")

        questions = passage_group.get('related_questions', [])
        print(f"  문항 수: {len(questions)}개")

        for q in questions[:2]:
            q_stem = q.get('q_stem', '')
            print(f"    - {q.get('q_num', '?')}번: {q_stem[:50]}...")

    if len(data) > max_items:
        print(f"\n... 외 {len(data) - max_items}개 지문 그룹")

    print("=" * 60 + "\n")


def get_processing_summary(log_path: str) -> dict:
    """처리 현황 요약 반환"""
    logs = load_jsonl_log(log_path)

    summary = {
        "total_pages": len(logs),
        "success": 0,
        "failed": 0,
        "by_pdf": {}
    }

    for log in logs:
        pdf_name = log.get("pdf_name", "unknown")
        status = log.get("status", "unknown")

        if pdf_name not in summary["by_pdf"]:
            summary["by_pdf"][pdf_name] = {"success": 0, "failed": 0}

        if status == "success":
            summary["success"] += 1
            summary["by_pdf"][pdf_name]["success"] += 1
        else:
            summary["failed"] += 1
            summary["by_pdf"][pdf_name]["failed"] += 1

    return summary
