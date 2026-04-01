"""
exam_pdf_generator.py
수능형 2단 시험지 PDF 생성 모듈

- 수능/모의고사 스타일 2단 레이아웃
- passage_id 기반 지문-문항 그룹핑
- BaseDocTemplate + Frame + Canvas 직접 그리기
"""

import io
import os
import re
from dataclasses import dataclass, field
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate,
    Paragraph, Spacer, Table, TableStyle, KeepTogether, FrameBreak,
)


# =============================================================================
# 1. 폰트 등록
# =============================================================================

FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansKR-Regular.ttf')
FONT = 'Helvetica'  # fallback

def _register_fonts():
    """한글 폰트 등록"""
    global FONT
    if os.path.exists(FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont('NotoSansKR', FONT_PATH))
            FONT = 'NotoSansKR'
        except Exception:
            pass
    else:
        # Windows fallback
        import platform
        if platform.system() == "Windows":
            try:
                pdfmetrics.registerFont(TTFont('MalgunGothic', 'C:/Windows/Fonts/malgun.ttf'))
                FONT = 'MalgunGothic'
            except Exception:
                pass

_register_fonts()


# =============================================================================
# 2. 설정 및 상수
# =============================================================================

@dataclass
class ExamPaperConfig:
    # 수능/모의고사용
    title: str = "2026학년도 대학수학능력시험 문제지"
    subject: str = "국어 영역"
    session: str = "제1교시"
    form_type: str = "홀수형"
    total_questions: int = 0       # 0이면 자동 계산
    total_pages: int = 0           # 0이면 자동 계산

    # 내신용 (layout_type="school"일 때 사용)
    school_name: str = ""
    exam_name: str = ""
    grade: str = ""
    exam_date: str = ""
    time_limit: str = ""

    # 레이아웃 선택
    layout_type: str = "suneung"   # "suneung" | "school"


# 페이지 수치
PAGE_W, PAGE_H = A4  # 210mm × 297mm

MARGIN_LEFT = 10 * mm
MARGIN_RIGHT = 10 * mm
MARGIN_TOP = 12 * mm
MARGIN_BOTTOM = 10 * mm

GUTTER = 6 * mm
CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT  # 190mm
COL_W = (CONTENT_W - GUTTER) / 2  # ~92mm

FIRST_PAGE_HEADER_H = 35 * mm
NORMAL_HEADER_H = 18 * mm
FOOTER_H = 12 * mm

FRAME_Y = MARGIN_BOTTOM + FOOTER_H
FRAME_H_FIRST = PAGE_H - MARGIN_TOP - FIRST_PAGE_HEADER_H - FRAME_Y
FRAME_H_NORMAL = PAGE_H - MARGIN_TOP - NORMAL_HEADER_H - FRAME_Y

# 내신형 1단 전폭
SINGLE_COL_W = CONTENT_W  # ~190mm


# =============================================================================
# 3. ParagraphStyle 정의
# =============================================================================

def _build_styles():
    """수능형(2단) 스타일 딕셔너리 생성"""
    return {
        'passage_intro': ParagraphStyle(
            'passage_intro', fontName=FONT, fontSize=8.5, leading=12,
            alignment=TA_LEFT, spaceBefore=6, spaceAfter=4,
        ),
        'passage_body': ParagraphStyle(
            'passage_body', fontName=FONT, fontSize=8, leading=11.5,
            alignment=TA_JUSTIFY, firstLineIndent=8,
            spaceBefore=0, spaceAfter=0,
        ),
        'passage_body_no_indent': ParagraphStyle(
            'passage_body_no_indent', fontName=FONT, fontSize=8, leading=11.5,
            alignment=TA_LEFT, firstLineIndent=0,
            spaceBefore=0, spaceAfter=0,
        ),
        'question_stem': ParagraphStyle(
            'question_stem', fontName=FONT, fontSize=8.5, leading=12,
            alignment=TA_LEFT, spaceBefore=8, spaceAfter=3,
            leftIndent=0,
        ),
        'choice': ParagraphStyle(
            'choice', fontName=FONT, fontSize=8, leading=11,
            alignment=TA_LEFT, leftIndent=10, spaceBefore=1, spaceAfter=1,
        ),
        'box_title': ParagraphStyle(
            'box_title', fontName=FONT, fontSize=8, leading=11,
            alignment=TA_CENTER, spaceBefore=3, spaceAfter=3,
        ),
        'box_body': ParagraphStyle(
            'box_body', fontName=FONT, fontSize=7.5, leading=10.5,
            alignment=TA_LEFT, leftIndent=4, rightIndent=4,
            spaceBefore=2, spaceAfter=2,
        ),
        'points': ParagraphStyle(
            'points', fontName=FONT, fontSize=8, leading=11,
            alignment=TA_LEFT,
        ),
    }


