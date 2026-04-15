#!/usr/bin/env python
"""
PRD 자동 동기화 Stop Hook
----------------------------------------------------
Claude가 작업을 완료할 때마다 PRD_영수증_지출관리앱.md를
자동으로 업데이트하도록 지시합니다.

동작 방식:
  - 쿨다운(3분) 미경과 시: 아무것도 출력하지 않고 종료 (Claude 정상 종료)
  - 쿨다운 경과 시: additionalContext + continue:true 반환
    → Claude가 코드 변경 사항을 PRD에 반영 후 종료
    → 종료 시 다시 Stop Hook 실행되지만 쿨다운에 걸려 멈춤

무한루프 방지: 상태 파일(.prd_sync_state)의 3분 쿨다운
----------------------------------------------------
"""

import os
import sys
import time
import json
from pathlib import Path

# Windows cp949 환경에서 한글/특수문자 출력 보장
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

PROJECT_DIR  = Path("C:/claude_ocr_1day")
PRD_PATH     = PROJECT_DIR / "PRD_영수증_지출관리앱.md"
STATE_FILE   = PROJECT_DIR / ".claude" / ".prd_sync_state"
COOLDOWN_SEC = 180  # 3분


def main():
    # PRD 파일이 없으면 skip
    if not PRD_PATH.exists():
        return

    # ── 쿨다운 체크 ──────────────────────────────────────
    if STATE_FILE.exists():
        try:
            last_run = float(STATE_FILE.read_text().strip())
            if time.time() - last_run < COOLDOWN_SEC:
                return          # 3분 이내 → Claude 그냥 종료
        except (ValueError, OSError):
            pass

    # ── 쿨다운 갱신 (이 요청이 처리되는 동안 재진입 차단) ──
    try:
        STATE_FILE.write_text(str(time.time()))
    except OSError:
        return

    # ── Claude에게 PRD 업데이트 요청 주입 ─────────────────
    context = (
        "방금 완료된 작업에서 backend/ 또는 frontend/ 코드 파일을 수정했다면, "
        "PRD_영수증_지출관리앱.md의 해당 Phase 완료 기준 체크박스를 업데이트해 주세요.\n"
        "• 완료된 항목: '- [ ]' → '- [x]'\n"
        "• 실제 구현과 다른 기술 스펙(버전, 경로 등)은 해당 부분만 수정\n"
        "• PRD 파일 외 다른 파일은 수정하지 마세요\n"
        "코드 변경이 없었거나 PRD가 이미 최신이라면 아무 말 없이 바로 종료하세요."
    )

    result = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": context,
        },
    }
    print(json.dumps(result, ensure_ascii=False))


main()
