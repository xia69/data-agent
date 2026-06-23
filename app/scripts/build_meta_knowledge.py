import argparse
import asyncio
from pathlib import Path

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant import column_qdrant_repo
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager


async def build(config_path: Path):
    logger.info(f"Building with config: {config_path}")
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    async with meta_mysql_client_manager.session_factory() as meta_session, \
            dw_mysql_client_manager.session_factory() as dw_session:

        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueESRepository(es_client_manager.client)

        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository=meta_mysql_repository,
            dw_mysql_repository=dw_mysql_repository,
            column_qdrant_repository=column_qdrant_repository,
            embedding_client=embedding_client_manager.client,
            value_es_repository=value_es_repository
        )
        await meta_knowledge_service.build(config_path)

    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # 【核心优化】
    # 1. type=Path：告诉解析器直接把输入的字符串转成 Path 对象
    # 2. required=True：强制校验，不传这个参数直接不让运行
    parser.add_argument('-c', '--conf', type=Path, required=True, help="配置文件的路径")

    args = parser.parse_args()

    # 因为上面指定了 type=Path，此时 args.conf 已经是一个 Path 对象了
    # 不需要再手动套一层 Path()，直接传给 build 函数即可
    asyncio.run(build(args.conf))