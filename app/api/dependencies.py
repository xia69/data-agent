from typing import Annotated

from fastapi import Depends
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    MysqlClientManager,
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repo import MetricQdrantRepository
from app.services.query_service import QueryService


def _get_column_qdrant_repo() -> ColumnQdrantRepository:
    return ColumnQdrantRepository(qdrant_client_manager.client)


def _get_metric_qdrant_repo() -> MetricQdrantRepository:
    return MetricQdrantRepository(qdrant_client_manager.client)


def _get_value_es_repo() -> ValueESRepository:
    return ValueESRepository(es_client_manager.client)


def _get_embedding_client() -> HuggingFaceEndpointEmbeddings:
    return embedding_client_manager.client


def _get_meta_mysql_mgr() -> MysqlClientManager:
    return meta_mysql_client_manager


def _get_dw_mysql_mgr() -> MysqlClientManager:
    return dw_mysql_client_manager


def get_query_service(
    column_qdrant_repo: Annotated[ColumnQdrantRepository, Depends(_get_column_qdrant_repo)],
    metric_qdrant_repo: Annotated[MetricQdrantRepository, Depends(_get_metric_qdrant_repo)],
    value_es_repo: Annotated[ValueESRepository, Depends(_get_value_es_repo)],
    embedding_client: Annotated[HuggingFaceEndpointEmbeddings, Depends(_get_embedding_client)],
    meta_mysql_mgr: Annotated[MysqlClientManager, Depends(_get_meta_mysql_mgr)],
    dw_mysql_mgr: Annotated[MysqlClientManager, Depends(_get_dw_mysql_mgr)],
) -> QueryService:
    return QueryService(
        column_qdrant_repository=column_qdrant_repo,
        metric_qdrant_repository=metric_qdrant_repo,
        value_es_repository=value_es_repo,
        embedding_client=embedding_client,
        meta_mysql_client_manager=meta_mysql_mgr,
        dw_mysql_client_manager=dw_mysql_mgr,
    )
