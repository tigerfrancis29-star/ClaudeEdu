from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
async def get_summary():
    """지출 합계 통계 — Phase 3에서 구현"""
    return {
        "total_amount": 0,
        "this_month_amount": 0,
        "category_summary": [],
    }
