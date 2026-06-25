from typing import TypedDict

from elasticsearch import AsyncElasticsearch
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.clients.mysql_client_manager import MysqlClientManager
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repo import MetricQdrantRepository


class DataAgentContext(TypedDict):
    column_qdrant_repository: ColumnQdrantRepository
    metric_qdrant_repository: MetricQdrantRepository
    value_es_repository: ValueESRepository
    embedding_client: HuggingFaceEndpointEmbeddings
    meta_mysql_client_manager: MysqlClientManager
    dw_mysql_client_manager: MysqlClientManager
