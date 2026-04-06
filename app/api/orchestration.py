from fastapi import APIRouter
from ..models.schemas import Task
from ..models.orchestration import OrchestrationResult
from app.services.product_orchestrator import ProductOrchestrator

router = APIRouter()


@router.post("/process", response_model=OrchestrationResult)
async def process_task_submission(task: Task):
    """
    Main entry point for the autonomous review process.
    """
    orchestrator = ProductOrchestrator()
    return orchestrator.process_submission(task)