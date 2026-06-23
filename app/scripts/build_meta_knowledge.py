"""
元数据知识库构建脚本
=====================
用途：将 YAML 配置中定义的表、字段、指标等信息，一次性同步到三个存储：

  MySQL   — 结构化元数据（表信息、字段信息、指标信息、字段-指标映射）
  Qdrant  — 向量索引（字段名/描述的向量，指标名/描述的向量，用于语义搜索）
  ES      — 全文索引（维度字段的具体取值，用于关键词匹配）

每次运行会全量覆盖已有数据（先删后插），可以反复执行。
"""

import argparse
import asyncio
from pathlib import Path

# ---- 客户端管理器（单例）----
# 每个管理器负责一个外部服务的连接生命周期：init() → 使用 → close()
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager

from app.core.log import logger

# ---- 仓库层（Repository）----
# 封装对具体存储的读写操作，Service 层不直接写 SQL/API 调用
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repo import MetricQdrantRepository

# ---- 核心业务逻辑 ----
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build(config_path: Path):
    """
    主流程：
    1. 初始化所有外部连接
    2. 组装依赖（Repository → Service）
    3. 执行构建
    4. 关闭所有连接
    """
    logger.info(f"Building with config: {config_path}")

    # ── 1. 初始化客户端连接 ──
    meta_mysql_client_manager.init()   # 元数据 MySQL
    dw_mysql_client_manager.init()     # 数仓 MySQL（只读，查字段类型和取值）
    qdrant_client_manager.init()       # Qdrant 向量库
    embedding_client_manager.init()    # Embedding 服务（文本 → 向量）
    es_client_manager.init()           # ES 全文检索

    # ── 2. 创建数据库会话 & 组装依赖 ──
    # async with 确保会话用完自动提交/回滚
    async with meta_mysql_client_manager.session_factory() as meta_session, \
            dw_mysql_client_manager.session_factory() as dw_session:

        # Repository 层：每种存储一个 repo
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueESRepository(es_client_manager.client)

        # Service 层：将所有 repo + embedding 客户端注入
        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository=meta_mysql_repository,
            dw_mysql_repository=dw_mysql_repository,
            column_qdrant_repository=column_qdrant_repository,
            embedding_client=embedding_client_manager.client,
            value_es_repository=value_es_repository,
            metric_qdrant_repository=metric_qdrant_repository,
        )

        # ── 3. 执行同步 ──
        await meta_knowledge_service.build(config_path)

    # ── 4. 释放连接 ──
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()
    await qdrant_client_manager.close()
    await es_client_manager.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="元数据知识库构建工具 — 将 YAML 配置同步到 MySQL/Qdrant/ES"
    )
    parser.add_argument(
        '-c', '--conf',
        type=Path,         # 自动将输入的字符串转为 Path 对象
        required=True,     # 不传 --conf 直接报错
        help="配置文件的路径，例如: conf/meta_config.yaml",
    )
    args = parser.parse_args()

    # asyncio.run()：Python 标准库的异步入口，自动创建事件循环
    asyncio.run(build(args.conf))
