# AI 시험지 관리 시스템 - 전체 아키텍처 문서

> 최종 업데이트: 2026-03-09

---

## 1. 시스템 개요

한국 고등학교 국어 시험지(수능/모의고사/내신)를 PDF로 업로드하면, AI가 지문과 문항을 자동 추출하여 구조화된 데이터로 변환하고, 이를 기반으로 새로운 시험지를 구성할 수 있는 웹 애플리케이션.

### 기술 스택
- **프론트엔드**: Streamlit (Python 기반 웹 UI)
- **백엔드**: Python (스레드 기반 비동기 작업)
- **AI 엔진**: Google Gemini 3 Pro (멀티모달 OCR + 구조 추출)
- **데이터베이스**: Firebase Firestore (문서 메타데이터)
- **파일 저장소**: Firebase Storage (PDF, JSON, JSONL, 로그, 엑셀)
- **PDF 처리**: PyMuPDF (PDF→이미지 변환), ReportLab (시험지 PDF 생성)
- **배포**: Streamlit Community Cloud

---

## 2. 파일 구조

```
국어문항시스템_신규개발/
├── app.py                  # Streamlit 웹 UI (6개 메뉴 페이지)
├── backend.py              # 핵심 작업 로직 (추출, 검증, 변환)
├── storage_backend.py      # Firebase 래퍼 (Firestore + Storage)
├── firebase_config.py      # Firebase Admin SDK 초기화
├── extractor.py            # Gemini AI 추출 모듈 (프롬프트 + API 호출)
├── pdf_processor.py        # PDF→PNG 이미지 변환 (PyMuPDF)
├── parser.py               # JSON→엑셀 변환
├── migrate_to_firebase.py  # 로컬→Firebase 1회성 마이그레이션
├── migrate_passage_ids.py  # passage_id 1회성 마이그레이션
├── requirements.txt        # Python 의존성
├── fonts/
│   └── NotoSansKR-Regular.ttf  # Linux용 한글 폰트 (PDF 생성)
└── .streamlit/
    └── secrets.toml        # API 키, Firebase 인증 (배포용)
```

---

## 3. 데이터 흐름

```
[PDF 업로드] → [Firebase Storage: inputs/]
      ↓
[AI 추출] → PDF→이미지(temp) → Gemini API → JSONL(체크포인트) → JSON(최종)
      ↓
[Firebase Storage: outputs/json/{file_id}.json]
      ↓
[문서 뷰어] ← JSON 로드 → 지문-문항 매핑 → 시험지/문항별/지문별 뷰
      ↓
[시험지구성] → 문항 선택 → ReportLab → PDF 다운로드
[엑셀 변환] → pandas → .xlsx 다운로드
```

---

## 4. 데이터 저장 구조

### 4-1. Firebase Firestore (`documents` 컬렉션)

각 문서(시험지)는 `file_id`를 키로 하는 Firestore 문서로 저장.

| 필드 | 타입 | 설명 |
|------|------|------|
| `file_id` | string | 8자리 UUID (고유 키) |
| `filename` | string | 원본 파일명 |
| `filepath` | string | Storage 경로 (`inputs/...`) |
| `subject` | string | 과목 (국어) |
| `year` | string | 연도 (2025) |
| `exam_type` | string | 시험유형 (모의고사/수능/중간고사/기말고사) |
| `grade` | string | 학년 (고1/고2/고3) |
| `month` | string | 월 (모의고사/수능) |
| `semester` | string | 학기 (중간/기말) |
| `school` | string | 학교명 |
| `author` | string | 출제자 |
| `status` | string | 상태 (아래 참조) |
| `progress` | int | 진행률 (0~100) |
| `current_page` | int | 현재 처리 페이지 |
| `total_pages` | int | 전체 페이지 수 |
| `ai_verified` | bool | AI 검증 완료 여부 |
| `excel_path` | string | 엑셀 파일 Storage 경로 |
| `error_msg` | string | 에러 메시지 |
| `last_updated` | string | 마지막 업데이트 시각 |

**상태 전이:**
```
Ready → Extracting → Extracted → Modified → Done
  ↑         ↓              ↓
  └── Stopped ←── Stopping
              ↓
            Error
```

### 4-2. Firebase Storage 구조

```
inputs/
  └── {file_id}_{원본파일명}.pdf     # 업로드된 원본 PDF

outputs/
  ├── json/
  │   ├── {file_id}.json             # 최종 구조화 데이터
  │   └── {file_id}_log.jsonl        # 페이지별 추출 체크포인트
  └── excel/
      └── {file_id}_{timestamp}.xlsx # 변환된 엑셀

logs/
  └── {file_id}.log                  # 실시간 처리 로그
```

### 4-3. JSON 데이터 구조 (핵심)

