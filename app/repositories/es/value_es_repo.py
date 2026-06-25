from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.entities.value_info import ValueInfo


class ValueESRepository:
    index_name = "value_index"
    index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def ensure_index(self):
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name,
                mappings=self.index_mappings
            )

    async def index(self, value_infos: list[ValueInfo], batch_size=20):
        for i in range(0, len(value_infos), batch_size):
            batch_value_infos = value_infos[i:i + batch_size]
            batch_operations = []
            for value_info in batch_value_infos:
                batch_operations.append(
                    {
                        "index": {
                            "_index": self.index_name
                        }
                    }
                )
                batch_operations.append(asdict(value_info))
            await self.client.bulk(operations=batch_operations)

    async def search(self, query: str, size: int = 10) -> list[dict]:
        result = await self.client.search(
            index=self.index_name,
            body={
                "query": {"match": {"value": query}},
                "size": size,
            },
        )
        return [hit["_source"] for hit in result["hits"]["hits"]]