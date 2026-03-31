# 국어 문항 시스템 (Korean Exam PDF Processor)

국어 시험지 PDF에서 문항과 지문을 자동 추출하여 구조화된 데이터(JSON/Excel)로 변환하는 웹 애플리케이션입니다.

## 주요 기능

### 1. PDF 업로드 및 메타데이터 관리
- PDF 파일 업로드 시 고유 ID(8자리) 자동 생성
- 메타데이터 입력: 연도, 과목, 시험유형, 학년, 월, 학기, 학교명, 출제자

### 2. AI 기반 데이터 추출 (Step 1)
- Google Gemini API를 사용한 멀티모달 OCR
- 페이지별 처리로 안정성 확보
- 체크포인트 지원 (중단 후 재개 가능)
- 추출 항목: 지문, 문항번호, 발문, 보기, 선지(1~5)

### 3. AI 검증 (Step 1.5)
- 원본 이미지와 추출된 JSON 비교 검증
- 페이지 범위 지정 가능 (예: "14", "1-5", "3,5,7")
- 누락된 문항/지문 자동 감지
- 검증 결과는 `verification_notes`에 저장

### 4. 페이지 재추출
- 특정 페이지만 선택적으로 재추출
- 기존 데이터에서 해당 페이지 교체
- 검증에서 문제 발견 시 즉시 재처리 가능

### 5. 데이터 편집
- 추출된 문항/지문 수동 수정
- 행 삽입/삭제 기능 (행 편집 모드)
- 메타정보 편집 (개별 입력 필드)

### 6. 엑셀 변환 및 다운로드 (Step 2)
- JSON 데이터를 Excel 파일로 변환
- 다운로드 버튼 제공


## 폴더 구조

```
국어문항시스템_신규개발/
├── app.py              # Streamlit 웹 애플리케이션 (메인)
├── backend.py          # 백엔드 로직 (추출, 검증, 변환)
├── extractor.py        # Gemini API 추출 모듈
├── pdf_processor.py    # PDF to 이미지 변환
├── parser.py           # 데이터 파싱 유틸리티
├── database.json       # 파일 메타데이터 DB
├── .env                # API 키 설정
├── inputs/             # 업로드된 PDF 저장
├── outputs/
│   ├── json/           # 추출된 JSON 데이터
│   └── excel/          # 생성된 Excel 파일
├── logs/               # 처리 로그 (파일별)
└── temp/               # 임시 이미지 파일
```


## 설치 및 실행

### 1. 의존성 설치
```bash
pip install streamlit pandas openpyxl pymupdf google-generativeai tenacity json-repair python-dotenv
```

### 2. API 키 설정
`.env` 파일 생성:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. 실행
```bash
python -m streamlit run app.py --server.port 8501
```
브라우저에서 `http://localhost:8501` 접속


## 사용 방법

### 기본 워크플로우
1. **파일 등록**: PDF 업로드 + 메타데이터 입력
2. **데이터 처리**: "추출 시작" 버튼 클릭
3. **AI 검증**: 페이지 범위 입력 후 "AI 검증" 클릭
4. **재추출** (필요시): 문제 있는 페이지 번호 입력 후 "페이지 재추출"
5. **데이터 편집**: 수동 수정 및 누락 문항 추가
6. **엑셀 생성**: "엑셀 생성" 클릭 후 다운로드

### 페이지 범위 입력 형식
- `all` - 전체 페이지
- `14` - 14페이지만
- `1-5` - 1~5페이지
- `3,5,7` - 3, 5, 7페이지
- `1-3,7,10-12` - 혼합


## 주요 설정

### extractor.py
- `model_name`: Gemini 모델 (현재: gemini-3-pro-preview)
- `temperature`: 0 (저작권 회피를 위해 낮게 설정)

### backend.py
- 검증 모델: gemini-3-pro-preview (temperature: 0)


## 상태 흐름

```
Ready → Extracting → Extracted → Modified → Done
         ↓              ↓           ↓
      Stopped        Verifying   Converting
         ↓              ↓
       Error        Extracted
```

### 상태 설명 (한글)
| 영문 | 한글 | 설명 |
|------|------|------|
| Ready | 대기 | 추출 대기 중 |
| Extracting | 추출중 | AI 추출 진행 중 |
| Extracted | 추출완료 | 추출 완료 |
| Modified | 수정됨 | 사용자가 데이터 수정함 |
| Verifying | 검증중 | AI 검증 진행 중 |
| Converting | 변환중 | 엑셀 변환 중 |
| Done | 완료 | 엑셀 생성 완료 |
| Stopped | 중단 | 사용자 요청으로 중단 |
| Error | 오류 | 처리 중 오류 발생 |


## 오늘 작업 내역 (2025-12-17)

### 버그 수정
1. **Windows cp949 인코딩 오류** - 로그 메시지에서 이모지 제거, 텍스트 프리픽스로 대체
2. **메타정보 편집 불가** - data_editor의 disabled 파라미터 문제 → 개별 입력 필드로 변경
3. **엑셀 다운로드 버튼 미표시** - 조건문 들여쓰기 오류 수정
4. **사이드바 접기 버튼** - 펼치기 불가 문제 → 항상 펼침 상태로 고정

### 기능 추가
1. **행 편집 모드** - 체크박스로 토글, 행 삽입(위/아래)/삭제 기능
2. **검증 페이지 지정** - 특정 페이지만 검증 가능
3. **페이지 재추출** - 누락/오류 페이지만 재처리
4. **검증 로직 개선** - AI 자유 응답 방식으로 변경, 데이터 없는 페이지도 검증

### 프롬프트 개선
1. **저작권 회피 문구 추가** - 교육 목적의 단순 OCR 작업임을 명시
2. **temperature 0 설정** - 창의성 없이 그대로 추출하도록 설정


## 알려진 이슈

1. **저작권 오류** (finish_reason: 4)
   - 일부 페이지에서 Gemini가 저작권 콘텐츠로 인식
   - 해결: temperature=0 설정, 프롬프트에 OCR 작업 명시
   - 그래도 발생 시: 해당 페이지 건너뛰고 수동 입력

2. **로그 자동 새로고침**
   - 현재 미지원 (UI 안정성 문제로 제거됨)
   - 브라우저 새로고침으로 확인


## 라이선스

Private - 내부 사용 목적