```json
{
  "meta": {
    "file_id": "abc12345",
    "subject": "국어",
    "year": "2025",
    "exam_type": "모의고사",
    "grade": "고3",
    "month": "6",
    "created_at": "2025-06-15 14:30:00",
    "modified_at": "2025-06-15 15:00:00",
    "verified_at": "2025-06-15 15:30:00"
  },
  "passages": [
    {
      "passage_id": "P001",
      "page_num": 2,
      "category": "화법과작문",
      "passage_content": "(가) 학생의 발표...",
      "is_continued_from_prev": false,
      "continues_to_next": false
    },
    {
      "passage_id": "P001",
      "page_num": 3,
      "category": "화법과작문",
      "passage_content": "(이어서) ...",
      "is_continued_from_prev": true,
      "continues_to_next": false
    }
  ],
  "questions": [
    {
      "passage_id": "P001",
      "page_num": 2,
      "q_num": 1,
      "category": "화법과작문",
      "q_stem": "윗글에 대한 설명으로 적절한 것은?",
      "reference_box": "",
      "choice_1": "① 선지1",
      "choice_2": "② 선지2",
      "choice_3": "③ 선지3",
      "choice_4": "④ 선지4",
      "choice_5": "⑤ 선지5",
      "ai_note": ""
    },
    {
      "passage_id": null,
      "page_num": 10,
      "q_num": 15,
      "category": "문법",
      "q_stem": "다음 중 밑줄 친 단어의 품사가...",
      "...": "..."
    }
  ],
  "verification_notes": [
    { "page": 5, "note": "14번 문항의 선지 ③이 잘림" }
  ]
}
```

#### passage_id 연결 규칙 (2026-03-09 추가)

| 상황 | passage_id 값 |
|------|---------------|
| 지문이 있는 문항 | `"P001"`, `"P002"` 등 순차 부여 |
| 여러 페이지에 걸친 지문 | 동일 `passage_id` 공유 (`is_continued_from_prev=true`) |
| 독립 문항 (지문 없음) | `null` |

---

## 5. 모듈별 상세

### 5-1. `extractor.py` — AI 추출 엔진

- **모델**: Gemini 3 Pro Preview (`gemini-3-pro-preview`)
- **설정**: `temperature=0`, `response_mime_type="application/json"`
- **프롬프트**: 시험지 이미지 1페이지를 입력받아 아래 구조를 JSON 배열로 출력
  ```
  [{category, passage_content, is_continued_from_prev, continues_to_next,
    related_questions: [{q_num, q_stem, reference_box, choice_1~5}]}]
  ```
- **재시도**: Tenacity 라이브러리로 exponential backoff (4초→8초→16초, 최대 3회)
- **JSON 복구**: `json_repair` 라이브러리로 깨진 JSON 자동 복구
- **영역 분류**: 화법과작문, 문법, 독서, 문학 4개 카테고리

### 5-2. `backend.py` — 작업 로직

| 함수 | 역할 |
|------|------|
| `task_extract_json()` | PDF 전체 페이지 추출 (메인 작업) |
| `_save_final_json()` | JSONL → 최종 JSON 변환 + passage_id 부여 |
| `_reassign_passage_ids()` | 재추출 후 passage_id 재정렬 |
| `task_reextract_pages()` | 특정 페이지만 재추출하여 기존 JSON에 병합 |
| `task_multimodal_verification()` | AI가 원본 이미지와 추출 JSON 비교 검증 |
| `task_generate_excel()` | JSON → 엑셀 변환 (지문_DB, 문항_DB 시트) |
| `update_json_manual()` | 프론트엔드 수동 편집 반영 |
| `request_stop()` / `reset_data()` | 작업 중단 / 데이터 초기화 |

**체크포인트 시스템**: 페이지별 추출 결과를 JSONL에 즉시 저장. 중단 후 재개 시 이미 처리된 페이지를 건너뜀.

### 5-3. `storage_backend.py` — Firebase 래퍼

로컬 파일 시스템 함수를 Firebase로 1:1 대체하는 래퍼 모듈.

| 카테고리 | 함수 | 설명 |
|---------|------|------|
| Firestore | `get_db()` | 전체 문서 목록 조회 |
| | `get_item_by_id()` | 단일 문서 조회 |
| | `save_entry()` | 새 문서 등록 |
| | `update_db_status()` | 상태/진행률 업데이트 |
| Storage | `upload_file()` / `upload_bytes()` | 파일 업로드 |
| | `download_file()` / `download_to_bytes()` | 파일 다운로드 |
| 로그 | `write_log()` / `read_log()` | 실시간 로그 읽기/쓰기 |
| JSON | `save_json_data()` / `load_json_data()` | JSON 저장/로드 |
| JSONL | `append_jsonl()` / `load_jsonl()` | 체크포인트 저장/로드 |

