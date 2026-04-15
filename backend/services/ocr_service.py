"""
OCR 서비스: Upstage Information Extraction API를 사용하여
영수증 이미지/PDF를 구조화된 JSON으로 파싱합니다.

API 레퍼런스:
  POST https://api.upstage.ai/v1/chat/completions
  model: "information-extract"
  문서: https://console.upstage.ai/docs/capabilities/information-extraction
"""

import base64
import json
import os
import re

import requests

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
_UPSTAGE_CHAT_URL = "https://api.upstage.ai/v1/information-extraction/chat/completions"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 영수증 구조화를 위한 JSON Schema
_RECEIPT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "store_name": {
            "type": "string",
            "description": "가게 또는 상호 이름"
        },
        "receipt_date": {
            "type": "string",
            "description": "영수증 날짜 (YYYY-MM-DD 형식, 연도를 추론할 수 없으면 현재 연도 사용)"
        },
        "receipt_time": {
            "type": "string",
            "description": "영수증 시각 (HH:MM 형식), 없으면 빈 문자열"
        },
        "category": {
            "type": "string",
            "description": (
                "지출 카테고리. 반드시 다음 중 하나: "
                "식료품, 외식, 교통, 쇼핑, 의료, 기타"
            )
        },
        "items": {
            "type": "array",
            "description": "구매 품목 목록",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "품목명"},
                    "quantity": {"type": "integer", "description": "수량"},
                    "unit_price": {"type": "integer", "description": "단가 (원)"},
                    "total_price": {"type": "integer", "description": "품목 합계 (원)"}
                }
            }
        },
        "subtotal": {
            "type": "integer",
            "description": "소계 금액 (원). 없으면 total_amount와 동일한 값"
        },
        "discount": {
            "type": "integer",
            "description": "할인 금액 (원). 없으면 0"
        },
        "tax": {
            "type": "integer",
            "description": "세금 (원). 없으면 0"
        },
        "total_amount": {
            "type": "integer",
            "description": "최종 결제 금액 (원)"
        },
        "payment_method": {
            "type": "string",
            "description": "결제 수단 (예: 신용카드, 체크카드, 현금). 없으면 빈 문자열"
        }
    }
}


def parse_receipt(file_bytes: bytes, content_type: str) -> dict:
    """
    영수증 파일(이미지/PDF)을 Upstage Information Extraction API로 파싱합니다.

    Args:
        file_bytes: 업로드된 파일 바이트
        content_type: MIME 타입 (image/jpeg | image/png | application/pdf)

    Returns:
        구조화된 영수증 데이터 dict

    Raises:
        requests.HTTPError: API 호출 실패
        json.JSONDecodeError: 응답 JSON 파싱 실패
        ValueError: 필수 필드 누락 등 파싱 결과 이상
    """
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    mime_type = content_type if content_type in ALLOWED_CONTENT_TYPES else "application/octet-stream"

    headers = {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "information-extract",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_data}"
                        }
                    }
                ]
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "receipt_schema",
                "schema": _RECEIPT_JSON_SCHEMA
            }
        }
    }

    response = requests.post(
        _UPSTAGE_CHAT_URL,
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()

    raw_content = response.json()["choices"][0]["message"]["content"]

    # 응답이 문자열인 경우 JSON 파싱 (코드 블록 래퍼 제거 후)
    if isinstance(raw_content, str):
        cleaned = re.sub(r"^```json\s*", "", raw_content.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned.strip())
    else:
        parsed = raw_content

    # 필수 필드 누락 검증
    if not parsed.get("store_name") or not parsed.get("total_amount"):
        raise ValueError(
            f"OCR 파싱 결과에 필수 필드(store_name, total_amount)가 없습니다. 원본: {parsed}"
        )

    # 선택 필드 기본값 보정
    parsed.setdefault("subtotal", parsed.get("total_amount", 0))
    parsed.setdefault("discount", 0)
    parsed.setdefault("tax", 0)
    parsed.setdefault("items", [])
    parsed.setdefault("category", "기타")

    # 빈 문자열 → None 변환 (선택 필드)
    for key in ("receipt_time", "payment_method"):
        if parsed.get(key) == "":
            parsed[key] = None

    return parsed