def _build_school_styles():
    """내신형(1단) 스타일 — 폰트 크기 확대"""
    return {
        'passage_intro': ParagraphStyle(
            'school_passage_intro', fontName=FONT, fontSize=11, leading=16,
            alignment=TA_LEFT, spaceBefore=10, spaceAfter=6,
        ),
        'passage_body': ParagraphStyle(
            'school_passage_body', fontName=FONT, fontSize=10, leading=15,
            alignment=TA_JUSTIFY, firstLineIndent=10,
            spaceBefore=0, spaceAfter=0,
        ),
        'passage_body_no_indent': ParagraphStyle(
            'school_passage_body_ni', fontName=FONT, fontSize=10, leading=15,
            alignment=TA_LEFT, firstLineIndent=0,
            spaceBefore=0, spaceAfter=0,
        ),
        'question_stem': ParagraphStyle(
            'school_question_stem', fontName=FONT, fontSize=11, leading=16,
            alignment=TA_LEFT, spaceBefore=12, spaceAfter=4,
            leftIndent=0,
        ),
        'choice': ParagraphStyle(
            'school_choice', fontName=FONT, fontSize=10, leading=14,
            alignment=TA_LEFT, leftIndent=14, spaceBefore=2, spaceAfter=2,
        ),
        'box_title': ParagraphStyle(
            'school_box_title', fontName=FONT, fontSize=10, leading=14,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=4,
        ),
        'box_body': ParagraphStyle(
            'school_box_body', fontName=FONT, fontSize=9.5, leading=14,
            alignment=TA_LEFT, leftIndent=6, rightIndent=6,
            spaceBefore=3, spaceAfter=3,
        ),
        'points': ParagraphStyle(
            'school_points', fontName=FONT, fontSize=10, leading=14,
            alignment=TA_LEFT,
        ),
    }


STYLES = _build_styles()
SCHOOL_STYLES = _build_school_styles()


# =============================================================================
# 4. 텍스트 전처리
# =============================================================================

def escape_xml(text):
    """XML 특수문자 이스케이프 (reportlab Paragraph용)"""
    if not text:
        return ''
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def preprocess_passage(text):
    """지문/문항 텍스트를 Paragraph-safe HTML로 변환"""
    if not text:
        return ''
    # 먼저 XML 이스케이프
    text = escape_xml(text)
    # (가), (나) 등 소제목 굵게 처리
    text = re.sub(r'(\([가-힣]\))', r'<b>\1</b>', text)
    # 줄바꿈 처리
    text = text.replace('\n', '<br/>')
    return text


# =============================================================================
# 5. 헤더/푸터 Canvas 그리기
# =============================================================================

def draw_first_page(canvas, doc, config):
    """1페이지 헤더 + 공통 푸터"""
    canvas.saveState()

    page_w, page_h = A4
    cx = page_w / 2

    # --- 제목 ---
    canvas.setFont(FONT, 11)
    canvas.drawCentredString(cx, page_h - MARGIN_TOP - 8 * mm, config.title)

    # --- 우상단 페이지 번호 ---
    canvas.setFont(FONT, 18)
    canvas.drawRightString(page_w - MARGIN_RIGHT, page_h - MARGIN_TOP - 10 * mm, "1")

    # --- 교시 (좌측, 타원) ---
    session_x = MARGIN_LEFT + 25 * mm
    session_y = page_h - MARGIN_TOP - 25 * mm
    canvas.setFont(FONT, 10)
    canvas.roundRect(
        session_x - 15 * mm, session_y - 4 * mm,
        30 * mm, 12 * mm, 5 * mm, stroke=1, fill=0
    )
    canvas.drawCentredString(session_x, session_y, config.session)

    # --- 영역명 (중앙, 큰 글씨) ---
    canvas.setFont(FONT, 24)
    canvas.drawCentredString(cx, session_y, config.subject)

    # --- 형번호 (우측, 박스) ---
    form_x = page_w - MARGIN_RIGHT - 25 * mm
    canvas.setFont(FONT, 10)
    canvas.roundRect(
        form_x - 15 * mm, session_y - 4 * mm,
        30 * mm, 12 * mm, 3 * mm, stroke=1, fill=0
    )
    canvas.drawCentredString(form_x, session_y, config.form_type)

    # --- 구분선 ---
    line_y = page_h - MARGIN_TOP - FIRST_PAGE_HEADER_H + 2 * mm
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_LEFT, line_y, page_w - MARGIN_RIGHT, line_y)

    canvas.restoreState()
    draw_footer(canvas, doc, config)