### 5-4. `app.py` — Streamlit UI (6개 메뉴)

| 메뉴 | 기능 |
|------|------|
| **대시보드** | 전체 문서 통계 (전체/대기/처리중/완료/오류), 최근 작업 목록 테이블 |
| **파일 업로드** | PDF 업로드 + 메타정보 입력 (연도, 과목, 시험유형, 학년 등) |
| **데이터 처리** | 추출 시작/재개, AI 검증, 페이지 재추출, 엑셀 생성, 실시간 로그 |
| **데이터 편집** | 문항/지문/메타정보 데이터 에디터 (행 삽입/삭제/수정) |
| **문서 뷰어** | 3가지 보기 모드 — 시험지, 문항별, 지문별 |
| **시험지구성** | 문서에서 문항 선택 → 순서 조정 → 미리보기 → PDF 생성/다운로드 |

---

## 6. 지문-문항 매칭 시스템

### 6-1. passage_id 부여 (추출 시)

`_save_final_json()`에서 JSONL의 계층 구조를 활용:

```
JSONL entry → data[] → item (passage_content + related_questions[])
```

1. entries를 `page_num` 순 정렬
2. 각 item에 대해:
   - `passage_content`가 있으면 → `passage_counter++` → `"P{counter:03d}"` 부여
   - `is_continued_from_prev=True`이면 → 이전 passage_id 재사용
   - `passage_content`가 없으면 → `passage_id = null` (독립 문항)
3. 같은 item 내 `related_questions`는 동일 `passage_id` 연결

### 6-2. 문서 뷰어 매칭 (`build_passage_question_map()`)

3단계 매칭 전략:
1. **passage_id 기반** (1차): 역색인으로 O(1) 직접 매칭
2. **문항 범위 매칭** (2차 fallback): 지문 텍스트에서 `(1~3)`, `[17~20]` 패턴 파싱
3. **page_num 매칭** (3차 fallback): 같은 페이지의 지문에 연결 (하위호환)

### 6-3. 시험지구성 매칭

문항 선택 시 passage_id로 지문을 먼저 찾고, 없으면 page_num으로 fallback:
```python
passage = (passage_id 매칭) or (page_num 매칭)
```

### 6-4. 재추출 시 passage_id 재정렬

`task_reextract_pages()` 후 `_reassign_passage_ids()` 호출:
- 새로 추출된 passages에 `passage_id=None` 임시 부여
- 기존 + 새 passages를 `page_num` 순 정렬
- 전체에 대해 P001부터 순차 재부여
- questions의 old→new 매핑 업데이트

---

## 7. 시험지 생성 (PDF)

### 처리 과정
1. 사용자가 여러 문서에서 문항을 선택 (좌측 패널)
2. 선택된 문항 순서 조정 (위/아래 이동, 삭제)
3. 시험지 정보 입력 (학교명, 시험명, 과목, 학년, 시험일, 시간)
4. 미리보기: HTML로 즉시 렌더링
5. PDF 생성: ReportLab으로 A4 시험지 생성

### PDF 생성 상세
- **라이브러리**: ReportLab (`SimpleDocTemplate`, `Paragraph`, `Spacer`)
- **폰트**: Windows→맑은 고딕, Linux→Noto Sans KR (번들)
- **레이아웃**: A4, 좌우 20mm 마진
- **구성**: 헤더(학교명, 시험명, 정보) → 문항(번호, 발문, 보기, 선지)

---

## 8. 인증 및 배포

### Firebase 인증
- **Streamlit Cloud**: `st.secrets["firebase"]`에 서비스 계정 JSON 필드 저장
- **로컬**: `firebase_credentials.json` 파일
- **API 키**: `st.secrets["GOOGLE_API_KEY"]` 또는 `.env` 파일

### 배포 (Streamlit Community Cloud)
1. GitHub 리포지토리 연결: `lhc4815/koreanexam-system`
2. `requirements.txt`로 의존성 자동 설치
3. Streamlit Secrets에 Firebase 인증 + API 키 설정
4. 자동 배포 (main 브랜치 푸시 시)

---

## 9. 주요 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| streamlit | >=1.28.0 | 웹 UI 프레임워크 |
| google-generativeai | >=0.3.0 | Gemini AI API |
| firebase-admin | >=6.2.0 | Firebase Firestore + Storage |
| pandas | >=2.0.0 | 데이터 처리, 엑셀 변환 |
| pymupdf | >=1.23.0 | PDF→이미지 변환 |
| reportlab | >=4.0.0 | 시험지 PDF 생성 |
| tenacity | >=8.2.0 | API 재시도 로직 |
| json_repair | >=0.28.0 | 깨진 JSON 자동 복구 |
| openpyxl | >=3.1.0 | 엑셀 파일 생성 |
