"""
main.py
안정형 국어 모의고사 PDF to Excel DB 변환기
- 멀티스레딩(병렬 처리) 적용으로 속도 대폭 개선
- 페이지별 분할 처리
- 체크포인트 기반 이어하기
- 강력한 오류 제어
"""

import os
import sys
import threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdf_processor import pdf_to_images, cleanup_temp_images, get_page_count
from extractor import configure_api, extract_page_data_with_fallback
from parser import (
    save_to_jsonl,
    get_processed_pages,
    process_logs_to_excel,
    get_processing_summary,
    load_jsonl_log
)

# ============================================================
# 설정값
# ============================================================
# 동시에 처리할 페이지 수 (API Rate Limit 고려)
# - Pro 모델: 2~3 권장 (무거워서 제한 걸리기 쉬움)
# - Flash 모델: 5~10 가능
MAX_WORKERS = 3

# 파일 저장 시 스레드 안전성을 위한 Lock
_file_lock = threading.Lock()


def load_environment() -> str:
    """환경 변수 로드 및 API 키 반환"""
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ERR] 오류: GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 GOOGLE_API_KEY=your_api_key 형식으로 추가하세요.")
        sys.exit(1)

    return api_key


def get_pdf_files(input_dir: str) -> list[Path]:
    """입력 디렉토리에서 PDF 파일 목록 조회"""
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"[ERR] 오류: 입력 디렉토리가 존재하지 않습니다: {input_dir}")
        sys.exit(1)

    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        print(f"[ERR] 오류: {input_dir} 폴더에 PDF 파일이 없습니다.")
        print("   PDF 파일을 input/ 폴더에 넣어주세요.")
        sys.exit(1)

    return pdf_files