def draw_normal_page(canvas, doc, config):
    """2페이지~ 헤더 + 공통 푸터"""
    canvas.saveState()

    page_w, page_h = A4
    page_num = doc.page
    cx = page_w / 2
    header_y = page_h - MARGIN_TOP - 12 * mm

    # 짝수/홀수 페이지 배치 차이
    if page_num % 2 == 0:
        left_text = str(page_num)
        right_text = config.form_type
    else:
        left_text = config.form_type
        right_text = str(page_num)

    canvas.setFont(FONT, 11)
    canvas.drawString(MARGIN_LEFT + 5 * mm, header_y, left_text)
    canvas.drawCentredString(cx, header_y, config.subject)
    canvas.drawRightString(page_w - MARGIN_RIGHT - 5 * mm, header_y, right_text)

    # 구분선
    line_y = page_h - MARGIN_TOP - NORMAL_HEADER_H + 2 * mm
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_LEFT, line_y, page_w - MARGIN_RIGHT, line_y)

    canvas.restoreState()
    draw_footer(canvas, doc, config)


def draw_footer(canvas, doc, config):
    """공통 푸터: 페이지번호 + 저작권"""
    canvas.saveState()

    page_w, page_h = A4
    page_num = doc.page

    # 페이지 번호 (중앙)
    canvas.setFont(FONT, 9)
    footer_y = MARGIN_BOTTOM + 4 * mm
    canvas.drawCentredString(page_w / 2, footer_y, f"{page_num}")

    # 저작권 문구 (하단 우측)
    canvas.setFont(FONT, 6.5)
    canvas.drawRightString(
        page_w - MARGIN_RIGHT,
        MARGIN_BOTTOM,
        "이 문제지에 관한 저작권은 한국교육과정평가원에 있습니다."
    )

    canvas.restoreState()


def draw_school_header(canvas, doc, config):
    """내신용 헤더"""
    canvas.saveState()

    page_w, page_h = A4
    cx = page_w / 2

    # 학교명
    canvas.setFont(FONT, 16)
    canvas.drawCentredString(cx, page_h - MARGIN_TOP - 10 * mm, config.school_name or "○○고등학교")

    # 시험명
    canvas.setFont(FONT, 13)
    canvas.drawCentredString(cx, page_h - MARGIN_TOP - 18 * mm, config.exam_name or "시험지")

    # 정보
    canvas.setFont(FONT, 9)
    info = f"과목: {config.subject}  |  학년: {config.grade}  |  시험일: {config.exam_date}  |  시간: {config.time_limit}"
    canvas.drawCentredString(cx, page_h - MARGIN_TOP - 26 * mm, info)

    # 구분선
    line_y = page_h - MARGIN_TOP - FIRST_PAGE_HEADER_H + 2 * mm
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_LEFT, line_y, page_w - MARGIN_RIGHT, line_y)

    canvas.restoreState()
    draw_school_footer(canvas, doc, config)


def draw_school_normal(canvas, doc, config):
    """내신용 2페이지~ 헤더"""
    canvas.saveState()

    page_w, page_h = A4
    page_num = doc.page
    cx = page_w / 2
    header_y = page_h - MARGIN_TOP - 12 * mm

    canvas.setFont(FONT, 10)
    canvas.drawString(MARGIN_LEFT + 5 * mm, header_y, str(page_num))
    canvas.drawCentredString(cx, header_y, config.subject)

    line_y = page_h - MARGIN_TOP - NORMAL_HEADER_H + 2 * mm
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_LEFT, line_y, page_w - MARGIN_RIGHT, line_y)

    canvas.restoreState()
    draw_school_footer(canvas, doc, config)


