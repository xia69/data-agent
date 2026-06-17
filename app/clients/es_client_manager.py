import asyncio

from elasticsearch import AsyncElasticsearch
from app.conf.app_config import ESConfig, app_config


class ESClientManager:
    def __init__(self, config: ESConfig):
        self.client: AsyncElasticsearch | None = None
        self.config: ESConfig = config

    def _get_url(self) -> str:
        # noinspection HttpUrlsUsage
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = AsyncElasticsearch(hosts=[self._get_url()])

    async def close(self):
        if self.client is not None:
            await self.client.close()

es_client_manager = ESClientManager(app_config.es)

# test
if __name__ == '__main__':
    es_client_manager.init()
    client = es_client_manager.client

    async def test():
        # 创建index
        await client.indices.create(
            index="book",
        )
        # 插入数据
        await client.index(
            index="books",
            document={
                "name": "Xiajinxi",
                "author": "Xiajinxi26",
                "release_date": "2002-10-26",
                "page_count": 470
            }
        )
        # query
        response = await client.search(
            index="books",
        )
        print(response)
        await client.close()
    asyncio.run(test())