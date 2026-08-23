from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_best_match_service
from app.models.best_match import BestMatchRequest, BestMatchResponse
from app.services.jobs.best_match import BestMatchService

router = APIRouter(prefix="/best-match", tags=["best-match"])


@router.post("", response_model=BestMatchResponse)
def analyze_best_match(
    request: BestMatchRequest,
    service: BestMatchService = Depends(get_best_match_service),
    x_run_id: str | None = Header(default=None, alias="X-Run-Id"),
) -> BestMatchResponse:
    return service.analyze(request, run_id=x_run_id)
