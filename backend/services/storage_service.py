import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_DATA_FILE = Path(__file__).parent.parent / "data" / "expenses.json"


def _get_data_file() -> Path:
    env_path = os.getenv("DATA_FILE_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = Path(__file__).parent.parent / p
        return p
    return _DEFAULT_DATA_FILE


def load_expenses() -> list:
    """expenses.json을 읽어 리스트로 반환. 파일 없으면 빈 배열로 초기화."""
    data_file = _get_data_file()
    if not data_file.exists():
        data_file.parent.mkdir(parents=True, exist_ok=True)
        data_file.write_text("[]", encoding="utf-8")
        return []
    try:
        text = data_file.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else []
    except (json.JSONDecodeError, OSError):
        return []


def save_expenses(data: list) -> None:
    """리스트를 expenses.json에 저장."""
    data_file = _get_data_file()
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def append_expense(item: dict) -> dict:
    """UUID와 생성 시각을 부여하고 expenses.json에 추가 저장 후 반환."""
    item["id"] = str(uuid.uuid4())
    item["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    expenses = load_expenses()
    expenses.append(item)
    save_expenses(expenses)
    return item