def draw_school_footer(canvas, doc, config):
    """내신용 푸터"""
    canvas.saveState()
    page_w = A4[0]
    canvas.setFont(FONT, 9)
    canvas.drawCentredString(page_w / 2, MARGIN_BOTTOM + 4 * mm, f"{doc.page}")
    canvas.restoreState()


# =============================================================================
# 6. Document 생성
# =============================================================================

def create_exam_document(output, config):
    """레이아웃 타입에 따라 2단(수능형) 또는 1단(내신형) BaseDocTemplate 생성"""

    frame_y = FRAME_Y

    if config.layout_type == "school":
        # ── 내신형: 1단 전폭 ──
        first_frame_h = FRAME_H_FIRST
        first_frame = Frame(
            MARGIN_LEFT, frame_y, SINGLE_COL_W, first_frame_h,
            id='first_single', showBoundary=0,
            leftPadding=4, rightPadding=4, topPadding=0, bottomPadding=0,
        )
        normal_frame_h = FRAME_H_NORMAL
        normal_frame = Frame(
            MARGIN_LEFT, frame_y, SINGLE_COL_W, normal_frame_h,
            id='normal_single', showBoundary=0,
            leftPadding=4, rightPadding=4, topPadding=0, bottomPadding=0,
        )

        first_page_template = PageTemplate(
            id='FirstPage',
            frames=[first_frame],
            onPage=lambda c, d: draw_school_header(c, d, config),
        )
        normal_page_template = PageTemplate(
            id='NormalPage',
            frames=[normal_frame],
            onPage=lambda c, d: draw_school_normal(c, d, config),
        )
    else:
        # ── 수능형: 2단 ──
        first_frame_h = FRAME_H_FIRST
        first_left = Frame(
            MARGIN_LEFT, frame_y, COL_W, first_frame_h,
            id='first_left', showBoundary=0,
            leftPadding=2, rightPadding=2, topPadding=0, bottomPadding=0,
        )
        first_right = Frame(
            MARGIN_LEFT + COL_W + GUTTER, frame_y, COL_W, first_frame_h,
            id='first_right', showBoundary=0,
            leftPadding=2, rightPadding=2, topPadding=0, bottomPadding=0,
        )
        normal_left = Frame(
            MARGIN_LEFT, frame_y, COL_W, FRAME_H_NORMAL,
            id='normal_left', showBoundary=0,
            leftPadding=2, rightPadding=2, topPadding=0, bottomPadding=0,
        )
        normal_right = Frame(
            MARGIN_LEFT + COL_W + GUTTER, frame_y, COL_W, FRAME_H_NORMAL,
            id='normal_right', showBoundary=0,
            leftPadding=2, rightPadding=2, topPadding=0, bottomPadding=0,
        )

        first_page_template = PageTemplate(
            id='FirstPage',
            frames=[first_left, first_right],
            onPage=lambda c, d: draw_first_page(c, d, config),
        )
        normal_page_template = PageTemplate(
            id='NormalPage',
            frames=[normal_left, normal_right],
            onPage=lambda c, d: draw_normal_page(c, d, config),
        )

    doc = BaseDocTemplate(
        output,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    doc.addPageTemplates([first_page_template, normal_page_template])

    return doc


# =============================================================================
# 7. 보기 박스 / 문항 블록 빌더
# =============================================================================

def build_reference_box(content_text, col_width, styles=None):
    """보기 박스를 Table Flowable로 생성"""
    styles = styles or STYLES
    inner_elements = []

    # 제목
    inner_elements.append(Paragraph('&lt;보 기&gt;', styles['box_title']))

    # 본문
    processed = preprocess_passage(content_text)
    inner_elements.append(Paragraph(processed, styles['box_body']))

    box_table = Table(
        [[inner_elements]],
        colWidths=[col_width - 8 * mm],
    )
    box_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, black),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    return box_table


