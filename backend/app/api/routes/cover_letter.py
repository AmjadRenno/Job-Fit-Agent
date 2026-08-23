from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_cover_letter_service
from app.models.cover_letter import CoverLetterRequest, CoverLetterResponse
from app.services.jobs.cover_letter import CoverLetterService

router = APIRouter(prefix="/cover-letter", tags=["cover-letter"])


@router.post("", response_model=CoverLetterResponse)
def generate_cover_letter(
    request: CoverLetterRequest,
    service: CoverLetterService = Depends(get_cover_letter_service),
    x_run_id: str | None = Header(default=None, alias="X-Run-Id"),
) -> CoverLetterResponse:
    return service.generate(request, run_id=x_run_id)
