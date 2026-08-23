from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_job_analysis_service
from app.models.job_analysis import JobAnalysisRequest, JobAnalysisResponse
from app.services.jobs.analysis import JobAnalysisService

router = APIRouter(prefix="/job-analysis", tags=["job-analysis"])


@router.post("", response_model=JobAnalysisResponse)
def analyze_job(
    request: JobAnalysisRequest,
    service: JobAnalysisService = Depends(get_job_analysis_service),
    x_run_id: str | None = Header(default=None, alias="X-Run-Id"),
) -> JobAnalysisResponse:
    return service.analyze(request, run_id=x_run_id)