def _build_question_elements(q_data, col_width, styles=None):
    """문항 1개의 Flowable 리스트 생성 (KeepTogether 없이)"""
    styles = styles or STYLES
    elements = []

    # 발문
    q_num = q_data.get('q_num', '?')
    q_stem = q_data.get('q_stem', '') or ''
    stem_text = f"<b>{q_num}.</b> {preprocess_passage(q_stem)}"
    points = q_data.get('score') or q_data.get('points')
    if points:
        stem_text += f" [{points}점]"
    elements.append(Paragraph(stem_text, styles['question_stem']))

    # 보기 박스
    ref = q_data.get('reference_box', '') or ''
    if ref.strip():
        elements.append(Spacer(1, 1.5 * mm))
        elements.append(build_reference_box(ref, col_width, styles))
        elements.append(Spacer(1, 1.5 * mm))

    # 선택지
    for i in range(1, 6):
        choice_text = q_data.get(f'choice_{i}', '') or ''
        if choice_text:
            elements.append(Paragraph(
                preprocess_passage(choice_text),
                styles['choice']
            ))

    elements.append(Spacer(1, 3 * mm))
    return elements


def build_question_block(q_data, col_width, styles=None):
    """문항 1개를 KeepTogether로 묶어 반환 (긴 보기는 풀어서 반환)"""
    elements = _build_question_elements(q_data, col_width, styles)

    ref = q_data.get('reference_box', '') or ''
    if len(ref) > 500:
        return elements
    else:
        return KeepTogether(elements)


# =============================================================================
# 8. 지문-문항 그룹핑
# =============================================================================

def _build_passage_map(all_passages):
    """passage_id별로 지문을 합쳐 dict 반환"""
    pid_pages = defaultdict(list)

    for p in all_passages:
        pid = p.get('passage_id')
        if pid:
            pid_pages[pid].append(p)

    result = {}
    for pid, pages in pid_pages.items():
        pages.sort(key=lambda x: x.get('page_num', 0))
        texts = []
        for p in pages:
            content = p.get('passage_content', '')
            if p.get('is_continued_from_prev') and texts:
                content = content.lstrip()
                if content.startswith('(이어서)'):
                    content = content[len('(이어서)'):].lstrip()
                texts.append(content)
            else:
                texts.append(content)
        result[pid] = '\n'.join(texts)

    return result


def _split_intro(full_text):
    """지문 텍스트에서 도입부와 본문 분리"""
    match = re.match(r'(\[[\d]+[~～][\d]+\][^\n]*)', full_text)
    if match:
        intro = match.group(1).strip()
        body = full_text[match.end():].strip()
        return intro, body
    return '', full_text


def group_questions_with_passages(selected_questions, all_passages):
    """선택된 문항들을 passage_id 기반으로 그룹핑"""
    passage_map = _build_passage_map(all_passages)

    groups = []
    current_pid = '__NONE__'

    for q in selected_questions:
        pid = q.get('passage_id') or None

        if pid and pid != current_pid:
            full_text = passage_map.get(pid, '')
            intro, body = _split_intro(full_text)
            groups.append({
                'type': 'passage_group',
                'passage_id': pid,
                'passage_text': body,
                'intro_text': intro,
                'questions': [q],
            })
            current_pid = pid

        elif pid and pid == current_pid:
            groups[-1]['questions'].append(q)

        else:
            groups.append({
                'type': 'standalone',
                'passage_id': None,
                'passage_text': '',
                'intro_text': '',
                'questions': [q],
            })
            current_pid = '__NONE__'

    return groups


# =============================================================================
# 9. Story 조립
# =============================================================================

def build_passage_group_flowables(group, col_width=None, styles=None):
    """지문 그룹을 Flowable 리스트로 변환"""
    col_width = col_width or COL_W
    styles = styles or STYLES
    elements = []

    # 도입부
    if group['intro_text']:
        elements.append(Paragraph(
            f"<b>{preprocess_passage(group['intro_text'])}</b>",
            styles['passage_intro']
        ))
        elements.append(Spacer(1, 2 * mm))

    # 지문 본문
    if group['passage_text']:
        paragraphs = group['passage_text'].split('\n\n')
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(
                    preprocess_passage(para.strip()),
                    styles['passage_body']
                ))
        elements.append(Spacer(1, 3 * mm))

    # 문항들
    for q in group['questions']:
        result = build_question_block(q, col_width, styles)
        if isinstance(result, list):
            elements.extend(result)
        else:
            elements.append(result)

    return elements


