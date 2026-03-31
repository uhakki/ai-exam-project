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
def get_status_badge(status: str) -> str:
    config = {
        "Ready": ("ready", "대기"),
        "Extracting": ("processing", "추출중"),
        "Verifying": ("processing", "검증중"),
        "Converting": ("processing", "변환중"),
        "Extracted": ("success", "추출완료"),
        "Modified": ("warning", "수정됨"),
        "Done": ("success", "완료"),
        "Stopped": ("warning", "중단"),
        "Stopping": ("warning", "중단중"),
        "Error": ("error", "오류")
    }
    style, label = config.get(status, ("ready", status))
    return f'<span class="badge badge-{style}">{label}</span>'


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

        # 최근 작업 목록
        st.markdown("### 최근 작업")

        recent = df.sort_values('last_updated', ascending=False).head(10)

        status_kr = {
            "Ready": "대기", "Extracting": "추출중", "Verifying": "검증중",
            "Converting": "변환중", "Extracted": "추출완료", "Modified": "수정됨",
            "Done": "완료", "Stopped": "중단", "Stopping": "중단중", "Error": "오류"
        }

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
                "문서": doc_info,
                "파일명": row.get('filename', '-'),
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
                "문서": st.column_config.TextColumn("문서", width="medium"),
                "파일명": st.column_config.TextColumn("파일명", width="medium"),
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
            exam_type = st.selectbox("시험 유형", ["", "모의고사", "수능", "중간고사", "기말고사", "기타"])
            grade = st.selectbox("학년", ["", "고1", "고2", "고3", "중1", "중2", "중3"])

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

        for item in reversed(filtered):
            status = item['status']
            file_id = item['file_id']
            progress = item.get('progress', 0)

            is_active = status in ['Extracting', 'Verifying', 'Converting', 'Stopping']

            title = f"{item.get('subject', item['filename'])} | {item['filename']}"

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
                            btn_text = "추출 시작" if status == 'Ready' else "추출 재개"
                            if st.button(btn_text, key=f"ext_{file_id}", type="primary", use_container_width=True):
                                run_thread(task_extract_json, (file_id, item['filepath'], item))
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
        options = {f"{item.get('subject', item['filename'])} ({item['filename']})": item['file_id'] for item in editable}
        selected_doc = st.selectbox("문서 선택", list(options.keys()))
        file_id = options[selected_doc]

        data = load_json_data(file_id)

        if data:
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
                st.rerun()
        else:
            st.error("데이터를 불러올 수 없습니다.")


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
        options = {f"{item.get('subject', item['filename'])} ({item['filename']})": item['file_id'] for item in viewable}
        selected_doc = st.selectbox("문서 선택", list(options.keys()))
        file_id = options[selected_doc]

        data = load_json_data(file_id)

        if data:
            meta = data.get("meta", {})
            questions = data.get("questions", [])
            passages = data.get("passages", [])

            # 문서 정보
            badge_class = 'success' if meta.get('verified_at') else 'ready'
            badge_text = 'AI 검증완료' if meta.get('verified_at') else '미검증'
            doc_info_html = f'<div class="content-card"><div style="display:flex;justify-content:space-between;align-items:center;"><div><h3 style="margin:0;color:#212529;">{meta.get("subject", "제목 없음")}</h3><p style="margin:0.5rem 0 0 0;color:#6c757d;font-size:0.875rem;">{meta.get("exam_type", "")} {meta.get("year", "")} {meta.get("grade", "")}</p></div><div style="text-align:right;"><span class="badge badge-{badge_class}">{badge_text}</span><p style="margin:0.5rem 0 0 0;color:#6c757d;font-size:0.75rem;">문항 {len(questions)}개 | 지문 {len(passages)}개</p></div></div></div>'
            st.markdown(doc_info_html, unsafe_allow_html=True)

            import re
            import html as html_lib  # HTML 이스케이프용

            def escape_html(text):
                """HTML 특수문자 이스케이프 (단, 이미 있는 HTML 태그는 유지하지 않음)"""
                if not text:
                    return ""
                return html_lib.escape(str(text))

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
                for q in sorted(questions, key=lambda x: x.get('q_num', 0)):
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
                    for q in sorted(orphan_questions, key=lambda x: x.get('q_num', 0)):
                        choices_html = "".join([f'<div class="exam-choice">{escape_html(q.get(f"choice_{i}", ""))}</div>' for i in range(1, 6) if q.get(f'choice_{i}')])
                        ref_content = escape_html(q.get("reference_box", "")).replace('\n', '<br/>') if q.get('reference_box') else ""
                        ref_html = f'<div class="exam-q-ref"><strong>&lt;보기&gt;</strong><br/>{ref_content}</div>' if ref_content else ""
                        q_stem = escape_html(q.get('q_stem', '')).replace('\n', '<br/>')
                        orphan_parts.append(f'<div class="exam-q"><span class="exam-q-num">{q.get("q_num", "?")}</span><div class="exam-q-stem">{q_stem}</div>{ref_html}<div class="exam-choices">{choices_html}</div></div>')
                    orphan_parts.append('</div></div>')
                    st.markdown(''.join(orphan_parts), unsafe_allow_html=True)

            # === 문항별 뷰 ===
            elif view_mode == "문항별":
                for q in sorted(questions, key=lambda x: x.get('q_num', 0)):
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
        else:
            st.error("데이터를 불러올 수 없습니다.")

