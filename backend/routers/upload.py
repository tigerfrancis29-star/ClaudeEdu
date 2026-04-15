import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services import ocr_service
from backend.services import storage_service

router = APIRouter()

_UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


@router.post("/upload")
async def upload_receipt(file: UploadFile = File(...)):
    """
    영수증 파일 업로드 → OCR 파싱 → expenses.json 저장

    - 지원 형식: JPG, PNG, PDF
    - 최대 크기: 10MB
    - 성공 시: 파싱된 지출 JSON 객체 반환
    - 실패 시: 400 (파일 오류) 또는 500 (OCR 실패)
    """

    # ── 1. 파일 형식 검증 ────────────────────────────────────────
    if file.content_type not in ocr_service.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"지원하지 않는 파일 형식입니다. JPG, PNG, PDF만 허용됩니다. "
                f"(수신된 형식: {file.content_type})"
            )
        )

    # ── 2. 파일 읽기 및 크기 검증 ────────────────────────────────
    file_bytes = await file.read()
    if len(file_bytes) > ocr_service.MAX_FILE_SIZE:
        size_mb = len(file_bytes) / 1024 / 1024
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 10MB를 초과합니다. (수신: {size_mb:.1f}MB)"
        )

    # ── 3. 업로드 파일 디스크 저장 ───────────────────────────────
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 파일명에서 경로 구분자 제거 (보안)
    original_name = Path(file.filename or "file").name
    safe_filename = f"receipt_{timestamp}_{original_name}"
    upload_path = _UPLOADS_DIR / safe_filename
    upload_path.write_bytes(file_bytes)

    # ── 4. OCR 파싱 (블로킹 I/O → 스레드 풀 실행) ───────────────
    try:
        parsed = await asyncio.to_thread(
            ocr_service.parse_receipt,
            file_bytes,
            file.content_type
        )
    except Exception as e:
        # OCR 실패 시 업로드된 파일 정리
        upload_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=(
                "영수증 파싱에 실패했습니다. 이미지를 확인하고 다시 시도해 주세요. "
                f"({type(e).__name__}: {e})"
            )
        )

    # ── 5. 원본 이미지 경로 추가 후 저장 ────────────────────────
    parsed["raw_image_path"] = f"uploads/{safe_filename}"
    saved = storage_service.append_expense(parsed)

    return saved