def build_story(groups, config):
    """그룹핑된 데이터를 Flowable 리스트로 변환"""
    story = []

    # 레이아웃별 스타일/폭 결정
    if config.layout_type == "school":
        styles = SCHOOL_STYLES
        col_width = SINGLE_COL_W
    else:
        styles = STYLES
        col_width = COL_W

    # 1페이지 후 NormalPage 템플릿으로 전환
    story.append(NextPageTemplate('NormalPage'))

    for group in groups:
        if group['type'] == 'passage_group':
            story.extend(build_passage_group_flowables(group, col_width, styles))
        else:
            for q in group['questions']:
                result = build_question_block(q, col_width, styles)
                if isinstance(result, list):
                    story.extend(result)
                else:
                    story.append(result)

    return story


# =============================================================================
# 10. 메인 생성 함수
# =============================================================================

def _build_custom_styles(fonts_cfg):
    """양식의 fonts 설정으로 동적 스타일 생성"""
    return {
        'passage_intro': ParagraphStyle(
            'cust_passage_intro', fontName=FONT,
            fontSize=fonts_cfg.get('stem_size', 11), leading=fonts_cfg.get('stem_leading', 16),
            alignment=TA_LEFT, spaceBefore=6, spaceAfter=4,
        ),
        'passage_body': ParagraphStyle(
            'cust_passage_body', fontName=FONT,
            fontSize=fonts_cfg.get('passage_size', 10), leading=fonts_cfg.get('passage_leading', 15),
            alignment=TA_JUSTIFY, firstLineIndent=fonts_cfg.get('passage_indent', 10) if hasattr(fonts_cfg, 'get') else 10,
            spaceBefore=0, spaceAfter=0,
        ),
        'passage_body_no_indent': ParagraphStyle(
            'cust_passage_body_ni', fontName=FONT,
            fontSize=fonts_cfg.get('passage_size', 10), leading=fonts_cfg.get('passage_leading', 15),
            alignment=TA_LEFT, firstLineIndent=0,
            spaceBefore=0, spaceAfter=0,
        ),
        'question_stem': ParagraphStyle(
            'cust_question_stem', fontName=FONT,
            fontSize=fonts_cfg.get('stem_size', 11), leading=fonts_cfg.get('stem_leading', 16),
            alignment=TA_LEFT, spaceBefore=fonts_cfg.get('before_question', 12), spaceAfter=3,
            leftIndent=0,
        ),
        'choice': ParagraphStyle(
            'cust_choice', fontName=FONT,
            fontSize=fonts_cfg.get('choice_size', 10), leading=fonts_cfg.get('choice_leading', 14),
            alignment=TA_LEFT, leftIndent=14,
            spaceBefore=fonts_cfg.get('choice_gap', 2), spaceAfter=fonts_cfg.get('choice_gap', 2),
        ),
        'box_title': ParagraphStyle(
            'cust_box_title', fontName=FONT,
            fontSize=fonts_cfg.get('box_title_size', 10), leading=fonts_cfg.get('box_title_size', 10) + 4,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=4,
        ),
        'box_body': ParagraphStyle(
            'cust_box_body', fontName=FONT,
            fontSize=fonts_cfg.get('box_body_size', 9.5), leading=fonts_cfg.get('box_body_size', 9.5) + 4.5,
            alignment=TA_LEFT, leftIndent=6, rightIndent=6,
            spaceBefore=3, spaceAfter=3,
        ),
        'points': ParagraphStyle(
            'cust_points', fontName=FONT,
            fontSize=fonts_cfg.get('choice_size', 10), leading=fonts_cfg.get('choice_leading', 14),
            alignment=TA_LEFT,
        ),
    }


