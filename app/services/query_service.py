from typing import AsyncIterator

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import MysqlClientManager
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repo import MetricQdrantRepository


class QueryService:
    def __init__(
        self,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
        embedding_client: HuggingFaceEndpointEmbeddings,
        meta_mysql_client_manager: MysqlClientManager,
        dw_mysql_client_manager: MysqlClientManager,
    ):
        self._context = DataAgentContext(
            column_qdrant_repository=column_qdrant_repository,
            metric_qdrant_repository=metric_qdrant_repository,
            value_es_repository=value_es_repository,
            embedding_client=embedding_client,
            meta_mysql_client_manager=meta_mysql_client_manager,
            dw_mysql_client_manager=dw_mysql_client_manager,
        )

    async def stream_query(self, question: str) -> AsyncIterator[str]:
        state = DataAgentState(query=question)
        async for chunk in graph.astream(
            state, context=self._context, stream_mode="custom",
        ):
            if chunk:
                # SSE 协议格式：data: xxx\n\n
                yield f"data: {chunk}\n\n"
