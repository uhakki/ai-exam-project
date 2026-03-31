"""
pdf_processor.py
PDF를 페이지별 이미지로 분할하는 모듈
"""

import fitz  # pymupdf
from pathlib import Path
from typing import Generator
import shutil


def pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 200
) -> list[Path]:
    """
    PDF 파일을 페이지별 PNG 이미지로 변환

    Args:
        pdf_path: PDF 파일 경로
        output_dir: 이미지 저장 디렉토리
        dpi: 이미지 해상도 (기본값 200)

    Returns:
        생성된 이미지 파일 경로 리스트
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # PDF 열기
    doc = fitz.open(str(pdf_path))
    image_paths = []

    # print 제거 (Windows cp949 인코딩 문제 방지)

    # 해상도 설정 (DPI를 zoom factor로 변환)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 페이지를 이미지로 렌더링
        pix = page.get_pixmap(matrix=matrix)

        # 파일명 생성: 원본파일명_page_001.png
        image_filename = f"{pdf_path.stem}_page_{page_num + 1:03d}.png"
        image_path = output_dir / image_filename

        # PNG로 저장
        pix.save(str(image_path))
        image_paths.append(image_path)

    doc.close()
    # print 제거 (Windows cp949 인코딩 문제 방지)

    return image_paths


def get_page_count(pdf_path: str) -> int:
    """PDF 총 페이지 수 반환"""
    doc = fitz.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count


def cleanup_temp_images(temp_dir: str) -> None:
    """임시 이미지 폴더 정리"""
    temp_path = Path(temp_dir)
    if temp_path.exists():
        shutil.rmtree(temp_path)
        print(f"[DEL] 임시 폴더 삭제: {temp_dir}")


def get_existing_images(temp_dir: str, pdf_stem: str) -> list[Path]:
    """
    이미 생성된 이미지 파일 목록 반환 (재시작 시 사용)

    Args:
        temp_dir: 임시 이미지 폴더
        pdf_stem: PDF 파일명 (확장자 제외)

    Returns:
        정렬된 이미지 파일 경로 리스트
    """
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return []

    pattern = f"{pdf_stem}_page_*.png"
    images = sorted(temp_path.glob(pattern))
    return images