def generate_exam_pdf(config, selected_questions, all_passages):
    """
    시험지 PDF를 생성하여 bytes로 반환.

    Args:
        config: ExamPaperConfig 인스턴스
        selected_questions: list[dict] — 선택된 문항 (순서대로)
        all_passages: list[dict] — 전체 지문

    Returns:
        bytes — PDF 파일 내용
    """
    buffer = io.BytesIO()

    doc = create_exam_document(buffer, config)
    groups = group_questions_with_passages(selected_questions, all_passages)
    story = build_story(groups, config)

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def generate_exam_pdf_from_template(template_config, selected_questions, all_passages):
    """
    양식 설정(template_config dict)으로 시험지 PDF 생성.
    template_config는 exam_templates.template_to_config()의 반환값.
    """
    # ExamPaperConfig 생성
    config = ExamPaperConfig(
        title=template_config.get("title", ""),
        subject=template_config.get("subject", "국어"),
        session=template_config.get("session", ""),
        form_type=template_config.get("form_type", ""),
        school_name=template_config.get("school_name", ""),
        exam_name=template_config.get("exam_name", ""),
        grade=template_config.get("grade", ""),
        exam_date=template_config.get("exam_date", ""),
        time_limit=template_config.get("time_limit", ""),
        layout_type=template_config.get("layout_type", "school"),
    )

    # 커스텀 마진 적용
    margins = template_config.get("margins", {})
    custom_margin_left = margins.get("left", 15) * mm
    custom_margin_right = margins.get("right", 15) * mm
    custom_margin_top = margins.get("top", 12) * mm
    custom_margin_bottom = margins.get("bottom", 10) * mm

    # 커스텀 스타일 생성
    fonts_cfg = {**template_config.get("fonts", {}), **template_config.get("spacing", {})}
    custom_styles = _build_custom_styles(fonts_cfg)

    # 단수에 따른 col_width 계산
    columns = template_config.get("columns", 1)
    content_w = PAGE_W - custom_margin_left - custom_margin_right
    if columns == 2:
        gutter = margins.get("gutter", 6) * mm
        col_width = (content_w - gutter) / 2
    else:
        col_width = content_w

    buffer = io.BytesIO()
    doc = create_exam_document(buffer, config)
    groups = group_questions_with_passages(selected_questions, all_passages)

    # 커스텀 스타일 + col_width로 story 생성
    story = []
    story.append(NextPageTemplate('NormalPage'))
    for group in groups:
        if group['type'] == 'passage_group':
            story.extend(build_passage_group_flowables(group, col_width, custom_styles))
        else:
            for q in group['questions']:
                result = build_question_block(q, col_width, custom_styles)
                if isinstance(result, list):
                    story.extend(result)
                else:
                    story.append(result)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# 테스트
# =============================================================================

