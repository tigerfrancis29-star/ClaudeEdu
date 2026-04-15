# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

영수증 이미지/PDF를 업로드하면 **Upstage Vision LLM**이 자동으로 OCR 파싱하여 지출 데이터를 관리하는 1일 스프린트 경량 웹앱입니다. DB 없이 JSON 파일 기반으로 동작합니다.

## 개발 명령어

### 백엔드 (Python FastAPI)

```bash
# 프로젝트 루트에서 실행 (backend가 Python 패키지로 등록됨)
backend/venv/Scripts/pip install -r backend/requirements.txt
backend/venv/Scripts/uvicorn backend.main:app --reload --port 8000
```

### 프론트엔드 (React + Vite)

```bash
cd frontend
npm install
npm run dev        # 개발 서버 (기본 포트 5173)
npm run build      # 프로덕션 빌드
npm run preview    # 빌드 결과 미리보기
```

### 환경변수 설정

`.env` 파일 (루트 또는 `backend/`)에 다음 변수가 필요합니다:
- `UPSTAGE_API_KEY` — Upstage Document AI API 키
- `VITE_API_BASE_URL` — 프론트엔드에서 사용하는 백엔드 API 기본 URL

## 프로젝트 디렉토리 구조

```
receipt-tracker/
├── frontend/                 # React + Vite + TailwindCSS
│   ├── src/
│   │   ├── pages/            # Dashboard, UploadPage, ExpenseDetail
│   │   ├── components/       # Badge, Modal, Toast, ProgressBar
│   │   └── api/              # Axios 인스턴스 (baseURL 설정)
│   ├── package.json
│   └── vite.config.js
├── backend/                  # Python FastAPI
│   ├── main.py               # FastAPI 앱 엔트리포인트
│   ├── routers/              # API 라우터 (upload, expenses, summary)
│   ├── services/             # LangChain + Upstage OCR 로직
│   ├── data/
│   │   └── expenses.json     # 누적 저장 데이터 (DB 대체)
│   └── requirements.txt
├── images/                   # 테스트용 영수증 샘플 이미지
├── vercel.json               # Vercel 배포 라우팅 설정
└── PRD_영수증_지출관리앱.md    # 상세 기능 요구사항 문서
```

## 아키텍처 핵심

### OCR 처리 흐름 (백엔드)

```
POST /api/upload (multipart/form-data)
  → 파일 형식/크기 검증 (JPG, PNG, PDF / 최대 10MB)
  → PIL 또는 pdf2image로 이미지 전처리 → Base64 인코딩
  → LangChain Chain 실행:
      ChatUpstage(model="document-digitization-vision")
      System Prompt: "JSON 형식으로만 응답"
      → LangChain OutputParser → 구조화 JSON
  → UUID 생성 후 backend/data/expenses.json에 append 저장
  → 파싱된 JSON 객체 반환
```

### 데이터 저장 방식

DB 없이 `backend/data/expenses.json`에 배열 형태로 누적 저장합니다. Vercel 서버리스 환경에서는 파일 시스템이 비지속적이므로 **프론트엔드 localStorage 병행 저장**을 기본 전략으로 채택합니다.

### expenses.json 스키마

```json
{
  "id": "uuid-v4-string",
  "created_at": "2025-07-15T14:30:00Z",
  "store_name": "이마트 강남점",
  "receipt_date": "2025-07-15",
  "receipt_time": "13:25",
  "category": "식료품",
  "items": [
    { "name": "신라면 멀티팩", "quantity": 2, "unit_price": 4500, "total_price": 9000 }
  ],
  "subtotal": 10800,
  "discount": 500,
  "tax": 0,
  "total_amount": 10300,
  "payment_method": "신용카드",
  "raw_image_path": "uploads/receipt_20250715_001.jpg"
}
```

## API 엔드포인트

| 메서드 | URL | 설명 |
|--------|-----|------|
| `POST` | `/api/upload` | 영수증 업로드 및 OCR 파싱 |
| `GET` | `/api/expenses` | 지출 목록 조회 (`?from=&to=` 날짜 필터) |
| `DELETE` | `/api/expenses/{id}` | 지출 항목 삭제 |
| `PUT` | `/api/expenses/{id}` | 지출 항목 수정 |
| `GET` | `/api/summary` | 합계 통계 조회 (`?month=YYYY-MM`) |

## UI 설계 원칙

- **스타일**: TailwindCSS, Primary 색상 `indigo-600`, 배경 `gray-50`
- **폰트**: `Pretendard` → `Noto Sans KR` fallback
- **반응형**: Mobile 1열 → Tablet(`sm:`) 2열 → Desktop(`lg:`) 3열 그리드
- **레이아웃**: `max-w-4xl mx-auto px-4` (최대 너비 896px, 중앙 정렬)
- **공통 컴포넌트**: `Badge`(카테고리), `Modal`(삭제 확인), `Toast`(3초 자동 소멸), `ProgressBar`

## 핵심 제약사항

- 파일 업로드: JPG, PNG, PDF만 허용, 최대 10MB, 서버 측에서도 재검증 필수
- OCR 응답 시간 목표: 10초 이내
- 지원 언어: 한국어·영어 영수증만 지원
- 인증 없음 (API URL 비공개로 최소 보안 유지)
- 동시 사용자: 1인 기준 MVP

## 테스트용 샘플 이미지

`images/` 디렉토리에 실제 영수증 테스트 이미지가 있습니다:
- `01_emart.png`, `02_starbucks.png`, `03_cu.jpg`, `04_lotteria.png` 등
- `GS25편의점_영수증.pdf` (PDF 파싱 테스트용)
