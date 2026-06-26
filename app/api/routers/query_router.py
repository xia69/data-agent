from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.services.query_service import QueryService


query_router = APIRouter()

class QueryRequest(BaseModel):
    question: str


@query_router.post("/api/query")
async def query(
    req: QueryRequest,
    service: QueryService = Depends(get_query_service),
):
    return StreamingResponse(
        service.stream_query(req.question),
        media_type="text/event-stream",
    )