def generate_output_filename(pdf_path: Path, output_dir: str) -> str:
    """출력 파일명 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{pdf_path.stem}_{timestamp}.xlsx"
    return str(Path(output_dir) / output_name)


def process_page_task(args: tuple) -> dict:
    """
    병렬 처리를 위한 단일 페이지 처리 함수

    Args:
        args: (image_path, page_num, pdf_name, log_path) 튜플

    Returns:
        처리 결과 딕셔너리
    """
    image_path, page_num, pdf_name, log_path = args

    # 페이지 처리
    result = extract_page_data_with_fallback(
        image_path=image_path,
        page_num=page_num,
        pdf_name=pdf_name,
        max_retries=3
    )

    # 결과 저장 (스레드 안전하게)
    with _file_lock:
        save_to_jsonl(result, log_path)

    return result


def process_single_pdf(
    pdf_path: Path,
    api_key: str,
    temp_dir: str,
    log_dir: str,
    output_dir: str
) -> dict:
    """
    단일 PDF 파일 처리 (병렬 처리 적용)

    Args:
        pdf_path: PDF 파일 경로
        api_key: Google API 키
        temp_dir: 임시 이미지 폴더
        log_dir: 로그 폴더
        output_dir: 출력 폴더

    Returns:
        처리 결과 딕셔너리
    """
    pdf_name = pdf_path.name
    log_path = str(Path(log_dir) / f"{pdf_path.stem}_log.jsonl")

    print(f"\n{'=' * 60}")
    print(f"[PROC] 처리 중: {pdf_name} (병렬 처리 모드, Workers: {MAX_WORKERS})")
    print(f"{'=' * 60}")

    result = {
        "pdf": pdf_name,
        "total_pages": 0,
        "processed_pages": 0,
        "success_pages": 0,
        "failed_pages": 0,
        "skipped_pages": 0,
        "excel_path": None,
        "status": "processing"
    }

    try:
        # 1. API 설정
        configure_api(api_key)

        # 2. PDF 페이지 수 확인
        total_pages = get_page_count(str(pdf_path))
        result["total_pages"] = total_pages
        print(f"[INFO] 총 {total_pages} 페이지")

        # 3. 이미 처리된 페이지 확인 (체크포인트)
        processed_pages = get_processed_pages(log_path, pdf_name)
        if processed_pages:
            print(f"[OK] 이전 진행 상황 발견: {len(processed_pages)}개 페이지 스킵")
            result["skipped_pages"] = len(processed_pages)

        # 4. PDF를 페이지별 이미지로 변환
        pdf_temp_dir = str(Path(temp_dir) / pdf_path.stem)
        image_paths = pdf_to_images(str(pdf_path), pdf_temp_dir)

        # 5. 처리할 작업 목록 생성 (이미 처리된 페이지 제외)
        tasks = []
        for page_num, image_path in enumerate(image_paths, start=1):
            if page_num not in processed_pages:
                tasks.append((image_path, page_num, pdf_name, log_path))

        # 6. 병렬 처리 실행
        if tasks:
            print(f"\n[PROC] {len(tasks)}개 페이지 병렬 처리 시작...")

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # 작업 제출
                future_to_page = {
                    executor.submit(process_page_task, task): task[1]
                    for task in tasks
                }

                # 진행률 표시와 함께 결과 수집
                with tqdm(total=len(tasks), desc="진행률", unit="page") as pbar:
                    for future in as_completed(future_to_page):
                        page_num = future_to_page[future]
                        try:
                            page_result = future.result()

                            result["processed_pages"] += 1
                            if page_result["status"] == "success":
                                result["success_pages"] += 1
                                pbar.set_postfix({"최근": f"[OK] P{page_num}"})
                            else:
                                result["failed_pages"] += 1
                                pbar.set_postfix({"최근": f"[ERR] P{page_num}"})

                        except Exception as e:
                            print(f"\n[ERR] 페이지 {page_num} 스레드 오류: {e}")
                            result["failed_pages"] += 1

                        pbar.update(1)
        else:
            print("[OK] 모든 페이지가 이미 처리되었습니다.")

        # 7. 최종 엑셀 생성
        print(f"\n[PROC] 엑셀 파일 생성 중...")
        output_path = generate_output_filename(pdf_path, output_dir)
        excel_path = process_logs_to_excel(log_path, output_path, pdf_name)

        result["excel_path"] = excel_path
        result["status"] = "completed"

        # 8. 임시 이미지 정리 (선택적)
        # cleanup_temp_images(pdf_temp_dir)

    except Exception as e:
        result["status"] = "error"
        result["error"] = f"{type(e).__name__}: {str(e)}"
        print(f"[ERR] 처리 중 오류 발생: {result['error']}")

        # 오류 발생해도 지금까지 처리된 데이터로 엑셀 생성 시도
        try:
            if Path(log_path).exists():
                print("[WARN] 부분 데이터로 엑셀 생성 시도...")
                output_path = generate_output_filename(pdf_path, output_dir)
                excel_path = process_logs_to_excel(log_path, output_path, pdf_name)
                result["excel_path"] = excel_path
                result["status"] = "partial"
        except Exception as excel_error:
            print(f"[ERR] 부분 엑셀 생성 실패: {excel_error}")

    return result


def print_summary(results: list[dict]) -> None:
    """처리 결과 요약 출력"""
    print("\n" + "=" * 60)
    print("[INFO] 처리 결과 요약")
    print("=" * 60)

    total_pages = sum(r.get("total_pages", 0) for r in results)
    success_pages = sum(r.get("success_pages", 0) for r in results)
    failed_pages = sum(r.get("failed_pages", 0) for r in results)
    skipped_pages = sum(r.get("skipped_pages", 0) for r in results)

    print(f"\n[INFO] 전체 통계:")
    print(f"   - 총 페이지: {total_pages}")
    print(f"   - 성공: {success_pages}")
    print(f"   - 실패: {failed_pages}")
    print(f"   - 스킵 (이전 처리): {skipped_pages}")

    print(f"\n[INFO] 파일별 결과:")
    for result in results:
        status_icon = {
            "completed": "[OK]",
            "partial": "[WARN]",
            "error": "[ERR]",
            "processing": "[PROC]"
        }.get(result.get("status", ""), "[?]")

        print(f"\n   {status_icon} {result['pdf']}")
        print(f"      - 상태: {result.get('status', 'unknown')}")
        print(f"      - 페이지: {result.get('success_pages', 0)}/{result.get('total_pages', 0)} 성공")

        if result.get("failed_pages", 0) > 0:
            print(f"      - 실패: {result['failed_pages']}개 페이지")

        if result.get("excel_path"):
            print(f"      - 출력: {result['excel_path']}")

        if result.get("error"):
            print(f"      - 오류: {result['error']}")


def main():
    """메인 실행 함수"""
    print("\n" + "=" * 60)
    print("[MAIN] 안정형 국어 모의고사 PDF to Excel DB 변환기")
    print("   (병렬 처리 / 자동 재시도 / 체크포인트)")
    print("=" * 60)

    # 경로 설정
    base_dir = Path(__file__).parent
    input_dir = str(base_dir / "input")
    output_dir = str(base_dir / "output")
    temp_dir = str(base_dir / "temp_images")
    log_dir = str(base_dir / "logs")

    # 디렉토리 생성
    for dir_path in [output_dir, temp_dir, log_dir]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # 환경 변수 로드
    print("\n[INFO] API 키 로드 중...")
    api_key = load_environment()
    print("[OK] API 키 로드 완료")

    # PDF 파일 목록 조회
    print(f"\n[INFO] 입력 폴더 스캔 중: {input_dir}")
    pdf_files = get_pdf_files(input_dir)
    print(f"[OK] {len(pdf_files)}개 PDF 파일 발견")

    for pdf_file in pdf_files:
        page_count = get_page_count(str(pdf_file))
        print(f"   - {pdf_file.name} ({page_count}페이지)")

    # 각 PDF 파일 처리
    results = []
    for pdf_path in pdf_files:
        result = process_single_pdf(
            pdf_path=pdf_path,
            api_key=api_key,
            temp_dir=temp_dir,
            log_dir=log_dir,
            output_dir=output_dir
        )
        results.append(result)

    # 결과 요약
    print_summary(results)

    print("\n[DONE] 작업 완료!")
    print("\n[TIP] 팁:")
    print("   - 실패한 페이지가 있다면 프로그램을 다시 실행하세요.")
    print("   - 이전에 성공한 페이지는 자동으로 스킵됩니다.")
    print(f"   - 병렬 처리 수: {MAX_WORKERS} (main.py의 MAX_WORKERS로 조절)")
    print("   - 로그 파일: logs/ 폴더")
    print("   - 결과 파일: output/ 폴더")


if __name__ == "__main__":
    main()