# =============================================================================
# 6. 시험지구성
# =============================================================================
elif selected == "시험지구성":
    from exam_pdf_generator import generate_exam_pdf, ExamPaperConfig

    st.markdown('<div class="page-header"><div class="page-title">시험지구성</div><div class="page-desc">문항을 선택하여 시험지 PDF를 생성합니다</div></div>', unsafe_allow_html=True)

    # 세션 상태 초기화
    if 'exam_selected_questions' not in st.session_state:
        st.session_state.exam_selected_questions = []  # [{id, file_id, question_data(원본 dict)}]
    if 'exam_passages_cache' not in st.session_state:
        st.session_state.exam_passages_cache = {}  # {file_id: passages_list}
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
            st.markdown("""
            <div style="background:#f8f9fa;padding:0.75rem;border-radius:8px;font-size:0.8rem;color:#6c757d;">
            수능/모의고사 스타일 2단 레이아웃.<br/>
            지문과 문항이 함께 배치됩니다.
            </div>
            """, unsafe_allow_html=True)
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
            file_options = {}
            for item in available_docs:
                label = f"{item.get('subject', '제목없음')} - {item.get('exam_type', '')} ({item['file_id']})"
                file_options[label] = item['file_id']

            selected_file = st.selectbox("문서 선택", list(file_options.keys()), key="exam_file_select")

            if selected_file:
                file_id = file_options[selected_file]
                data = load_json_data(file_id)

                if data:
                    questions = data.get("questions", [])
                    passages = data.get("passages", [])

                    # passages 캐시 (PDF 생성 시 사용)
                    st.session_state.exam_passages_cache[file_id] = passages

                    # 카테고리 필터
                    categories = list(set([q.get('category', '기타') for q in questions]))
                    selected_category = st.selectbox("카테고리 필터", ["전체"] + categories, key="exam_category_filter")

                    filtered_questions = questions if selected_category == "전체" else [q for q in questions if q.get('category') == selected_category]

                    st.markdown(f"**{len(filtered_questions)}개 문항**")

                    for q_idx, q in enumerate(sorted(filtered_questions, key=lambda x: int(x.get('q_num', 0)) if str(x.get('q_num', 0)).isdigit() else 0)):
                        q_num = q.get('q_num', '?')
                        q_stem = q.get('q_stem', '')[:50] + "..." if len(q.get('q_stem', '')) > 50 else q.get('q_stem', '')
                        q_category = q.get('category', '')
                        q_page = q.get('page_num', 0)

                        q_id = f"{file_id}_{q_page}_{q_num}_{q_idx}"
                        is_selected = any(sq['id'] == q_id for sq in st.session_state.exam_selected_questions)

                        col_a, col_b = st.columns([4, 1])
                        with col_a:
                            st.markdown(f"<div style='padding:0.5rem;background:#f8f9fa;border-radius:4px;margin-bottom:0.5rem;font-size:0.85rem;color:#212529;'><strong>{q_num}번</strong> <span style='color:#6c757d;'>({q_category})</span><br/>{q_stem}</div>", unsafe_allow_html=True)
                        with col_b:
                            if is_selected:
                                st.markdown("<span style='color:#28a745;'>선택됨</span>", unsafe_allow_html=True)
                            else:
                                if st.button("추가", key=f"add_{q_id}"):
                                    # 문항 원본 dict 그대로 저장 (passage_id 포함)
                                    st.session_state.exam_selected_questions.append({
                                        'id': q_id,
                                        'file_id': file_id,
                                        'question_data': q,
                                    })
                                    st.rerun()
        else:
            st.info("추출된 문서가 없습니다. 먼저 데이터 처리를 진행해주세요.")

        st.markdown('</div>', unsafe_allow_html=True)

    # 오른쪽: 선택된 문항
    with right_col:
        st.markdown('<div class="content-card"><h4 style="margin:0 0 1rem 0;color:#212529;">선택된 문항</h4>', unsafe_allow_html=True)

        if st.session_state.exam_selected_questions:
            st.markdown(f"**{len(st.session_state.exam_selected_questions)}개 문항 선택됨**")

            for idx, sq in enumerate(st.session_state.exam_selected_questions):
                qd = sq['question_data']
                col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                with col_a:
                    q_stem_short = (qd.get('q_stem', '') or '')[:40]
                    if len(qd.get('q_stem', '') or '') > 40:
                        q_stem_short += "..."
                    st.markdown(f"<div style='padding:0.5rem;background:#e3f2fd;border-radius:4px;font-size:0.85rem;color:#212529;'><strong>{idx+1}.</strong> ({qd.get('q_num','?')}번) {q_stem_short}</div>", unsafe_allow_html=True)
                with col_b:
                    if idx > 0:
                        if st.button("^", key=f"up_{sq['id']}"):
                            st.session_state.exam_selected_questions[idx], st.session_state.exam_selected_questions[idx-1] = st.session_state.exam_selected_questions[idx-1], st.session_state.exam_selected_questions[idx]
                            st.rerun()
                with col_c:
                    if idx < len(st.session_state.exam_selected_questions) - 1:
                        if st.button("v", key=f"down_{sq['id']}"):
                            st.session_state.exam_selected_questions[idx], st.session_state.exam_selected_questions[idx+1] = st.session_state.exam_selected_questions[idx+1], st.session_state.exam_selected_questions[idx]
                            st.rerun()
                with col_d:
                    if st.button("x", key=f"remove_{sq['id']}"):
                        st.session_state.exam_selected_questions.pop(idx)
                        st.rerun()

            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

            if st.button("전체 삭제", key="clear_all"):
                st.session_state.exam_selected_questions = []
                st.rerun()
        else:
            st.info("왼쪽에서 문항을 선택해주세요.")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # 하단: 미리보기 & PDF 생성
    st.markdown('<div class="content-card"><h4 style="margin:0 0 1rem 0;color:#212529;">미리보기 & 출력</h4>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        preview_btn = st.button("시험지 미리보기", use_container_width=True)
    with col2:
        pdf_btn = st.button("PDF 생성 (2단 수능형)", use_container_width=True, type="primary", disabled=len(st.session_state.exam_selected_questions) == 0)

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
            points_html = f' <span style="color:#d93025;">[{qd["points"]}점]</span>' if qd.get('points') else ''
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

            # 선택된 문항의 question_data 리스트 추출
            selected_q_list = [sq['question_data'] for sq in st.session_state.exam_selected_questions]

            # 관련 passages 수집 (캐시 + 필요시 재로드)
            all_passages = []
            seen_file_ids = set(sq['file_id'] for sq in st.session_state.exam_selected_questions)
            for fid in seen_file_ids:
                if fid in st.session_state.exam_passages_cache:
                    all_passages.extend(st.session_state.exam_passages_cache[fid])
                else:
                    fdata = load_json_data(fid)
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