if __name__ == '__main__':
    test_config = ExamPaperConfig(
        title="2026학년도 대학수학능력시험 문제지",
        subject="국어 영역",
        session="제1교시",
        form_type="홀수형",
    )

    test_passages = [
        {
            "passage_id": "P001",
            "page_num": 1,
            "category": "독서",
            "passage_content": "[1~3] 다음 글을 읽고 물음에 답하시오.\n\n글을 읽고 그 의미를 이해하는 독해에는 글의 유형이나 독서 흥미 등의 다양한 요소가 영향을 미칠 수 있다. 이를 고려하여 독해 능력을 복잡한 과정으로 설명한 연구가 많다. 하지만 고프와 동료 연구자들이 제시한 단순 관점은 독해 능력을 '해독'과 '언어 이해'로 단순화하여 설명한다.\n\n해독은 개별 단어를 인식하는 능력으로, 단어를 빠르고 정확히 소리 내어 읽기, 단어를 한눈에 식별하기 등을 포함한다. 언어 이해는 말로 듣거나 글로 읽은 내용의 의미를 파악하는 능력으로, 중심 내용 파악하기, 추론하기 등을 포함한다.\n\n단순 관점은 독해 능력을 해독과 언어 이해의 곱으로 나타낸다. 이에 따르면, 해독과 언어 이해는 독해 능력에 각각 독립적으로 기여하고 하나라도 0이면 독해 능력도 0이 된다. 단순 관점을 지지하는 연구자들은 해독과 언어 이해 두 요인이 독해 능력의 차이를 상당 부분 설명할 수 있다고 본다.",
            "is_continued_from_prev": False,
            "continues_to_next": False,
        }
    ]

    test_questions = [
        {
            "passage_id": "P001", "q_num": 1, "category": "독서",
            "q_stem": "윗글의 내용과 일치하지 않는 것은?",
            "reference_box": "",
            "choice_1": "① 단순 관점에 따르면 추론하기는 언어 이해에 해당한다.",
            "choice_2": "② 단순 관점은 해독의 발달과 언어 이해의 발달을 모두 고려하여 독자 유형을 나눈다.",
            "choice_3": "③ 단순 관점에 따르면 독해 능력이 발달되기 위해서는 말소리 듣기 경험에 앞서 독서 경험이 필요하다.",
            "choice_4": "④ 단순 관점은 해독과 언어 이해가 독해 능력에 끼치는 영향을 밝혀 독해 능력 연구의 기반을 마련하였다.",
            "choice_5": "⑤ 단순 관점과 달리, 독해에 영향을 주는 여러 요소를 고려하여 독해 능력을 복잡한 과정으로 설명한 연구들이 있다.",
            "points": None,
        },
        {
            "passage_id": "P001", "q_num": 2, "category": "독서",
            "q_stem": "단순 관점에 대한 비판으로 가장 적절한 것은?",
            "reference_box": "",
            "choice_1": "① 해독이 부족하여 글의 내용을 잘 이해하지 못하는 경우를 다루지 않았다.",
            "choice_2": "② 독해에서 어려움이 나타날 수 있음을 고려하지 않아 독해를 지나치게 단순화하였다.",
            "choice_3": "③ 독해 능력 발달에 있어 해독의 영향이 더 크다고 보아 언어 이해의 중요성을 고려하지 않았다.",
            "choice_4": "④ 해독 발달을 글을 통한 시각적 경험으로만 설명하여 청각적 경험의 필요성을 증명하지 못하였다.",
            "choice_5": "⑤ 해독과 언어 이해를 바탕으로 글의 의미를 이해하기까지의 사고 과정이 어떻게 이루어지는지 밝히지 않았다.",
            "points": None,
        },
        {
            "passage_id": "P001", "q_num": 3, "category": "독서",
            "q_stem": "윗글을 바탕으로 <보기>를 이해한 내용으로 적절하지 않은 것은?",
            "reference_box": "단순 관점을 지지하는 연구자 갑은 학생 A, B의 독해 능력을 분석하기 위한 활동을 진행하였다.\n\n◦ 소리 내어 단어 읽기: 학생 A는 활동 자료에 있는 단어를 빠르고 정확하게 소리 내어 읽었고 한눈에 잘 식별하였다. 학생 B는 활동 자료에 있는 단어를 올바르게 발음하지 못하였고 한눈에 식별하지 못하였다.\n\n◦ 중심 내용 파악하기: 학생 A는 활동 자료를 글로 읽을 때와 말로 들을 때 모두 중심 내용을 파악하지 못하였다. 학생 B는 활동 자료를 글로 읽을 때는 중심 내용을 파악하지 못했지만 말로 들을 때는 중심 내용을 파악하였다.",
            "choice_1": "① 갑은 학생 A가 해독은 발달되었지만, 중심 내용을 파악하지 못한 점에서 언어 이해가 부족하다고 생각하겠군.",
            "choice_2": "② 갑은 학생 A가 글자와 글자 소리에 대한 학습을 통해 개별 단어를 인식하는 능력이 발달되었다고 생각하겠군.",
            "choice_3": "③ 갑은 학생 A의 언어 이해가 구어 의사소통 경험뿐 아니라 글 읽기 경험을 통해서도 발달될 수 있다고 생각하겠군.",
            "choice_4": "④ 갑은 학생 B가 단어를 올바르게 발음하지는 못하지만, 글 읽기 경험을 통해 중심 내용은 파악할 수 있게 되었다고 생각하겠군.",
            "choice_5": "⑤ 갑은 학생 B가 단어를 한눈에 식별하지는 못하지만 말로 들은 활동 자료의 중심 내용을 파악할 수 있었던 것은, 해독 발달 전에 언어 이해가 발달되었기 때문이라고 생각하겠군.",
            "points": 3,
        },
        {
            "passage_id": None, "q_num": 4, "category": "문법",
            "q_stem": "다음 중 표준어로만 짝지어진 것은?",
            "reference_box": "",
            "choice_1": "① 가을걷이 / 가을갈이",
            "choice_2": "② 강남콩 / 강낭콩",
            "choice_3": "③ 고구마줄기 / 고구마순",
            "choice_4": "④ 눈두덩이 / 눈두덩",
            "choice_5": "⑤ 발가숭이 / 발가벗이",
            "points": None,
        },
    ]

    pdf_bytes = generate_exam_pdf(test_config, test_questions, test_passages)

    output_path = os.path.join(os.path.dirname(__file__), 'test_exam.pdf')
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)

    print(f"test_exam.pdf 생성 완료 ({len(pdf_bytes):,} bytes)")
