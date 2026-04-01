"""
app.py
AI 시험지 관리 시스템 - Streamlit 웹 인터페이스
"""

import streamlit as st
import pandas as pd
import os
import json
import uuid
import time
import tempfile
from pathlib import Path
from datetime import datetime

# =============================================================================
# 페이지 설정
# =============================================================================
st.set_page_config(
    layout="wide",
    page_title="AI 시험지 관리 시스템",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 커스텀 CSS
# =============================================================================
st.markdown("""
<style>
/* ===== 전역 스타일 ===== */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
}

.main .block-container {
    padding: 2rem 3rem;
    max-width: 1400px;
}

/* ===== 사이드바 스타일 ===== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    width: 280px !important;
}

section[data-testid="stSidebar"] > div {
    padding: 1.5rem 1rem;
}

/* 사이드바 제목 */
.sidebar-title {
    color: #ffffff;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    padding: 0 0.5rem;
}

.sidebar-subtitle {
    color: #8892b0;
    font-size: 0.8rem;
    margin-bottom: 2rem;
    padding: 0 0.5rem;
}

/* 사이드바 메뉴 버튼 */
.menu-button {
    display: block;
    width: 100%;
    padding: 0.875rem 1rem;
    margin-bottom: 0.375rem;
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #ccd6f6;
    font-size: 0.9375rem;
    font-weight: 500;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
}

.menu-button:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
}

.menu-button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #ffffff;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

/* 사이드바 라디오 숨김 및 스타일링 */
section[data-testid="stSidebar"] .stRadio > div {
    flex-direction: column;
    gap: 0.375rem;
}

section[data-testid="stSidebar"] .stRadio > div > label {
    background: rgba(255, 255, 255, 0.06) !important;
    padding: 0.875rem 1rem !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    font-size: 0.9375rem !important;
    font-weight: 500 !important;
    border: none !important;
    margin: 0 !important;
    transition: all 0.2s ease !important;
}

section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(255, 255, 255, 0.12) !important;
    color: #ffffff !important;
}

section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
}

/* 라디오 라벨 내부 텍스트 색상 강제 적용 */
section[data-testid="stSidebar"] .stRadio > div > label span,
section[data-testid="stSidebar"] .stRadio > div > label p,
section[data-testid="stSidebar"] .stRadio > div > label div {
    color: inherit !important;
}

section[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none !important;
}

/* ===== 페이지 헤더 ===== */
.page-header {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 2px solid #e9ecef;
}

.page-title {
    color: #212529;
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
}

.page-desc {
    color: #6c757d;
    font-size: 0.9375rem;
    margin: 0;
}

/* ===== 메트릭 카드 ===== */
.stat-card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    text-align: center;
    transition: all 0.2s ease;
}

.stat-card:hover {
    border-color: #667eea;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
}

.stat-value {
    font-size: 2.25rem;
    font-weight: 700;
    color: #212529;
    line-height: 1.2;
}

.stat-label {
    font-size: 0.8125rem;
    color: #6c757d;
    margin-top: 0.375rem;
    font-weight: 500;
}

/* ===== 상태 뱃지 ===== */
.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-ready { background: #f1f3f4; color: #5f6368; }
.badge-processing { background: #e8f0fe; color: #1967d2; }
.badge-success { background: #e6f4ea; color: #1e8e3e; }
.badge-warning { background: #fef7e0; color: #f9ab00; }
.badge-error { background: #fce8e6; color: #d93025; }

/* ===== 콘텐츠 카드 ===== */
.content-card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.content-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e9ecef;
}

.content-card-title {
    font-size: 1rem;
    font-weight: 600;
    color: #212529;
    margin: 0;
}

/* ===== 터미널 스타일 로그 ===== */
.log-container {
    background: #1e1e1e;
    border-radius: 8px;
    overflow: hidden;
    margin-top: 1rem;
}

.log-header {
    background: #323233;
    padding: 0.625rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.log-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}
.log-dot.r { background: #ff5f57; }
.log-dot.y { background: #febc2e; }
.log-dot.g { background: #28c840; }

.log-title {
    color: #9ca3af;
    font-size: 0.75rem;
    margin-left: 0.5rem;
}

.log-body {
    padding: 1rem;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.8125rem;
    line-height: 1.6;
    color: #d4d4d4;
    max-height: 350px;
    overflow-y: auto;
    white-space: pre-wrap;
}

.log-body .time { color: #569cd6; }
.log-body .ok { color: #4ec9b0; }
.log-body .err { color: #f14c4c; }

/* ===== 데이터 테이블 ===== */
.data-tbl {
    width: 100%;
    border-collapse: collapse;
    background: #ffffff;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e9ecef;
}

.data-tbl th {
    background: #f8f9fa;
    padding: 0.875rem 1rem;
    text-align: left;
    font-size: 0.75rem;
    font-weight: 600;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #e9ecef;
}

.data-tbl td {
    padding: 0.875rem 1rem;
    font-size: 0.875rem;
    color: #212529;
    border-bottom: 1px solid #f1f3f4;
}

.data-tbl tr:last-child td { border-bottom: none; }
.data-tbl tr:hover td { background: #f8f9fa; }

/* ===== 폼 스타일 ===== */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 8px !important;
    border: 1px solid #dee2e6 !important;
    padding: 0.625rem 0.875rem !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
}

.stSelectbox > div > div {
    border-radius: 8px !important;
}

/* ===== 버튼 스타일 ===== */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    border: 1px solid #dee2e6 !important;
    color: #495057 !important;
}

.stButton > button[kind="secondary"]:hover {
    background: #f8f9fa !important;
    border-color: #adb5bd !important;
}

/* ===== 진행률 바 ===== */
.stProgress > div > div > div {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}

.stProgress > div > div {
    background: #e9ecef !important;
}

/* ===== Expander ===== */
.streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid #e9ecef !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: #212529 !important;
}

.streamlit-expanderHeader:hover {
    border-color: #667eea !important;
}

.streamlit-expanderContent {
    border: 1px solid #e9ecef !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    background: #ffffff !important;
}

/* ===== 탭 ===== */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: transparent;
}

.stTabs [data-baseweb="tab"] {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-weight: 500;
    color: #6c757d;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

/* ===== 알림 ===== */
.alert {
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}

.alert-info {
    background: #e8f4fd;
    border-left: 4px solid #0ea5e9;
    color: #0c4a6e;
}

.alert-success {
    background: #ecfdf5;
    border-left: 4px solid #10b981;
    color: #065f46;
}

.alert-warning {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    color: #92400e;
}

.alert-error {
    background: #fef2f2;
    border-left: 4px solid #ef4444;
    color: #991b1b;
}

/* ===== 숨김 ===== */
#MainMenu, footer, header { visibility: hidden; }

/* ===== 사이드바 항상 표시 (접기 버튼 숨김) ===== */
section[data-testid="stSidebar"] {
    min-width: 280px !important;
    width: 280px !important;
    transform: none !important;
}

/* 접기 버튼 숨김 */
[data-testid="collapsedControl"],
button[kind="headerNoPadding"] {
    display: none !important;
}

/* ===== 문항 카드 ===== */
.q-card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.q-num {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.875rem;
    margin-right: 0.75rem;
}

.q-category {
    color: #6c757d;
    font-size: 0.75rem;
}

.q-stem {
    color: #212529;
    font-size: 1rem;
    line-height: 1.6;
    margin: 0.75rem 0;
}

.q-ref {
    background: #f8f9fa;
    border-left: 3px solid #667eea;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
    border-radius: 0 6px 6px 0;
    font-size: 0.875rem;
    color: #495057;
}

.q-choice {
    padding: 0.5rem 0;
    border-bottom: 1px solid #f1f3f4;
    font-size: 0.9375rem;
    color: #212529;
}

.q-choice:last-child { border-bottom: none; }

.choice-num {
    color: #667eea;
    font-weight: 600;
    margin-right: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Backend 임포트 (Firebase 기반)
# =============================================================================
from backend import (
    task_extract_json, task_multimodal_verification, task_generate_excel,
    task_reextract_pages,
    request_stop, reset_data, update_json_manual, run_thread,
)
from storage_backend import (
    get_db, save_entry, get_item_by_id, read_log,
    load_json_data, download_to_bytes, upload_file, upload_bytes,
    get_temp_dir,
)

# =============================================================================
# 유틸리티 함수
# =============================================================================

import html as html_lib

STATUS_MAP = {
    "Ready": ("ready", "대기"),
    "Extracting": ("processing", "추출중"),
    "Verifying": ("processing", "검증중"),
    "Converting": ("processing", "변환중"),
    "Extracted": ("success", "추출완료"),
    "Modified": ("warning", "수정됨"),
    "Done": ("success", "완료"),
    "Stopped": ("warning", "중단"),
    "Stopping": ("warning", "중단중"),
    "Error": ("error", "오류"),
}

STATUS_KR = {k: v[1] for k, v in STATUS_MAP.items()}


def get_status_badge(status: str) -> str:
    style, label = STATUS_MAP.get(status, ("ready", status))
    return f'<span class="badge badge-{style}">{label}</span>'


def escape_html(text) -> str:
    """HTML 특수문자 이스케이프"""
    if not text:
        return ""
    return html_lib.escape(str(text))


def format_doc_label(item: dict) -> str:
    """문서 선택 드롭다운용 통합 라벨 생성.
    예: '2024년 4월 고3 국어 모의고사 [추출완료]'
    """
    parts = []
    year = item.get("year", "") or ""
    month = item.get("month", "") or ""
    semester = item.get("semester", "") or ""
    grade = item.get("grade", "") or ""
    subject = item.get("subject", "") or ""
    exam_type = item.get("exam_type", "") or ""
    school = item.get("school", "") or ""
    status = item.get("status", "Ready")

    if year:
        parts.append(f"{year}년")
    if month:
        parts.append(f"{month}월")
    elif semester:
        parts.append(semester)
    if grade:
        parts.append(grade)
    if subject:
        parts.append(subject)
    if exam_type:
        parts.append(exam_type)
    if school:
        parts.append(school)

    label = " ".join(parts) if parts else item.get("filename", item.get("file_id", "문서"))
    status_label = STATUS_KR.get(status, status)
    return f"{label} [{status_label}]"


def get_doc_options(db: list, status_filter: list = None) -> dict:
    """DB 목록에서 {label: file_id} 딕셔너리 생성."""
    if status_filter:
        items = [d for d in db if d.get("status") in status_filter]
    else:
        items = db
    return {format_doc_label(item): item["file_id"] for item in items}


def load_json_cached(file_id: str) -> dict:
    """JSON 데이터를 세션 상태에 캐시하여 로드."""
    cache_key = f"_json_cache_{file_id}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = load_json_data(file_id)
    return st.session_state[cache_key]


def invalidate_json_cache(file_id: str):
    """캐시된 JSON 데이터 무효화."""
    cache_key = f"_json_cache_{file_id}"
    if cache_key in st.session_state:
        del st.session_state[cache_key]


def render_log(content: str, title: str = "처리 로그") -> str:
    formatted = content.replace("[", '<span class="time">[').replace("]", "]</span>")
    return f'''
    <div class="log-container">
        <div class="log-header">
            <span class="log-dot r"></span>
            <span class="log-dot y"></span>
            <span class="log-dot g"></span>
            <span class="log-title">{title}</span>
        </div>
        <div class="log-body">{formatted if formatted.strip() else "로그 없음"}</div>
    </div>
    '''


def render_stat_card(value: str, label: str) -> str:
    return f'''
    <div class="stat-card">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    '''


# =============================================================================
# 세션 상태 조기 초기화 (탭 진입 순서 무관하게 안전)
# =============================================================================
if 'exam_selected_questions' not in st.session_state:
    st.session_state.exam_selected_questions = []
if 'exam_passages_cache' not in st.session_state:
    st.session_state.exam_passages_cache = {}
if 'exam_info' not in st.session_state:
    st.session_state.exam_info = {
        'layout_type': '수능형',
        'title': '2026학년도 대학수학능력시험 문제지',
        'subject': '국어 영역',
        'session': '제1교시',
        'form_type': '홀수형',
        'school_name': '',
        'exam_name': '',
        'grade': '',
        'date': '',
        'time_limit': ''
    }


# =============================================================================
# 사이드바
# =============================================================================
with st.sidebar:
    st.markdown('<div class="sidebar-title">AI 시험지 관리</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">문서 자동 추출 시스템</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    menu_items = {
        "대시보드": "대시보드",
        "파일 업로드": "파일 업로드",
        "데이터 처리": "데이터 처리",
        "데이터 편집": "데이터 편집",
        "문서 뷰어": "문서 뷰어",
        "시험지구성": "시험지구성",
        "문제은행": "문제은행"
    }

    selected = st.radio(
        "메뉴",
        list(menu_items.keys()),
        label_visibility="collapsed"
    )


# =============================================================================
# 1. 대시보드
# =============================================================================
if selected == "대시보드":
    st.markdown('''
    <div class="page-header">
        <div class="page-title">대시보드</div>
        <div class="page-desc">문서 처리 현황을 한눈에 확인하세요</div>
    </div>
    ''', unsafe_allow_html=True)

    db = get_db()

    if db:
        df = pd.DataFrame(db)

        total = len(df)
        ready = len(df[df['status'].isin(['Ready', 'Stopped'])])
        processing = len(df[df['status'].isin(['Extracting', 'Verifying', 'Converting', 'Stopping'])])
        completed = len(df[df['status'].isin(['Extracted', 'Modified', 'Done'])])
        error = len(df[df['status'] == 'Error'])

        # 통계 카드
        cols = st.columns(5)
        with cols[0]:
            st.markdown(render_stat_card(str(total), "전체 문서"), unsafe_allow_html=True)
        with cols[1]:
            st.markdown(render_stat_card(str(ready), "대기/중단"), unsafe_allow_html=True)
        with cols[2]:
            st.markdown(render_stat_card(str(processing), "처리중"), unsafe_allow_html=True)
        with cols[3]:
            st.markdown(render_stat_card(str(completed), "완료"), unsafe_allow_html=True)
        with cols[4]:
            st.markdown(render_stat_card(str(error), "오류"), unsafe_allow_html=True)

        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

        # 계층 필터
        st.markdown("### 문서 필터")
        fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
        with fcol1:
            sl_options = ["전체"] + sorted(df['school_level'].dropna().unique().tolist()) if 'school_level' in df.columns else ["전체"]
            f_school_level = st.selectbox("학교급", sl_options, key="dash_sl")
        with fcol2:
            yr_options = ["전체"] + sorted(df['year'].dropna().unique().tolist(), reverse=True)
            f_year = st.selectbox("연도", yr_options, key="dash_yr")
        with fcol3:
            gr_options = ["전체"] + sorted(df['grade'].dropna().unique().tolist())
            f_grade = st.selectbox("학년", gr_options, key="dash_gr")
        with fcol4:
            sem_options = ["전체"] + sorted(df['semester'].dropna().unique().tolist())
            f_semester = st.selectbox("학기", sem_options, key="dash_sem")
        with fcol5:
            et_options = ["전체"] + sorted(df['exam_type'].dropna().unique().tolist())
            f_exam_type = st.selectbox("시험유형", et_options, key="dash_et")

        filtered_df = df.copy()
        if f_school_level != "전체" and 'school_level' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['school_level'] == f_school_level]
        if f_year != "전체":
            filtered_df = filtered_df[filtered_df['year'] == f_year]
        if f_grade != "전체":
            filtered_df = filtered_df[filtered_df['grade'] == f_grade]
        if f_semester != "전체":
            filtered_df = filtered_df[filtered_df['semester'] == f_semester]
        if f_exam_type != "전체":
            filtered_df = filtered_df[filtered_df['exam_type'] == f_exam_type]

        st.markdown(f"**{len(filtered_df)}**개 문서", unsafe_allow_html=True)

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        # 문서 목록
        st.markdown("### 문서 목록")

        recent = filtered_df.sort_values('last_updated', ascending=False)

        status_kr = STATUS_KR

        table_rows = []
        for _, row in recent.iterrows():
            year_val = row.get('year', '') or ''
            month_val = row.get('month', '') or ''
            semester_val = row.get('semester', '') or ''
            grade_val = row.get('grade', '') or ''
            subject_val = row.get('subject', '') or ''
            time_info = f"{month_val}월" if month_val else semester_val
            doc_info = f"{year_val} {time_info} {grade_val} {subject_val}".strip()
            if not doc_info:
                doc_info = row.get('filename', '-')

            exam_type_val = row.get('exam_type', '') or ''
            school_val = row.get('school', '') or ''
            exam_info = f"{exam_type_val} {school_val}".strip() if school_val else exam_type_val

            table_rows.append({
                "학교급": row.get('school_level', '') or '',
                "문서": doc_info,
                "학교": school_val,
                "시험유형": exam_info,
                "상태": status_kr.get(row.get('status', 'Ready'), row.get('status', '')),
                "진행률": int(row.get('progress', 0)),
                "업데이트": row.get('last_updated', '-'),
            })

        display_df = pd.DataFrame(table_rows)
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "학교급": st.column_config.TextColumn("학교급", width="small"),
                "문서": st.column_config.TextColumn("문서", width="medium"),
                "학교": st.column_config.TextColumn("학교", width="small"),
                "시험유형": st.column_config.TextColumn("시험유형", width="small"),
                "상태": st.column_config.TextColumn("상태", width="small"),
                "진행률": st.column_config.ProgressColumn("진행률", min_value=0, max_value=100, width="small"),
                "업데이트": st.column_config.TextColumn("업데이트", width="medium"),
            }
        )

    else:
        st.markdown('''
        <div class="alert alert-info">
            등록된 문서가 없습니다. 파일 업로드 메뉴에서 시험지를 등록해주세요.
        </div>
        ''', unsafe_allow_html=True)


# =============================================================================
# 2. 파일 업로드
# =============================================================================
elif selected == "파일 업로드":
    st.markdown('''
    <div class="page-header">
        <div class="page-title">파일 업로드</div>
        <div class="page-desc">PDF 또는 이미지 파일을 업로드하세요</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="content-card">', unsafe_allow_html=True)

    with st.form("upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "파일 선택",
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="PDF, PNG, JPG 형식 지원"
        )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        st.markdown("#### 문서 정보 (선택사항)")

        col1, col2, col3 = st.columns(3)

        with col1:
            year = st.text_input("연도", placeholder="예: 2025")
            subject = st.text_input("과목", placeholder="예: 국어")

        with col2:
            school_level = st.selectbox("학교급", ["", "중등", "고등"])
            exam_type = st.selectbox("시험 유형", ["", "모의고사", "수능", "중간고사", "기말고사", "기타"])
            grade = st.selectbox("학년", ["", "중1", "중2", "중3", "고1", "고2", "고3"])

        with col3:
            # 시험 유형에 따라 다른 필드 표시 (폼 내에서는 조건부 표시 제한이 있어 모두 표시)
            month = st.text_input("월 (모의고사/수능)", placeholder="예: 6")
            semester = st.selectbox("학기 (중간/기말)", ["", "1학기", "2학기"])

        # 중간/기말고사용 추가 필드
        col4, col5 = st.columns(2)
        with col4:
            school = st.text_input("학교명 (중간/기말)", placeholder="예: OO고등학교")
        with col5:
            author = st.text_input("출제자 (중간/기말)", placeholder="예: 홍길동")

        desc = st.text_area("메모", placeholder="추가 정보 입력 (선택)")

        auto_col1, auto_col2 = st.columns([1, 3])
        with auto_col1:
            st.session_state["auto_extract"] = st.checkbox("업로드 후 자동 추출", value=True, key="auto_extract_cb")

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("업로드", use_container_width=True, type="primary")

        if submitted:
            if not uploaded_file:
                st.error("파일을 선택해주세요.")
            else:
                file_id = str(uuid.uuid4())[:8]
                saved_filename = f"{file_id}_{uploaded_file.name}"

                # Firebase Storage에 업로드
                storage_path = f"inputs/{saved_filename}"
                file_bytes = uploaded_file.getbuffer()
                upload_bytes(bytes(file_bytes), storage_path)

                entry = {
                    "file_id": file_id,
                    "filename": uploaded_file.name,
                    "filepath": storage_path,
                    "subject": subject if subject else "",
                    "year": year if year else "",
                    "exam_type": exam_type if exam_type else "",
                    "grade": grade if grade else "",
                    "month": month if month else "",
                    "semester": semester if semester else "",
                    "school": school if school else "",
                    "school_level": school_level if school_level else "",
                    "author": author if author else "",
                    "desc": desc,
                    "status": "Ready",
                    "progress": 0,
                    "current_page": 0,
                    "total_pages": 0,
                    "ai_verified": False,
                    "error_msg": "",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                save_entry(entry)

                # 자동 추출 시작
                auto_extract = st.session_state.get("auto_extract", True)
                if auto_extract:
                    st.info(f"'{uploaded_file.name}' 업로드 완료! AI 추출을 자동 시작합니다...")
                    from backend import task_extract_json, run_thread
                    run_thread(task_extract_json, file_id)
                    st.success(f"추출이 시작되었습니다. 데이터 처리 메뉴에서 진행 상황을 확인하세요.")
                else:
                    st.success(f"'{uploaded_file.name}' 파일이 업로드되었습니다. 데이터 처리 메뉴에서 추출을 시작하세요.")

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 3. 데이터 처리
# =============================================================================
elif selected == "데이터 처리":
    st.markdown('''
    <div class="page-header">
        <div class="page-title">데이터 처리</div>
        <div class="page-desc">AI 추출, 검증, 변환 작업을 관리합니다</div>
    </div>
    ''', unsafe_allow_html=True)

    # 계층 필터
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        f_sl = st.selectbox("학교급", ["전체", "중등", "고등"], key="proc_sl")
    with fcol2:
        f_yr = st.text_input("연도", placeholder="예: 2025", key="proc_yr")
    with fcol3:
        f_gr = st.selectbox("학년", ["전체", "중1", "중2", "중3", "고1", "고2", "고3"], key="proc_gr")
    with fcol4:
        f_et = st.selectbox("시험유형", ["전체", "중간고사", "기말고사", "모의고사", "수능"], key="proc_et")

    # 상태 필터 (한글 표시, 내부값은 영문 유지)
    status_options = {
        "대기": "Ready",
        "추출중": "Extracting",
        "검증중": "Verifying",
        "변환중": "Converting",
        "추출완료": "Extracted",
        "수정됨": "Modified",
        "완료": "Done",
        "중단": "Stopped",
        "오류": "Error"
    }
    selected_status_kr = st.multiselect(
        "상태 필터",
        list(status_options.keys()),
        default=list(status_options.keys()),
        label_visibility="collapsed"
    )
    status_filter = [status_options[s] for s in selected_status_kr]

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    db = get_db()

    if not db:
        st.markdown('''
        <div class="alert alert-info">
            처리할 문서가 없습니다. 먼저 파일을 업로드해주세요.
        </div>
        ''', unsafe_allow_html=True)
    else:
        filtered = [item for item in db if item['status'] in status_filter]
        # 계층 필터 적용
        if f_sl != "전체":
            filtered = [item for item in filtered if item.get('school_level') == f_sl]
        if f_yr:
            filtered = [item for item in filtered if item.get('year') == f_yr]
        if f_gr != "전체":
            filtered = [item for item in filtered if item.get('grade') == f_gr]
        if f_et != "전체":
            filtered = [item for item in filtered if item.get('exam_type') == f_et]

        for item in reversed(filtered):
            status = item['status']
            file_id = item['file_id']
            progress = item.get('progress', 0)

            is_active = status in ['Extracting', 'Verifying', 'Converting', 'Stopping']

            title = format_doc_label(item)

            with st.expander(title, expanded=is_active):
                col_info, col_actions = st.columns([2, 1])

                with col_info:
                    st.markdown(f'''
                    <div style="margin-bottom:1rem;">
                        {get_status_badge(status)}
                        <span style="margin-left:1rem;color:#6c757d;font-size:0.875rem;">ID: {file_id}</span>
                    </div>
                    ''', unsafe_allow_html=True)

                    if status in ['Extracting', 'Converting', 'Verifying']:
                        st.progress(progress / 100)

                        page_info = ""
                        if item.get('current_page') and item.get('total_pages'):
                            page_info = f" | {item['current_page']}/{item['total_pages']} 페이지"

                        st.markdown(f'''
                        <p style="color:#6c757d;font-size:0.875rem;margin-top:0.5rem;">
                            진행률: {progress}%{page_info}
                        </p>
                        ''', unsafe_allow_html=True)

                    log_content = read_log(file_id)
                    st.markdown(render_log(log_content, f"로그: {file_id}"), unsafe_allow_html=True)

                    if item.get('error_msg'):
                        st.markdown(f'''
                        <div class="alert alert-error" style="margin-top:1rem;">
                            <strong>오류:</strong> {item['error_msg']}
                        </div>
                        ''', unsafe_allow_html=True)

                with col_actions:
                    st.markdown("#### 작업")

                    if status in ['Extracting', 'Verifying', 'Converting']:
                        if st.button("중단", key=f"stop_{file_id}", use_container_width=True):
                            request_stop(file_id)
                            st.rerun()

                    elif status == 'Stopping':
                        st.markdown('''
                        <div class="alert alert-warning">중단 처리중...</div>
                        ''', unsafe_allow_html=True)

                    else:
                        if status in ['Ready', 'Stopped', 'Error']:
                            model_choice = st.radio("AI 모델", ["flash (빠름)", "pro (고품질)"], horizontal=True, key=f"model_{file_id}")
                            model_type = "flash" if "flash" in model_choice else "pro"
                            btn_text = "추출 시작" if status == 'Ready' else "추출 재개"
                            if st.button(btn_text, key=f"ext_{file_id}", type="primary", use_container_width=True):
                                item_with_model = {**item, "model_type": model_type}
                                run_thread(task_extract_json, (file_id, item['filepath'], item_with_model))
                                st.rerun()

                        if status in ['Extracted', 'Modified', 'Done']:
                            st.markdown("<hr style='margin:1rem 0;border-color:#e9ecef;'>", unsafe_allow_html=True)

                            # 페이지 범위 입력 (검증/재추출 공용)
                            st.markdown("<p style='font-size:0.8rem;color:#495057;margin-bottom:0.25rem;'>페이지 범위</p>", unsafe_allow_html=True)
                            page_range_input = st.text_input(
                                "페이지 범위",
                                value="all",
                                key=f"page_range_{file_id}",
                                label_visibility="collapsed",
                                placeholder="예: all, 14, 1-5, 3,5,7"
                            )

                            # 검증 / 재추출 버튼
                            btn_col1, btn_col2 = st.columns(2)
                            with btn_col1:
                                verify_text = "재검증" if item.get('ai_verified') else "AI 검증"
                                if st.button(verify_text, key=f"verify_{file_id}", use_container_width=True):
                                    run_thread(task_multimodal_verification, (file_id, item['filepath'], page_range_input))
                                    st.rerun()
                            with btn_col2:
                                if st.button("페이지 재추출", key=f"reextract_{file_id}", use_container_width=True):
                                    if page_range_input.lower() == "all":
                                        st.warning("재추출은 특정 페이지만 가능합니다")
                                    else:
                                        run_thread(task_reextract_pages, (file_id, item['filepath'], page_range_input))
                                        st.rerun()

                            if item.get('ai_verified'):
                                st.markdown('<p style="color:#1e8e3e;font-size:0.75rem;margin-top:0.5rem;">검증 완료</p>', unsafe_allow_html=True)

                            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

                            if st.button("엑셀 생성", key=f"excel_{file_id}", use_container_width=True):
                                run_thread(task_generate_excel, (file_id,))
                                st.rerun()

                            # 엑셀 다운로드 버튼 (status가 Done이고 excel_path가 있을 때)
                            if status == 'Done' and item.get('excel_path'):
                                st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
                                try:
                                    excel_bytes = download_to_bytes(item['excel_path'])
                                    st.download_button(
                                        "엑셀 다운로드",
                                        excel_bytes,
                                        file_name=f"{item.get('subject', 'output')}_{item.get('year', '')}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True,
                                        key=f"download_{file_id}"
                                    )
                                except Exception:
                                    st.warning("엑셀 파일을 다운로드할 수 없습니다.")

                        st.markdown("<hr style='margin:1rem 0;border-color:#e9ecef;'>", unsafe_allow_html=True)

                        if st.button("초기화", key=f"reset_{file_id}", use_container_width=True):
                            reset_data(file_id)
                            st.rerun()



# =============================================================================
# 4. 데이터 편집
# =============================================================================
elif selected == "데이터 편집":
    st.markdown('''
    <div class="page-header">
        <div class="page-title">데이터 편집</div>
        <div class="page-desc">추출된 데이터를 검토하고 수정합니다</div>
    </div>
    ''', unsafe_allow_html=True)

    db = get_db()
    editable = [item for item in db if item['status'] in ['Extracted', 'Modified', 'Done']]

    if not editable:
        st.markdown('''
        <div class="alert alert-info">
            편집 가능한 문서가 없습니다. 먼저 추출을 완료해주세요.
        </div>
        ''', unsafe_allow_html=True)
    else:
        options = get_doc_options(editable)
        selected_doc = st.selectbox("문서 선택", list(options.keys()))
        file_id = options[selected_doc]

        data = load_json_cached(file_id)

        if not data:
            st.error(f"데이터를 불러올 수 없습니다. (ID: {file_id})")
        else:
            tab1, tab2, tab3 = st.tabs(["문항", "지문", "메타정보"])

            with tab1:
                questions = data.get("questions", [])

                # 세션에서 수정된 데이터가 있으면 사용
                if f"questions_data_{file_id}" in st.session_state:
                    questions = st.session_state[f"questions_data_{file_id}"]

                if questions:
                    questions_df = pd.DataFrame(questions)

                    # 행 편집 모드 토글
                    show_row_edit = st.checkbox("행 편집 모드", key=f"row_edit_mode_{file_id}")

                    if show_row_edit:
                        st.markdown("""
                        <div style="background:#f8f9fa;padding:0.75rem 1rem;border-radius:8px;margin-bottom:0.5rem;">
                            <span style="color:#495057;font-size:0.875rem;">행 번호 입력 후 원하는 작업을 선택하세요</span>
                        </div>
                        """, unsafe_allow_html=True)
                        edit_col1, edit_col2, edit_col3, edit_col4 = st.columns([1.5, 1, 1, 1])
                        with edit_col1:
                            target_row = st.number_input(
                                "행 번호",
                                min_value=1,
                                max_value=len(questions),
                                value=1,
                                key=f"target_row_{file_id}",
                                label_visibility="collapsed"
                            )
                        with edit_col2:
                            if st.button("위에 삽입", key=f"insert_above_{file_id}", use_container_width=True):
                                empty_row = {col: "" for col in questions_df.columns}
                                idx = target_row - 1
                                upper = questions_df.iloc[:idx].to_dict('records')
                                lower = questions_df.iloc[idx:].to_dict('records')
                                st.session_state[f"questions_data_{file_id}"] = upper + [empty_row] + lower
                                st.rerun()
                        with edit_col3:
                            if st.button("아래에 삽입", key=f"insert_below_{file_id}", use_container_width=True):
                                empty_row = {col: "" for col in questions_df.columns}
                                idx = target_row
                                upper = questions_df.iloc[:idx].to_dict('records')
                                lower = questions_df.iloc[idx:].to_dict('records')
                                st.session_state[f"questions_data_{file_id}"] = upper + [empty_row] + lower
                                st.rerun()
                        with edit_col4:
                            if st.button("삭제", key=f"delete_row_{file_id}", use_container_width=True):
                                idx = target_row - 1
                                st.session_state[f"questions_data_{file_id}"] = questions_df.drop(idx).to_dict('records')
                                st.rerun()
                        st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)

                    edited_questions = st.data_editor(
                        questions_df,
                        num_rows="dynamic",
                        use_container_width=True,
                        key=f"edit_q_{file_id}"
                    )

                    # 세션 데이터 정리 (편집 후)
                    if f"questions_data_{file_id}" in st.session_state:
                        del st.session_state[f"questions_data_{file_id}"]
                else:
                    st.info("문항 데이터가 없습니다.")
                    edited_questions = pd.DataFrame()

            with tab2:
                passages = data.get("passages", [])
                if passages:
                    passages_df = pd.DataFrame(passages)
                    edited_passages = st.data_editor(
                        passages_df,
                        num_rows="dynamic",
                        use_container_width=True,
                        key=f"edit_p_{file_id}"
                    )
                else:
                    st.info("지문 데이터가 없습니다.")
                    edited_passages = pd.DataFrame()

            with tab3:
                meta = data.get("meta", {})
                # 메타정보를 개별 입력 필드로 표시
                st.markdown("##### 기본 정보")
                st.text_input("파일 ID", value=meta.get("file_id", ""), disabled=True, key=f"meta_fileid_{file_id}")

                meta_col1, meta_col2 = st.columns(2)
                with meta_col1:
                    edit_subject = st.text_input("과목", value=str(meta.get("subject", "")), key=f"meta_subject_{file_id}")
                    edit_year = st.text_input("연도", value=str(meta.get("year", "")), key=f"meta_year_{file_id}")
                    edit_exam_type = st.selectbox(
                        "시험 유형",
                        options=["", "모의고사", "수능", "중간고사", "기말고사", "기타"],
                        index=["", "모의고사", "수능", "중간고사", "기말고사", "기타"].index(meta.get("exam_type", "")) if meta.get("exam_type", "") in ["", "모의고사", "수능", "중간고사", "기말고사", "기타"] else 0,
                        key=f"meta_examtype_{file_id}"
                    )
                    edit_grade = st.selectbox(
                        "학년",
                        options=["", "고1", "고2", "고3", "중1", "중2", "중3"],
                        index=["", "고1", "고2", "고3", "중1", "중2", "중3"].index(meta.get("grade", "")) if meta.get("grade", "") in ["", "고1", "고2", "고3", "중1", "중2", "중3"] else 0,
                        key=f"meta_grade_{file_id}"
                    )
                with meta_col2:
                    edit_month = st.text_input("월", value=str(meta.get("month", "")), key=f"meta_month_{file_id}")
                    edit_semester = st.selectbox(
                        "학기",
                        options=["", "1학기", "2학기"],
                        index=["", "1학기", "2학기"].index(meta.get("semester", "")) if meta.get("semester", "") in ["", "1학기", "2학기"] else 0,
                        key=f"meta_semester_{file_id}"
                    )
                    edit_school = st.text_input("학교명", value=str(meta.get("school", "")), key=f"meta_school_{file_id}")
                    edit_author = st.text_input("출제자", value=str(meta.get("author", "")), key=f"meta_author_{file_id}")

                edit_desc = st.text_area("메모", value=str(meta.get("desc", "")), key=f"meta_desc_{file_id}")
                st.text_input("생성일시", value=str(meta.get("created_at", "")), disabled=True, key=f"meta_created_{file_id}")

            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

            if st.button("변경사항 저장", type="primary", use_container_width=True):
                new_questions = edited_questions.to_dict('records') if not edited_questions.empty else []
                new_passages = edited_passages.to_dict('records') if not edited_passages.empty else []

                # 메타정보 업데이트
                new_meta = {
                    "file_id": meta.get("file_id", ""),
                    "subject": edit_subject,
                    "year": edit_year,
                    "exam_type": edit_exam_type,
                    "grade": edit_grade,
                    "month": edit_month,
                    "semester": edit_semester,
                    "school": edit_school,
                    "author": edit_author,
                    "desc": edit_desc,
                    "created_at": meta.get("created_at", "")
                }

                update_json_manual(file_id, new_questions, new_passages, new_meta)
                st.success("저장되었습니다.")
                invalidate_json_cache(file_id)
                st.rerun()


# =============================================================================
# 5. 문서 뷰어
# =============================================================================
elif selected == "문서 뷰어":
    st.markdown('''
    <div class="page-header">
        <div class="page-title">문서 뷰어</div>
        <div class="page-desc">추출된 시험지 내용을 미리봅니다</div>
    </div>
    ''', unsafe_allow_html=True)

    db = get_db()
    viewable = [item for item in db if item['status'] in ['Extracted', 'Modified', 'Done']]

    if not viewable:
        st.markdown('''
        <div class="alert alert-info">
            미리볼 문서가 없습니다. 먼저 추출을 완료해주세요.
        </div>
        ''', unsafe_allow_html=True)
    else:
        options = get_doc_options(viewable)
        selected_doc = st.selectbox("문서 선택", list(options.keys()))
        file_id = options[selected_doc]

        data = load_json_cached(file_id)

        if not data:
            st.error(f"데이터를 불러올 수 없습니다. (ID: {file_id}) 추출이 정상 완료되었는지 확인해주세요.")
        else:
            meta = data.get("meta", {})
            questions = data.get("questions", [])
            passages = data.get("passages", [])

            # 문서 정보
            badge_class = 'success' if meta.get('verified_at') else 'ready'
            badge_text = 'AI 검증완료' if meta.get('verified_at') else '미검증'
            doc_info_html = f'<div class="content-card"><div style="display:flex;justify-content:space-between;align-items:center;"><div><h3 style="margin:0;color:#212529;">{meta.get("subject", "제목 없음")}</h3><p style="margin:0.5rem 0 0 0;color:#6c757d;font-size:0.875rem;">{meta.get("exam_type", "")} {meta.get("year", "")} {meta.get("grade", "")}</p></div><div style="text-align:right;"><span class="badge badge-{badge_class}">{badge_text}</span><p style="margin:0.5rem 0 0 0;color:#6c757d;font-size:0.75rem;">문항 {len(questions)}개 | 지문 {len(passages)}개</p></div></div></div>'
            st.markdown(doc_info_html, unsafe_allow_html=True)

            # ── 시험지 PDF 다운로드 (양식 선택) ──
            from exam_pdf_generator import generate_exam_pdf, generate_exam_pdf_from_template, ExamPaperConfig
            from exam_templates import get_all_templates, get_template, template_to_config

            viewer_templates = get_all_templates()
            vt_options = {t["name"]: t["template_id"] for t in viewer_templates}

            dl_col1, dl_col2 = st.columns([2, 1])
            with dl_col1:
                viewer_tmpl_name = st.selectbox("양식 선택", list(vt_options.keys()), key="viewer_tmpl_select")
            with dl_col2:
                st.markdown("<div style='height:1.8rem;'></div>", unsafe_allow_html=True)
                pdf_gen_btn = st.button("시험지 PDF 생성", key="viewer_pdf_gen", use_container_width=True, type="primary")

            if pdf_gen_btn:
                with st.spinner("PDF 생성 중..."):
                    selected_tmpl = get_template(vt_options[viewer_tmpl_name])
                    overrides = {
                        "subject": meta.get("subject", "국어"),
                        "school_name": meta.get("school", ""),
                        "exam_name": f"{meta.get('year', '')} {meta.get('exam_type', '')}".strip(),
                        "grade": meta.get("grade", ""),
                        "title": f"{meta.get('year', '')}학년도 {meta.get('exam_type', '시험')} 문제지",
                    }
                    tmpl_cfg = template_to_config(selected_tmpl, overrides)
                    sorted_questions = sorted(questions, key=lambda x: int(x.get('q_num', 0)) if str(x.get('q_num', 0)).isdigit() else 0)
                    pdf_bytes = generate_exam_pdf_from_template(tmpl_cfg, sorted_questions, passages)
                    fname = f"시험지_{meta.get('exam_type', '')}_{meta.get('subject', '국어')}.pdf".replace(' ', '_')
                    st.download_button("PDF 다운로드", data=pdf_bytes, file_name=fname, mime="application/pdf", use_container_width=True)
                    st.success(f"PDF 생성 완료! ({len(questions)}문항, {len(passages)}지문) — 양식: {viewer_tmpl_name}")

            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

            import re

            view_mode = st.radio(
                "보기 모드",
                ["시험지", "문항별", "지문별"],
                horizontal=True,
                label_visibility="collapsed"
            )

            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

            # 지문에서 문항 범위 파싱 (예: "(객1~8)", "[1~3]", "(17~20)")
            def parse_question_range(text):
                patterns = [
                    r'\(객?(\d+)~(\d+)\)',  # (객1~8), (1~8)
                    r'\[(\d+)~(\d+)\]',      # [1~3]
                    r'(\d+)~(\d+)',          # 17~20
                ]
                for pattern in patterns:
                    match = re.search(pattern, text[:200] if text else '')  # 앞부분만 검색
                    if match:
                        return int(match.group(1)), int(match.group(2))
                return None, None

            # 지문-문항 매핑 생성
            def build_passage_question_map():
                passage_map = []
                for p in passages:
                    start, end = parse_question_range(p.get('passage_content', ''))
                    passage_map.append({
                        'passage': p,
                        'q_start': start,
                        'q_end': end,
                        'questions': []
                    })

                # passage_id 기반 역색인 (빠른 lookup)
                pid_to_pm = {}
                for pm in passage_map:
                    pid = pm['passage'].get('passage_id')
                    if pid and pid not in pid_to_pm:
                        pid_to_pm[pid] = pm

                # 문항을 지문에 매핑
                for q in sorted(questions, key=lambda x: int(x.get('q_num', 0)) if str(x.get('q_num', 0)).isdigit() else 0):
                    q_num = q.get('q_num', 0)
                    q_pid = q.get('passage_id')
                    matched = False

                    # 1차: passage_id 기반 매칭
                    if q_pid and q_pid in pid_to_pm:
                        pid_to_pm[q_pid]['questions'].append(q)
                        matched = True

                    # 2차 fallback: 문항 범위 매칭
                    if not matched:
                        for pm in passage_map:
                            if pm['q_start'] and pm['q_end']:
                                if pm['q_start'] <= q_num <= pm['q_end']:
                                    pm['questions'].append(q)
                                    matched = True
                                    break

                    # 3차 fallback: 같은 페이지 기준 (하위호환)
                    if not matched:
                        for pm in passage_map:
                            if pm['passage'].get('page_num') == q.get('page_num'):
                                pm['questions'].append(q)
                                break

                return passage_map

            # === 시험지 뷰 ===
            if view_mode == "시험지":
                st.markdown("""
                <style>
                .exam-section { margin-bottom: 2rem; }
                .exam-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 0.75rem 1.25rem; border-radius: 8px 8px 0 0;
                    font-weight: 600; font-size: 0.95rem;
                }
                .exam-passage {
                    background: #fafbfc; border: 1px solid #e1e4e8; border-top: none;
                    padding: 1.5rem; line-height: 1.9; font-size: 0.95rem;
                }
                .exam-passage-text { white-space: pre-wrap; color: #24292e; }
                .exam-questions { background: #fff; border: 1px solid #e1e4e8; border-top: none;
                    padding: 1.25rem; border-radius: 0 0 8px 8px; }
                .exam-q { margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px dashed #e1e4e8; }
                .exam-q:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
                .exam-q-num { display: inline-block; background: #667eea; color: white;
                    padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700; font-size: 0.9rem; margin-right: 0.5rem; }
                .exam-q-stem { margin: 0.75rem 0; line-height: 1.7; font-size: 0.95rem; color: #24292e; white-space: pre-wrap; }
                .exam-q-ref { background: #f6f8fa; border-left: 3px solid #667eea;
                    padding: 1rem; margin: 1rem 0; border-radius: 0 6px 6px 0; font-size: 0.9rem; color: #24292e; }
                .exam-choices { margin-top: 0.75rem; }
                .exam-choice { padding: 0.4rem 0; color: #24292e; font-size: 0.9rem; line-height: 1.5; }
                </style>
                """, unsafe_allow_html=True)

                passage_map = build_passage_question_map()

                for pm in passage_map:
                    p = pm['passage']
                    qs = pm['questions']

                    # 이전 페이지 연속 지문은 헤더 다르게
                    if p.get('is_continued_from_prev'):
                        header_text = f"(이어서) {p.get('category', '')}"
                    else:
                        q_range = ""
                        if pm['q_start'] and pm['q_end']:
                            q_range = f" [{pm['q_start']}~{pm['q_end']}번]"
                        header_text = f"{p.get('category', '')}{q_range}"

                    passage_content = escape_html(p.get('passage_content', '')).replace('\n', '<br/>')

                    # 시험지 섹션 - 깔끔한 HTML 생성
                    html_parts = []
                    html_parts.append(f'<div class="exam-section">')
                    html_parts.append(f'<div class="exam-header">{escape_html(header_text)}</div>')
                    html_parts.append(f'<div class="exam-passage"><div class="exam-passage-text">{passage_content}</div></div>')

                    if qs:
                        html_parts.append('<div class="exam-questions">')
                        for q in qs:
                            # 선지 HTML
                            choices_list = []
                            for i in range(1, 6):
                                choice = q.get(f'choice_{i}', '')
                                if choice:
                                    choices_list.append(f'<div class="exam-choice">{escape_html(choice)}</div>')
                            choices_html = ''.join(choices_list)

                            # 보기 HTML
                            ref_html = ""
                            if q.get('reference_box'):
                                ref_content = escape_html(q["reference_box"]).replace('\n', '<br/>')
                                ref_html = f'<div class="exam-q-ref"><strong>&lt;보기&gt;</strong><br/>{ref_content}</div>'

                            q_stem = escape_html(q.get('q_stem', '')).replace('\n', '<br/>')
                            q_category = escape_html(q.get('category', ''))

                            q_html = f'<div class="exam-q"><span class="exam-q-num">{q.get("q_num", "?")}</span><span style="color:#586069;font-size:0.8rem;">{q_category}</span><div class="exam-q-stem">{q_stem}</div>{ref_html}<div class="exam-choices">{choices_html}</div></div>'
                            html_parts.append(q_html)
                        html_parts.append('</div>')

                    html_parts.append('</div>')
                    final_html = ''.join(html_parts)
                    st.markdown(final_html, unsafe_allow_html=True)

                # 지문에 매핑되지 않은 독립 문항 표시
                mapped_q_nums = set()
                for pm in passage_map:
                    for q in pm['questions']:
                        mapped_q_nums.add(q.get('q_num'))

                orphan_questions = [q for q in questions if q.get('q_num') not in mapped_q_nums]
                if orphan_questions:
                    # 하나의 완전한 HTML 블록으로 구성
                    orphan_parts = ['<div class="exam-section"><div class="exam-header">기타 문항</div><div class="exam-questions">']
                    for q in sorted(orphan_questions, key=lambda x: int(x.get('q_num', 0)) if str(x.get('q_num', 0)).isdigit() else 0):
                        choices_html = "".join([f'<div class="exam-choice">{escape_html(q.get(f"choice_{i}", ""))}</div>' for i in range(1, 6) if q.get(f'choice_{i}')])
                        ref_content = escape_html(q.get("reference_box", "")).replace('\n', '<br/>') if q.get('reference_box') else ""
                        ref_html = f'<div class="exam-q-ref"><strong>&lt;보기&gt;</strong><br/>{ref_content}</div>' if ref_content else ""
                        q_stem = escape_html(q.get('q_stem', '')).replace('\n', '<br/>')
                        orphan_parts.append(f'<div class="exam-q"><span class="exam-q-num">{q.get("q_num", "?")}</span><div class="exam-q-stem">{q_stem}</div>{ref_html}<div class="exam-choices">{choices_html}</div></div>')
                    orphan_parts.append('</div></div>')
                    st.markdown(''.join(orphan_parts), unsafe_allow_html=True)

            # === 문항별 뷰 ===
            elif view_mode == "문항별":
                for q in sorted(questions, key=lambda x: int(x.get('q_num', 0)) if str(x.get('q_num', 0)).isdigit() else 0):
                    choices_html = "".join([f'<div class="q-choice">{escape_html(q.get(f"choice_{i}", ""))}</div>' for i in range(1, 6) if q.get(f'choice_{i}')])
                    ref_content = escape_html(q.get("reference_box", "")).replace('\n', '<br/>') if q.get('reference_box') else ""
                    ref_html = f'<div class="q-ref"><strong>&lt;보기&gt;</strong><div style="margin-top:0.5rem;">{ref_content}</div></div>' if ref_content else ""
                    q_stem = escape_html(q.get('q_stem', '')).replace('\n', '<br/>')
                    card_html = f'<div class="q-card"><div><span class="q-num">{q.get("q_num", "?")}번</span><span class="q-category">{escape_html(q.get("category", ""))}</span></div><div class="q-stem">{q_stem}</div>{ref_html}<div style="margin-top:0.75rem;">{choices_html}</div></div>'
                    st.markdown(card_html, unsafe_allow_html=True)

            # === 지문별 뷰 ===
            elif view_mode == "지문별":
                passage_map = build_passage_question_map()
                for idx, pm in enumerate(passage_map, 1):
                    p = pm['passage']
                    qs = pm['questions']
                    q_range = f" ({pm['q_start']}~{pm['q_end']}번)" if pm['q_start'] else ""

                    with st.expander(f"지문 {idx}: {p.get('category', '')}{q_range}", expanded=True):
                        passage_text = escape_html(p.get("passage_content", "")).replace('\n', '<br/>')
                        st.markdown(f'<div style="line-height:1.9;font-size:0.95rem;">{passage_text}</div>', unsafe_allow_html=True)

                        if qs:
                            st.markdown("---")
                            st.markdown(f"**관련 문항 ({len(qs)}개)**")
                            for q in qs:
                                choices_html = "".join([f'<div class="q-choice">{escape_html(q.get(f"choice_{j}", ""))}</div>' for j in range(1, 6) if q.get(f'choice_{j}')])
                                ref_content = escape_html(q.get("reference_box", "")).replace('\n', '<br/>') if q.get('reference_box') else ""
                                ref_html = f'<div class="q-ref"><strong>&lt;보기&gt;</strong><div style="margin-top:0.5rem;">{ref_content}</div></div>' if ref_content else ""
                                q_stem = escape_html(q.get('q_stem', '')).replace('\n', '<br/>')
                                card_html = f'<div class="q-card"><span class="q-num">{q.get("q_num", "?")}번</span><div class="q-stem">{q_stem}</div>{ref_html}<div>{choices_html}</div></div>'
                                st.markdown(card_html, unsafe_allow_html=True)

# =============================================================================
# 6. 시험지구성
# =============================================================================
elif selected == "시험지구성":
    from exam_pdf_generator import generate_exam_pdf, generate_exam_pdf_from_template, ExamPaperConfig
    from exam_templates import (
        get_all_templates, get_template, save_template,
        delete_template, duplicate_template, template_to_config,
    )

    st.markdown('<div class="page-header"><div class="page-title">시험지구성</div><div class="page-desc">문항을 선택하여 시험지 PDF를 생성합니다</div></div>', unsafe_allow_html=True)

    compose_tab, template_tab = st.tabs(["시험지 만들기", "양식 관리"])

    # =================================================================
    # 탭 2: 양식 관리
    # =================================================================
    with template_tab:
        st.markdown("#### 시험지 양식 관리")
        st.info("양식을 생성/편집하여 시험지 PDF의 레이아웃, 폰트, 여백 등을 자유롭게 커스터마이징할 수 있습니다.")

        templates = get_all_templates()

        # 양식 목록
        tmpl_col1, tmpl_col2 = st.columns([3, 1])
        with tmpl_col2:
            if st.button("새 양식 만들기", use_container_width=True, type="primary"):
                st.session_state["editing_template"] = {
                    "template_id": "",
                    "name": "새 양식",
                    "description": "",
                    "is_default": False,
                    "layout": {"columns": 1, "page_size": "A4", "margin_top": 12, "margin_bottom": 10, "margin_left": 15, "margin_right": 15, "gutter": 0},
                    "header": {"style": "school", "line_1": "{school_name}", "line_2": "{exam_name}", "line_3": "과목: {subject}  |  학년: {grade}", "show_border": True},
                    "footer": {"show_page_number": True, "custom_text": ""},
                    "fonts": {"passage_size": 10, "passage_leading": 15, "stem_size": 11, "stem_leading": 16, "choice_size": 10, "choice_leading": 14, "box_title_size": 10, "box_body_size": 9.5},
                    "spacing": {"before_question": 12, "after_question": 3, "choice_gap": 2, "passage_indent": 10},
                    "exam_info": {"school_name": "", "exam_name": "", "subject": "국어", "grade": "", "exam_date": "", "time_limit": ""},
                }

        with tmpl_col1:
            st.markdown(f"**등록된 양식: {len(templates)}개**")

        for tmpl in templates:
            cols_label = "2단" if tmpl.get("layout", {}).get("columns", 1) == 2 else "1단"
            header_style = tmpl.get("header", {}).get("style", "school")
            default_badge = " (기본)" if tmpl.get("is_default") else ""

            with st.expander(f"**{tmpl['name']}**{default_badge} — {cols_label} / {header_style}"):
                st.caption(tmpl.get("description", ""))

                # 주요 설정 미리보기
                fonts = tmpl.get("fonts", {})
                layout = tmpl.get("layout", {})
                prev_col1, prev_col2, prev_col3 = st.columns(3)
                prev_col1.metric("단수", f"{layout.get('columns', 1)}단")
                prev_col2.metric("발문 폰트", f"{fonts.get('stem_size', 11)}pt")
                prev_col3.metric("좌우 여백", f"{layout.get('margin_left', 15)}mm")

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("편집", key=f"edit_{tmpl['template_id']}", use_container_width=True):
                        st.session_state["editing_template"] = {**tmpl}
                with btn_col2:
                    if st.button("복제", key=f"dup_{tmpl['template_id']}", use_container_width=True):
                        new_id = duplicate_template(tmpl["template_id"])
                        if new_id:
                            st.success(f"복제 완료!")
                            st.rerun()
                with btn_col3:
                    if tmpl.get("is_default"):
                        st.button("삭제 불가", key=f"del_{tmpl['template_id']}", disabled=True, use_container_width=True)
                    else:
                        if st.button("삭제", key=f"del_{tmpl['template_id']}", use_container_width=True):
                            delete_template(tmpl["template_id"])
                            st.success("삭제 완료!")
                            st.rerun()

        # 양식 편집 폼
        if "editing_template" in st.session_state:
            st.markdown("---")
            tmpl_edit = st.session_state["editing_template"]
            tid = tmpl_edit.get("template_id", "new")  # 양식별 고유 키 접미사
            is_new = not tmpl_edit.get("template_id")
            edit_title = "새 양식 만들기" if is_new else f"양식 편집: {tmpl_edit.get('name', '')}"
            st.markdown(f"#### {edit_title}")

            edit_left, edit_right = st.columns([1, 1])

            # ── 왼쪽: 설정 폼 ──
            with edit_left:
                layout_e = tmpl_edit.setdefault("layout", {})
                header_e = tmpl_edit.setdefault("header", {})
                footer_e = tmpl_edit.setdefault("footer", {})
                fonts_e = tmpl_edit.setdefault("fonts", {})
                spacing_e = tmpl_edit.setdefault("spacing", {})

                tmpl_edit["name"] = st.text_input("양식 이름", value=tmpl_edit.get("name", ""), key=f"tn_{tid}")
                tmpl_edit["description"] = st.text_input("설명", value=tmpl_edit.get("description", ""), key=f"td_{tid}")

                st.markdown("##### 레이아웃")
                le_col1, le_col2 = st.columns(2)
                with le_col1:
                    layout_e["columns"] = st.selectbox("단수", [1, 2], index=0 if layout_e.get("columns", 1) == 1 else 1, key=f"tc_{tid}")
                    layout_e["margin_left"] = st.number_input("좌우 여백(mm)", value=layout_e.get("margin_left", 15), min_value=5, max_value=40, key=f"tml_{tid}")
                    layout_e["margin_right"] = layout_e["margin_left"]
                with le_col2:
                    layout_e["margin_top"] = st.number_input("상 여백(mm)", value=layout_e.get("margin_top", 12), min_value=5, max_value=40, key=f"tmt_{tid}")
                    layout_e["margin_bottom"] = st.number_input("하 여백(mm)", value=layout_e.get("margin_bottom", 10), min_value=5, max_value=40, key=f"tmb_{tid}")
                if layout_e["columns"] == 2:
                    layout_e["gutter"] = st.number_input("단 간격(mm)", value=layout_e.get("gutter", 6), min_value=2, max_value=20, key=f"tg_{tid}")

                st.markdown("##### 헤더")
                header_styles = ["school", "suneung", "minimal", "none"]
                cur_style = header_e.get("style", "school")
                style_idx = header_styles.index(cur_style) if cur_style in header_styles else 0
                he_col1, he_col2 = st.columns(2)
                with he_col1:
                    header_e["style"] = st.selectbox("헤더 스타일", header_styles, index=style_idx, key=f"ths_{tid}")
                with he_col2:
                    header_e["show_border"] = st.checkbox("구분선 표시", value=header_e.get("show_border", True), key=f"thb_{tid}")
                header_e["line_1"] = st.text_input("1행", value=header_e.get("line_1", ""), key=f"th1_{tid}",
                    help="변수: {school_name}, {exam_name}, {title}, {subject}, {grade}, {session}, {form_type}, {exam_date}, {time_limit}")
                header_e["line_2"] = st.text_input("2행", value=header_e.get("line_2", ""), key=f"th2_{tid}")
                header_e["line_3"] = st.text_input("3행", value=header_e.get("line_3", ""), key=f"th3_{tid}")

                st.markdown("##### 푸터")
                fe_col1, fe_col2 = st.columns(2)
                with fe_col1:
                    footer_e["show_page_number"] = st.checkbox("페이지 번호", value=footer_e.get("show_page_number", True), key=f"tfp_{tid}")
                with fe_col2:
                    footer_e["custom_text"] = st.text_input("푸터 텍스트", value=footer_e.get("custom_text", ""), key=f"tft_{tid}")

                st.markdown("##### 폰트 크기")
                fc1, fc2 = st.columns(2)
                with fc1:
                    fonts_e["passage_size"] = st.number_input("지문(pt)", value=float(fonts_e.get("passage_size", 10)), min_value=6.0, max_value=16.0, step=0.5, key=f"tfps_{tid}")
                    fonts_e["passage_leading"] = fonts_e["passage_size"] + 5
                    fonts_e["stem_size"] = st.number_input("발문(pt)", value=float(fonts_e.get("stem_size", 11)), min_value=6.0, max_value=16.0, step=0.5, key=f"tfss_{tid}")
                    fonts_e["stem_leading"] = fonts_e["stem_size"] + 5
                with fc2:
                    fonts_e["choice_size"] = st.number_input("선지(pt)", value=float(fonts_e.get("choice_size", 10)), min_value=6.0, max_value=16.0, step=0.5, key=f"tfcs_{tid}")
                    fonts_e["choice_leading"] = fonts_e["choice_size"] + 4
                    fonts_e["box_body_size"] = st.number_input("보기(pt)", value=float(fonts_e.get("box_body_size", 9.5)), min_value=6.0, max_value=16.0, step=0.5, key=f"tfbs_{tid}")
                    fonts_e["box_title_size"] = fonts_e["box_body_size"] + 0.5

                st.markdown("##### 간격")
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    spacing_e["before_question"] = st.number_input("문항 전", value=int(spacing_e.get("before_question", 12)), min_value=4, max_value=30, key=f"tsb_{tid}")
                with sc2:
                    spacing_e["choice_gap"] = st.number_input("선지", value=int(spacing_e.get("choice_gap", 2)), min_value=0, max_value=10, key=f"tsc_{tid}")
                with sc3:
                    spacing_e["passage_indent"] = st.number_input("들여쓰기", value=int(spacing_e.get("passage_indent", 10)), min_value=0, max_value=30, key=f"tsp_{tid}")

                save_col1, save_col2 = st.columns(2)
                with save_col1:
                    if st.button("저장", use_container_width=True, type="primary", key="tmpl_save"):
                        saved_id = save_template(tmpl_edit)
                        st.success(f"양식 '{tmpl_edit['name']}' 저장 완료!")
                        del st.session_state["editing_template"]
                        st.rerun()
                with save_col2:
                    if st.button("취소", use_container_width=True, key="tmpl_cancel"):
                        del st.session_state["editing_template"]
                        st.rerun()

            # ── 오른쪽: 실시간 미리보기 ──
            with edit_right:
                st.markdown("##### 미리보기")
                # 변수 치환용 샘플 데이터
                sample_vars = {
                    "school_name": "서울고등학교", "exam_name": "2026학년도 1학기 중간고사",
                    "title": "2026학년도 대학수학능력시험 문제지", "subject": "국어",
                    "grade": "1학년", "session": "제1교시", "form_type": "홀수형",
                    "exam_date": "2026.04.25", "time_limit": "50분",
                }
                h1 = header_e.get("line_1", "").format_map({**sample_vars, **{k: v for k, v in sample_vars.items()}})
                h2 = header_e.get("line_2", "").format_map(sample_vars)
                h3 = header_e.get("line_3", "").format_map(sample_vars)

                margin_lr = layout_e.get("margin_left", 15)
                margin_t = layout_e.get("margin_top", 12)
                cols = layout_e.get("columns", 1)
                stem_sz = fonts_e.get("stem_size", 11)
                passage_sz = fonts_e.get("passage_size", 10)
                choice_sz = fonts_e.get("choice_size", 10)
                box_sz = fonts_e.get("box_body_size", 9.5)
                q_gap = spacing_e.get("before_question", 12)
                c_gap = spacing_e.get("choice_gap", 2)
                p_indent = spacing_e.get("passage_indent", 10)
                border_css = "border-bottom:2px solid #333;padding-bottom:8px;margin-bottom:12px;" if header_e.get("show_border") else "margin-bottom:12px;"
                footer_txt = footer_e.get("custom_text", "")
                show_pn = footer_e.get("show_page_number", True)

                # 헤더 스타일별 HTML
                h_style = header_e.get("style", "school")
                if h_style == "none":
                    header_html = ""
                elif h_style == "suneung":
                    header_html = f'<div style="text-align:center;{border_css}"><div style="font-size:10px;color:#333;">{h1}</div><div style="font-size:22px;font-weight:bold;margin:4px 0;">{h2}</div><div style="font-size:9px;color:#555;">{h3}</div></div>'
                elif h_style == "minimal":
                    header_html = f'<div style="{border_css}"><div style="font-size:14px;font-weight:600;">{h1}</div><div style="font-size:9px;color:#666;margin-top:2px;">{h3}</div></div>'
                else:
                    header_html = f'<div style="text-align:center;{border_css}"><div style="font-size:16px;font-weight:bold;">{h1}</div><div style="font-size:13px;font-weight:600;margin:3px 0;">{h2}</div><div style="font-size:9px;color:#555;">{h3}</div></div>'

                # 푸터 HTML
                footer_parts = []
                if show_pn:
                    footer_parts.append("1")
                if footer_txt:
                    footer_parts.append(f'<span style="font-size:6px;color:#999;">{footer_txt}</span>')
                footer_html = f'<div style="text-align:center;border-top:1px solid #ddd;padding-top:4px;margin-top:10px;font-size:8px;color:#666;">{" &nbsp; ".join(footer_parts)}</div>' if footer_parts else ""

                # 샘플 문항 HTML
                sample_passage = f'<div style="font-size:{passage_sz}px;line-height:1.5;text-indent:{p_indent}px;color:#333;margin-bottom:8px;">글을 읽고 그 의미를 이해하는 독해에는 글의 유형이나 독서 흥미 등의 다양한 요소가 영향을 미칠 수 있다. 이를 고려하여 독해 능력을 복잡한 과정으로 설명한 연구가 많다.</div>'
                sample_q1 = f'<div style="margin-top:{q_gap}px;"><div style="font-size:{stem_sz}px;font-weight:500;"><b>1.</b> 윗글의 내용과 일치하지 않는 것은?</div>'
                sample_choices = "".join([f'<div style="font-size:{choice_sz}px;padding-left:14px;margin:{c_gap}px 0;color:#444;">{c}</div>' for c in ["① 해독은 단어 인식 능력이다.", "② 언어 이해는 의미 파악 능력이다.", "③ 독해는 해독과 언어 이해의 곱이다.", "④ 해독과 언어 이해는 독립적이다.", "⑤ 독서 경험이 선행되어야 한다."]])
                sample_q2 = f'<div style="margin-top:{q_gap}px;"><div style="font-size:{stem_sz}px;font-weight:500;"><b>2.</b> &lt;보기&gt;를 바탕으로 이해한 내용으로 적절한 것은?</div><div style="border:1px solid #999;padding:6px 8px;margin:4px 0;font-size:{box_sz}px;color:#444;text-align:center;"><b>&lt;보 기&gt;</b><br/>학생 A는 해독은 잘 되었으나 이해력이 부족했다.</div>'
                sample_choices2 = "".join([f'<div style="font-size:{choice_sz}px;padding-left:14px;margin:{c_gap}px 0;color:#444;">{c}</div>' for c in ["① 학생 A는 해독이 발달되었다.", "② 학생 A는 언어 이해가 부족하다.", "③ 학생 B는 해독이 부족하다."]])

                # 2단 처리
                if cols == 2:
                    col_css = "display:flex;gap:8px;"
                    content_html = f'<div style="{col_css}"><div style="flex:1;">{sample_passage}{sample_q1}{sample_choices}</div></div><div style="{col_css}"><div style="flex:1;">{sample_q2}{sample_choices2}</div></div></div>'
                else:
                    content_html = f'{sample_passage}{sample_q1}{sample_choices}</div>{sample_q2}{sample_choices2}</div>'

                # 전체 미리보기 조립
                preview_html = f'''
                <div style="border:2px solid #333;padding:{margin_t}px {margin_lr}px;background:white;font-family:'Noto Sans KR',sans-serif;max-height:600px;overflow-y:auto;box-shadow:0 2px 8px rgba(0,0,0,0.15);">
                    {header_html}
                    {content_html}
                    {footer_html}
                </div>
                '''
                st.markdown(preview_html, unsafe_allow_html=True)
                st.caption("설정을 변경하면 미리보기가 자동 업데이트됩니다.")

    # =================================================================
    # 탭 1: 시험지 만들기 (기존 시험지구성 로직)
    # =================================================================
    with compose_tab:
        # 양식 선택 드롭다운
        all_templates = get_all_templates()
        tmpl_options = {t["name"]: t["template_id"] for t in all_templates}
        selected_tmpl_name = st.selectbox("양식 선택", list(tmpl_options.keys()), key="compose_template_select")
        active_template = get_template(tmpl_options[selected_tmpl_name]) if selected_tmpl_name else None

        # 세션 상태는 앱 상단에서 초기화됨

        # 양식에서 기본값 가져오기
        if active_template:
            tmpl_info = active_template.get("exam_info", {})
            for k, v in tmpl_info.items():
                if v and k in st.session_state.exam_info and not st.session_state.exam_info[k]:
                    st.session_state.exam_info[k] = v

        # 상단: 시험지 정보 입력
        st.markdown('<div class="content-card"><h4 style="margin:0 0 1rem 0;color:#212529;">시험지 정보</h4>', unsafe_allow_html=True)

        # 레이아웃 선택
        layout_choice = st.radio("레이아웃", ["수능형", "내신형"], horizontal=True, key="layout_radio")
        st.session_state.exam_info['layout_type'] = layout_choice

        if layout_choice == "수능형":
            col1, col2, col3 = st.columns(3)
            with col1:
                st.session_state.exam_info['title'] = st.text_input("시험 제목", value=st.session_state.exam_info['title'], placeholder="예: 2026학년도 대학수학능력시험 문제지")
                st.session_state.exam_info['subject'] = st.text_input("영역명", value=st.session_state.exam_info['subject'], placeholder="예: 국어 영역")
            with col2:
                st.session_state.exam_info['session'] = st.text_input("교시", value=st.session_state.exam_info['session'], placeholder="예: 제1교시")
                st.session_state.exam_info['form_type'] = st.text_input("형번호", value=st.session_state.exam_info['form_type'], placeholder="예: 홀수형")
            with col3:
                st.markdown("<div style='height:3.5rem;'></div>", unsafe_allow_html=True)
                st.markdown("<div style='background:#f8f9fa;padding:0.75rem;border-radius:8px;font-size:0.8rem;color:#6c757d;'>수능/모의고사 스타일 2단 레이아웃.<br/>지문과 문항이 함께 배치됩니다.</div>", unsafe_allow_html=True)
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.session_state.exam_info['school_name'] = st.text_input("학교명", value=st.session_state.exam_info['school_name'], placeholder="예: ○○고등학교")
                st.session_state.exam_info['subject'] = st.text_input("과목", value=st.session_state.exam_info['subject'], placeholder="예: 국어")
            with col2:
                st.session_state.exam_info['exam_name'] = st.text_input("시험명", value=st.session_state.exam_info['exam_name'], placeholder="예: 2026학년도 1학기 중간고사")
                st.session_state.exam_info['grade'] = st.text_input("학년/반", value=st.session_state.exam_info['grade'], placeholder="예: 1학년")
            with col3:
                st.session_state.exam_info['date'] = st.text_input("시험일", value=st.session_state.exam_info['date'], placeholder="예: 2026.04.25")
                st.session_state.exam_info['time_limit'] = st.text_input("시험시간", value=st.session_state.exam_info['time_limit'], placeholder="예: 50분")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        # 2단 레이아웃: 문항 선택 | 선택된 문항
        left_col, right_col = st.columns([1, 1])

        # 왼쪽: 문항 선택
        with left_col:
            st.markdown('<div class="content-card"><h4 style="margin:0 0 1rem 0;color:#212529;">문항 선택</h4>', unsafe_allow_html=True)

            all_db = get_db()
            available_docs = [item for item in all_db if item['status'] in ['Extracted', 'Modified', 'Done']]

            if available_docs:
                file_options = get_doc_options(available_docs)

                selected_file = st.selectbox("문서 선택", list(file_options.keys()), key="exam_file_select")

                if selected_file:
                    file_id = file_options[selected_file]
                    data = load_json_cached(file_id)

                    if data:
                        questions = data.get("questions", [])
                        passages = data.get("passages", [])

                        # passages 캐시 (PDF 생성 시 사용)
                        st.session_state.exam_passages_cache[file_id] = passages

                        # 카테고리 필터
                        categories = list(set([q.get('category', '기타') for q in questions]))
                        selected_category = st.selectbox("카테고리 필터", ["전체"] + categories, key="exam_category_filter")

                        filtered_questions = questions if selected_category == "전체" else [q for q in questions if q.get('category') == selected_category]
                        sorted_filtered = sorted(filtered_questions, key=lambda x: int(x.get('q_num', 0)) if str(x.get('q_num', 0)).isdigit() else 0)

                        # 전체/카테고리 일괄 선택 버튼
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button(f"전체 추가 ({len(sorted_filtered)}문항)", key="add_all_q", use_container_width=True):
                                existing_ids = set(sq['id'] for sq in st.session_state.exam_selected_questions)
                                added = 0
                                for q_idx, q in enumerate(sorted_filtered):
                                    q_id = f"{file_id}_{q.get('page_num',0)}_{q.get('q_num','?')}_{q_idx}"
                                    if q_id not in existing_ids:
                                        st.session_state.exam_selected_questions.append({'id': q_id, 'file_id': file_id, 'question_data': q})
                                        added += 1
                                if added:
                                    st.rerun()
                        with btn_col2:
                            if st.button("선택 초기화", key="clear_checks", use_container_width=True):
                                for k in list(st.session_state.keys()):
                                    if k.startswith("chk_"):
                                        del st.session_state[k]
                                st.rerun()

                        st.markdown(f"**{len(sorted_filtered)}개 문항** — 체크 후 하단 '선택 추가' 클릭")

                        # 체크박스 기반 문항 목록
                        check_states = {}
                        for q_idx, q in enumerate(sorted_filtered):
                            q_num = q.get('q_num', '?')
                            q_stem_raw = q.get('q_stem', '') or ''
                            q_stem = q_stem_raw[:60] + "..." if len(q_stem_raw) > 60 else q_stem_raw
                            q_category = q.get('category', '')
                            score = q.get('score') or q.get('points') or ''
                            score_str = f" [{score}점]" if score else ""
                            q_id = f"{file_id}_{q.get('page_num',0)}_{q_num}_{q_idx}"
                            is_already = any(sq['id'] == q_id for sq in st.session_state.exam_selected_questions)

                            label = f"{q_num}번 ({q_category}{score_str}) — {q_stem}"
                            if is_already:
                                st.markdown(f"<div style='padding:4px 8px;background:#d4edda;border-radius:4px;margin-bottom:4px;font-size:0.82rem;color:#155724;'>✓ {escape_html(label)}</div>", unsafe_allow_html=True)
                            else:
                                check_states[q_id] = st.checkbox(label, key=f"chk_{q_id}", value=False)

                        # 체크된 문항 일괄 추가
                        checked_ids = [qid for qid, checked in check_states.items() if checked]
                        if checked_ids:
                            if st.button(f"선택 추가 ({len(checked_ids)}문항)", type="primary", use_container_width=True, key="add_checked"):
                                existing_ids = set(sq['id'] for sq in st.session_state.exam_selected_questions)
                                for q_idx, q in enumerate(sorted_filtered):
                                    q_id = f"{file_id}_{q.get('page_num',0)}_{q.get('q_num','?')}_{q_idx}"
                                    if q_id in checked_ids and q_id not in existing_ids:
                                        st.session_state.exam_selected_questions.append({'id': q_id, 'file_id': file_id, 'question_data': q})
                                # 체크 상태 초기화
                                for k in list(st.session_state.keys()):
                                    if k.startswith("chk_"):
                                        del st.session_state[k]
                                st.rerun()

            else:
                st.info("추출된 문서가 없습니다. 먼저 데이터 처리를 진행해주세요.")

            st.markdown('</div>', unsafe_allow_html=True)

        # 오른쪽: 선택된 문항 (재번호 + 배점 합계)
        with right_col:
            st.markdown('<div class="content-card"><h4 style="margin:0 0 1rem 0;color:#212529;">선택된 문항</h4>', unsafe_allow_html=True)

            if st.session_state.exam_selected_questions:
                total_score = sum(
                    sq.get('custom_score') or sq['question_data'].get('score') or sq['question_data'].get('points') or 0
                    for sq in st.session_state.exam_selected_questions
                )
                score_text = f" / 총 {total_score}점" if total_score else ""
                st.markdown(f"**{len(st.session_state.exam_selected_questions)}개 문항{score_text}**")

                # 옵션: 원본 번호 유지 / 배점 편집
                opt_col1, opt_col2 = st.columns(2)
                with opt_col1:
                    keep_original = st.checkbox("원본 문항번호 유지", value=False, key="keep_original_num",
                        help="체크 해제 시 PDF에서 1번부터 자동 재번호됩니다")
                with opt_col2:
                    edit_scores = st.checkbox("배점 편집", value=False, key="edit_scores",
                        help="각 문항의 배점을 직접 지정합니다")

                # 배점 편집 모드: 일괄 배점 설정
                if edit_scores:
                    sc_col1, sc_col2 = st.columns(2)
                    with sc_col1:
                        default_score = st.number_input("기본 배점", min_value=1, max_value=10, value=3, step=1, key="default_score")
                    with sc_col2:
                        if st.button("전체 문항에 적용", key="apply_default_score"):
                            for sq in st.session_state.exam_selected_questions:
                                sq['custom_score'] = default_score
                            st.rerun()

                for idx, sq in enumerate(st.session_state.exam_selected_questions):
                    qd = sq['question_data']
                    orig_num = qd.get('q_num', '?')
                    new_num = orig_num if keep_original else idx + 1
                    q_stem_short = (qd.get('q_stem', '') or '')[:35]
                    if len(qd.get('q_stem', '') or '') > 35:
                        q_stem_short += "..."
                    cat = qd.get('category', '')

                    # 배점: custom_score 우선, 없으면 원본
                    orig_score = qd.get('score') or qd.get('points') or ''
                    display_score = sq.get('custom_score', orig_score) if edit_scores else orig_score
                    score_str = f" {display_score}점" if display_score else ""

                    # 번호 표시: 재번호 → (원본)
                    if keep_original:
                        num_display = f"<strong>{orig_num}번</strong>"
                    else:
                        num_display = f"<strong>{new_num}번</strong> <span style='color:#999;font-size:0.75rem;'>(원본:{orig_num})</span>"

                    if edit_scores:
                        col_a, col_score, col_b, col_c, col_d = st.columns([3, 1, 1, 1, 1])
                    else:
                        col_a, col_b, col_c, col_d = st.columns([4, 1, 1, 1])

                    with col_a:
                        st.markdown(f"<div style='padding:5px 8px;background:#e3f2fd;border-radius:4px;font-size:0.82rem;color:#212529;'>{num_display} <span style='color:#667eea;'>{cat}</span>{score_str}<br/><span style='color:#555;'>{escape_html(q_stem_short)}</span></div>", unsafe_allow_html=True)

                    if edit_scores:
                        with col_score:
                            new_score = st.number_input("점", min_value=1, max_value=10,
                                value=int(sq.get('custom_score', orig_score) or 3),
                                key=f"score_{sq['id']}", label_visibility="collapsed")
                            if new_score != sq.get('custom_score'):
                                sq['custom_score'] = new_score
                    with col_b:
                        if idx > 0 and st.button("↑", key=f"up_{sq['id']}"):
                            lst = st.session_state.exam_selected_questions
                            lst[idx], lst[idx-1] = lst[idx-1], lst[idx]
                            st.rerun()
                    with col_c:
                        if idx < len(st.session_state.exam_selected_questions) - 1 and st.button("↓", key=f"down_{sq['id']}"):
                            lst = st.session_state.exam_selected_questions
                            lst[idx], lst[idx+1] = lst[idx+1], lst[idx]
                            st.rerun()
                    with col_d:
                        if st.button("✕", key=f"remove_{sq['id']}"):
                            st.session_state.exam_selected_questions.pop(idx)
                            st.rerun()

                st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

                if st.button("전체 삭제", key="clear_all"):
                    st.session_state.exam_selected_questions = []
                    st.rerun()
            else:
                st.info("왼쪽에서 문항을 선택해주세요.\n\n체크박스로 여러 문항을 한 번에 선택할 수 있습니다.")

            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        # 하단: 미리보기 & PDF 생성
        st.markdown('<div class="content-card"><h4 style="margin:0 0 1rem 0;color:#212529;">미리보기 & 출력</h4>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            preview_btn = st.button("시험지 미리보기", use_container_width=True)
        with col2:
            layout_label = "수능형 2단" if st.session_state.exam_info['layout_type'] == '수능형' else "내신형 1단"
            pdf_btn = st.button(f"PDF 생성 ({layout_label})", use_container_width=True, type="primary", disabled=len(st.session_state.exam_selected_questions) == 0)

        if preview_btn and st.session_state.exam_selected_questions:
            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

            info = st.session_state.exam_info
            preview_parts = []
            if info['layout_type'] == '수능형':
                preview_parts.append(f'<div style="border:2px solid #333;padding:2rem;background:white;max-width:800px;margin:0 auto;font-family:Noto Sans KR,sans-serif;">')
                preview_parts.append(f'<div style="text-align:center;border-bottom:2px solid #333;padding-bottom:1rem;margin-bottom:1.5rem;">')
                preview_parts.append(f'<p style="margin:0;color:#000;font-size:0.9rem;">{info["title"]}</p>')
                preview_parts.append(f'<h2 style="margin:0.5rem 0;color:#000;">{info["subject"]}</h2>')
                preview_parts.append(f'<p style="margin:0;color:#333;">{info["session"]} | {info["form_type"]}</p>')
                preview_parts.append('</div>')
            else:
                preview_parts.append(f'<div style="border:2px solid #333;padding:2rem;background:white;max-width:800px;margin:0 auto;font-family:Noto Sans KR,sans-serif;">')
                preview_parts.append(f'<div style="text-align:center;border-bottom:2px solid #333;padding-bottom:1rem;margin-bottom:1.5rem;">')
                preview_parts.append(f'<h2 style="margin:0;color:#000;">{info["school_name"] or "○○고등학교"}</h2>')
                preview_parts.append(f'<h3 style="margin:0.5rem 0;color:#000;">{info["exam_name"] or "시험지"}</h3>')
                preview_parts.append(f'<p style="margin:0;color:#333;">과목: {info["subject"]} | 학년: {info["grade"]} | 시험일: {info["date"]} | 시간: {info["time_limit"]}</p>')
                preview_parts.append('</div>')

            for idx, sq in enumerate(st.session_state.exam_selected_questions):
                qd = sq['question_data']
                choices_html = ''.join([f'<div style="margin:0.3rem 0;color:#000;">{qd.get(f"choice_{i}", "")}</div>' for i in range(1, 6) if qd.get(f'choice_{i}')])
                ref_html = f'<div style="background:#f5f5f5;padding:0.75rem;margin:0.5rem 0;border-left:3px solid #333;color:#000;"><strong>[보기]</strong><br/>{qd.get("reference_box", "")}</div>' if qd.get('reference_box') else ''
                display_pts = sq.get('custom_score') or qd.get('points') or qd.get('score') or ''
                points_html = f' <span style="color:#d93025;">[{display_pts}점]</span>' if display_pts else ''
                preview_parts.append(f'<div style="margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px dashed #ccc;">')
                preview_parts.append(f'<p style="margin:0;color:#000;"><strong>{idx+1}.</strong> {qd.get("q_stem", "")}{points_html}</p>')
                preview_parts.append(ref_html)
                preview_parts.append(f'<div style="margin-top:0.5rem;padding-left:1rem;">{choices_html}</div>')
                preview_parts.append('</div>')

            preview_parts.append('</div>')
            st.markdown(''.join(preview_parts), unsafe_allow_html=True)

        if pdf_btn and st.session_state.exam_selected_questions:
            try:
                info = st.session_state.exam_info

                # ExamPaperConfig 생성
                if info['layout_type'] == '수능형':
                    config = ExamPaperConfig(
                        title=info['title'],
                        subject=info['subject'],
                        session=info['session'],
                        form_type=info['form_type'],
                        layout_type="suneung",
                    )
                else:
                    config = ExamPaperConfig(
                        subject=info['subject'],
                        school_name=info['school_name'],
                        exam_name=info['exam_name'],
                        grade=info['grade'],
                        exam_date=info['date'],
                        time_limit=info['time_limit'],
                        layout_type="school",
                    )

                # 선택된 문항의 question_data 리스트 추출 (재번호 + 배점 적용)
                keep_orig = st.session_state.get("keep_original_num", False)
                selected_q_list = []
                for idx, sq in enumerate(st.session_state.exam_selected_questions):
                    q_copy = {**sq['question_data']}
                    if not keep_orig:
                        q_copy['q_num'] = idx + 1
                    # custom_score가 있으면 배점 덮어쓰기
                    if sq.get('custom_score'):
                        q_copy['score'] = sq['custom_score']
                        q_copy['points'] = sq['custom_score']
                    selected_q_list.append(q_copy)

                # 관련 passages 수집 (캐시 + 필요시 재로드)
                all_passages = []
                seen_file_ids = set(sq['file_id'] for sq in st.session_state.exam_selected_questions)
                for fid in seen_file_ids:
                    if fid in st.session_state.exam_passages_cache:
                        all_passages.extend(st.session_state.exam_passages_cache[fid])
                    else:
                        fdata = load_json_cached(fid)
                        if fdata:
                            passages_data = fdata.get("passages", [])
                            st.session_state.exam_passages_cache[fid] = passages_data
                            all_passages.extend(passages_data)

                # PDF 생성
                pdf_bytes = generate_exam_pdf(config, selected_q_list, all_passages)

                file_name = f"시험지_{info['subject']}.pdf".replace(' ', '_')
                st.download_button(
                    label="PDF 다운로드",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF가 생성되었습니다! 위 버튼을 클릭하여 다운로드하세요.")

            except Exception as e:
                st.error(f"PDF 생성 중 오류가 발생했습니다: {str(e)}")

        st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# 7. 문제은행
# =============================================================================
elif selected == "문제은행":
    st.markdown('''
    <div class="page-header">
        <div class="page-title">문제은행</div>
        <div class="page-desc">수능/모의고사 기출문항을 가져와 문제은행을 구축합니다</div>
    </div>
    ''', unsafe_allow_html=True)

    from kice_importer import (
        fetch_available_files, download_kice_file,
        convert_kice_to_system, import_from_local_json,
        import_kice_exam, TYPE_TO_CATEGORY
    )

    tab1, tab2, tab3 = st.tabs(["KICE 기출 가져오기", "JSON 파일 업로드", "문제은행 현황"])

    # --- 탭 1: KICE 기출 자동 가져오기 ---
    with tab1:
        st.markdown("#### KICE 수능 기출 데이터 가져오기")
        st.info("한국교육과정평가원(KICE) 수능 국어영역 기출문항을 구조화된 데이터로 가져옵니다. (출처: KICE_slayer_AI_Korean)")

        # 이미 가져온 KICE 데이터 확인
        db = get_db()
        imported_kice = [d for d in db if d.get("source") == "KICE_slayer_AI_Korean"]
        imported_filenames = set(d.get("filename", "") for d in imported_kice)

        if imported_kice:
            st.success(f"이미 가져온 KICE 데이터: {len(imported_kice)}건")
            for item in imported_kice:
                st.markdown(f"- **{item.get('year', '')}학년도 {item.get('month', '')}월 수능** (ID: `{item['file_id']}`)")

        st.markdown("---")

        col_fetch, col_status = st.columns([2, 1])
        with col_fetch:
            if st.button("GitHub에서 사용 가능한 데이터 조회", use_container_width=True):
                with st.spinner("GitHub에서 파일 목록 조회 중..."):
                    files = fetch_available_files()
                    if files:
                        st.session_state["kice_available_files"] = files
                    else:
                        st.warning("GitHub에서 파일 목록을 가져올 수 없습니다. gh CLI가 인증되어 있는지 확인해주세요.")

        available = st.session_state.get("kice_available_files", [])
        if available:
            st.markdown(f"**사용 가능한 파일: {len(available)}건**")

            for f_info in available:
                fname = f_info["name"]
                size_kb = f_info.get("size", 0) / 1024
                already = fname in imported_filenames

                col_name, col_size, col_btn = st.columns([3, 1, 1])
                with col_name:
                    year = fname.split("_")[0]
                    label = f"{year}학년도 수능 국어"
                    if already:
                        st.markdown(f"~~{label}~~ (가져옴)")
                    else:
                        st.markdown(f"**{label}**")
                with col_size:
                    st.caption(f"{size_kb:.1f} KB")
                with col_btn:
                    if not already:
                        if st.button("가져오기", key=f"import_{fname}"):
                            with st.spinner(f"{fname} 가져오는 중..."):
                                result = import_kice_exam(fname)
                            if result["success"]:
                                stats = result["stats"]
                                st.success(
                                    f"가져오기 완료! "
                                    f"지문 {stats['passages']}개, "
                                    f"문항 {stats['questions']}개, "
                                    f"총점 {stats['total_score']}점"
                                )
                                st.rerun()
                            else:
                                st.error(f"가져오기 실패: {result.get('error', '알 수 없는 오류')}")

    # --- 탭 2: KICE 형식 JSON 파일 직접 업로드 ---
    with tab2:
        st.markdown("#### KICE 형식 JSON 파일 업로드")
        st.info(
            "KICE_slayer_AI_Korean 형식의 JSON 파일을 직접 업로드하여 가져올 수 있습니다. "
            "다른 연도 데이터를 별도로 확보한 경우 여기서 업로드하세요."
        )

        uploaded = st.file_uploader(
            "JSON 파일 선택",
            type=["json"],
            key="kice_json_upload"
        )

        if uploaded:
            try:
                content = uploaded.read().decode("utf-8")
                kice_data = json.loads(content)

                if not isinstance(kice_data, list):
                    st.error("올바른 KICE 형식이 아닙니다. 최상위가 배열(list)이어야 합니다.")
                else:
                    # 미리보기
                    total_problems = sum(len(s.get("problems", [])) for s in kice_data)
                    total_sections = len(kice_data)
                    categories = set()
                    for s in kice_data:
                        categories.add(TYPE_TO_CATEGORY.get(s.get("type", 0), "독서"))

                    col1, col2, col3 = st.columns(3)
                    col1.metric("지문 수", total_sections)
                    col2.metric("문항 수", total_problems)
                    col3.metric("영역", ", ".join(categories))

                    st.markdown("**파일명으로 연도 정보가 추출됩니다** (예: `2024_11_KICE.json`)")
                    custom_name = st.text_input(
                        "파일명 (연도_월_KICE.json 형식)",
                        value=uploaded.name,
                        key="kice_custom_filename"
                    )

                    if st.button("가져오기", key="upload_import", use_container_width=True):
                        with st.spinner("변환 및 저장 중..."):
                            result = import_from_local_json(kice_data, custom_name)
                        if result["success"]:
                            stats = result["stats"]
                            st.success(
                                f"가져오기 완료! "
                                f"지문 {stats['passages']}개, "
                                f"문항 {stats['questions']}개, "
                                f"총점 {stats['total_score']}점 "
                                f"(ID: `{result['file_id']}`)"
                            )
                            st.rerun()
                        else:
                            st.error(f"가져오기 실패: {result.get('error', '알 수 없는 오류')}")
            except json.JSONDecodeError:
                st.error("JSON 파싱 오류입니다. 올바른 JSON 파일인지 확인해주세요.")

    # --- 탭 3: 문제은행 현황 ---
    with tab3:
        st.markdown("#### 문제은행 현황")

        db = get_db()
        bank_items = [d for d in db if d.get("source") == "KICE_slayer_AI_Korean"]

        if not bank_items:
            st.info("아직 문제은행에 가져온 데이터가 없습니다. 'KICE 기출 가져오기' 탭에서 데이터를 가져오세요.")
        else:
            # 통계 요약
            total_q = 0
            total_p = 0
            for item in bank_items:
                fdata = load_json_data(item["file_id"])
                if fdata:
                    total_q += len(fdata.get("questions", []))
                    total_p += len(fdata.get("passages", []))

            col1, col2, col3 = st.columns(3)
            col1.metric("시험지 수", len(bank_items))
            col2.metric("총 지문 수", total_p)
            col3.metric("총 문항 수", total_q)

            st.markdown("---")

            for item in sorted(bank_items, key=lambda x: x.get("year", ""), reverse=True):
                fdata = load_json_data(item["file_id"])
                if not fdata:
                    continue

                questions = fdata.get("questions", [])
                passages = fdata.get("passages", [])
                year = item.get("year", "?")
                month = item.get("month", "?")

                with st.expander(f"{year}학년도 {month}월 수능 국어 — 지문 {len(passages)}개 / 문항 {len(questions)}개", expanded=False):
                    # 카테고리별 통계
                    cat_counts = {}
                    for q in questions:
                        cat = q.get("category", "기타")
                        cat_counts[cat] = cat_counts.get(cat, 0) + 1

                    cat_cols = st.columns(len(cat_counts))
                    for i, (cat, cnt) in enumerate(cat_counts.items()):
                        cat_cols[i].metric(cat, f"{cnt}문항")

                    st.markdown("---")

                    # 문항 목록
                    for q in sorted(questions, key=lambda x: int(x.get("q_num", 0)) if str(x.get("q_num", 0)).isdigit() else 0):
                        q_num = q.get("q_num", "?")
                        stem = q.get("q_stem", "")[:80]
                        cat = q.get("category", "")
                        answer = q.get("answer", "")
                        score = q.get("score", "")
                        ans_str = f" | 정답: {answer}" if answer else ""
                        score_str = f" | {score}점" if score else ""

                        st.markdown(
                            f"**{q_num}번** ({cat}{score_str}{ans_str}) — {stem}..."
                        )
