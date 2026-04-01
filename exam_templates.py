"""
exam_templates.py
시험지 양식 관리 모듈 — Firebase Firestore 기반 CRUD
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from firebase_config import get_firestore_client

COLLECTION = "exam_templates"

# =============================================================================
# 기본 양식 정의
# =============================================================================

DEFAULT_TEMPLATES = [
    {
        "template_id": "default_school",
        "name": "내신형 기본",
        "description": "학교 내신 시험지 공식 양식 (1단, A4)",
        "is_default": True,
        "layout": {
            "columns": 1,
            "page_size": "A4",
            "margin_top": 15,
            "margin_bottom": 12,
            "margin_left": 18,
            "margin_right": 18,
            "gutter": 0,
        },
        "header": {
            "style": "school",
            "line_1": "{school_name}",
            "line_2": "{exam_name}",
            "line_3": "과목: {subject}  |  학년: {grade}  |  시험일: {exam_date}  |  시간: {time_limit}",
            "show_border": True,
        },
        "footer": {
            "show_page_number": True,
            "custom_text": "",
        },
        "fonts": {
            "passage_size": 10.5,
            "passage_leading": 16,
            "stem_size": 11,
            "stem_leading": 17,
            "choice_size": 10.5,
            "choice_leading": 15,
            "box_title_size": 10.5,
            "box_body_size": 10,
        },
        "spacing": {
            "before_question": 14,
            "after_question": 4,
            "choice_gap": 2,
            "passage_indent": 12,
        },
        "exam_info": {
            "school_name": "",
            "exam_name": "",
            "subject": "국어",
            "grade": "",
            "exam_date": "",
            "time_limit": "",
        },
    },
    {
        "template_id": "default_suneung",
        "name": "수능형 기본",
        "description": "수능/모의고사 스타일 양식 (2단)",
        "is_default": True,
        "layout": {
            "columns": 2,
            "page_size": "A4",
            "margin_top": 12,
            "margin_bottom": 10,
            "margin_left": 10,
            "margin_right": 10,
            "gutter": 6,
        },
        "header": {
            "style": "suneung",
            "line_1": "{title}",
            "line_2": "{subject}",
            "line_3": "{session} | {form_type}",
            "show_border": True,
        },
        "footer": {
            "show_page_number": True,
            "custom_text": "이 문제지에 관한 저작권은 한국교육과정평가원에 있습니다.",
        },
        "fonts": {
            "passage_size": 8,
            "passage_leading": 11.5,
            "stem_size": 8.5,
            "stem_leading": 12,
            "choice_size": 8,
            "choice_leading": 11,
            "box_title_size": 8,
            "box_body_size": 7.5,
        },
        "spacing": {
            "before_question": 8,
            "after_question": 3,
            "choice_gap": 1,
            "passage_indent": 8,
        },
        "exam_info": {
            "title": "2026학년도 대학수학능력시험 문제지",
            "subject": "국어 영역",
            "session": "제1교시",
            "form_type": "홀수형",
        },
    },
    {
        "template_id": "default_minimal",
        "name": "미니멀",
        "description": "깔끔한 1단 양식, 헤더 최소화",
        "is_default": True,
        "layout": {
            "columns": 1,
            "page_size": "A4",
            "margin_top": 15,
            "margin_bottom": 12,
            "margin_left": 20,
            "margin_right": 20,
            "gutter": 0,
        },
        "header": {
            "style": "minimal",
            "line_1": "{exam_name}",
            "line_2": "",
            "line_3": "{subject}  {grade}",
            "show_border": False,
        },
        "footer": {
            "show_page_number": True,
            "custom_text": "",
        },
        "fonts": {
            "passage_size": 10.5,
            "passage_leading": 16,
            "stem_size": 11,
            "stem_leading": 16,
            "choice_size": 10.5,
            "choice_leading": 15,
            "box_title_size": 10,
            "box_body_size": 10,
        },
        "spacing": {
            "before_question": 14,
            "after_question": 4,
            "choice_gap": 2,
            "passage_indent": 12,
        },
        "exam_info": {
            "exam_name": "",
            "subject": "국어",
            "grade": "",
        },
    },
]


# =============================================================================
# CRUD 함수
# =============================================================================

def get_all_templates() -> list:
    """모든 양식 조회"""
    db = get_firestore_client()
    docs = db.collection(COLLECTION).stream()
    templates = [doc.to_dict() for doc in docs]
    if not templates:
        seed_default_templates()
        docs = db.collection(COLLECTION).stream()
        templates = [doc.to_dict() for doc in docs]
    return templates


def get_template(template_id: str) -> Optional[dict]:
    """양식 1개 조회"""
    db = get_firestore_client()
    doc = db.collection(COLLECTION).document(template_id).get()
    return doc.to_dict() if doc.exists else None


def save_template(template: dict) -> str:
    """양식 저장 (생성 또는 업데이트)"""
    db = get_firestore_client()
    if not template.get("template_id"):
        template["template_id"] = uuid.uuid4().hex[:8]
    template["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not template.get("created_at"):
        template["created_at"] = template["updated_at"]
    db.collection(COLLECTION).document(template["template_id"]).set(template)
    return template["template_id"]


def delete_template(template_id: str) -> bool:
    """양식 삭제 (기본 양식은 삭제 불가)"""
    template = get_template(template_id)
    if template and template.get("is_default"):
        return False
    db = get_firestore_client()
    db.collection(COLLECTION).document(template_id).delete()
    return True


def duplicate_template(template_id: str, new_name: str = None) -> str:
    """양식 복제"""
    original = get_template(template_id)
    if not original:
        return ""
    new_template = {**original}
    new_template["template_id"] = uuid.uuid4().hex[:8]
    new_template["name"] = new_name or f"{original['name']} (복사본)"
    new_template["is_default"] = False
    new_template["created_at"] = ""
    return save_template(new_template)


def seed_default_templates():
    """기본 양식 시딩"""
    db = get_firestore_client()
    for tmpl in DEFAULT_TEMPLATES:
        tmpl["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tmpl["updated_at"] = tmpl["created_at"]
        db.collection(COLLECTION).document(tmpl["template_id"]).set(tmpl)


# =============================================================================
# 양식 → ExamPaperConfig 변환
# =============================================================================

def template_to_config(template: dict, overrides: dict = None) -> dict:
    """
    양식 데이터를 PDF 생성에 필요한 설정 dict로 변환.
    overrides로 exam_info 필드를 덮어쓸 수 있음.
    """
    layout = template.get("layout", {})
    header = template.get("header", {})
    fonts = template.get("fonts", {})
    spacing = template.get("spacing", {})
    exam_info = {**template.get("exam_info", {})}

    if overrides:
        exam_info.update({k: v for k, v in overrides.items() if v})

    columns = layout.get("columns", 1)
    header_style = header.get("style", "school")

    if columns == 2 or header_style == "suneung":
        layout_type = "suneung"
    else:
        layout_type = "school"

    return {
        "layout_type": layout_type,
        "columns": columns,
        "margins": {
            "top": layout.get("margin_top", 12),
            "bottom": layout.get("margin_bottom", 10),
            "left": layout.get("margin_left", 15),
            "right": layout.get("margin_right", 15),
            "gutter": layout.get("gutter", 6),
        },
        "header": header,
        "footer": template.get("footer", {}),
        "fonts": fonts,
        "spacing": spacing,
        "exam_info": exam_info,
        # ExamPaperConfig 호환 필드
        "title": exam_info.get("title", ""),
        "subject": exam_info.get("subject", "국어"),
        "session": exam_info.get("session", ""),
        "form_type": exam_info.get("form_type", ""),
        "school_name": exam_info.get("school_name", ""),
        "exam_name": exam_info.get("exam_name", ""),
        "grade": exam_info.get("grade", ""),
        "exam_date": exam_info.get("exam_date", ""),
        "time_limit": exam_info.get("time_limit", ""),
    }
