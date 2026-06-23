"""
元数据知识库构建服务
=====================
这是整个数据同步的"大脑"，负责将 YAML 配置中的元数据组织并写入三个存储：

  ① MySQL (meta 库) — 结构化元数据，供 Agent 查询"有哪些表、字段、指标"
  ② Qdrant           — 向量索引，供 Agent 做语义搜索（"用户说的是哪个字段？"）
  ③ ES               — 全文索引，供 Agent 做关键词匹配（"广东省"对应哪个字段值？）

整个 build() 方法分两大部分：
  Part 1 — 表的处理：表信息 → 字段信息 → 向量化 → 字段取值全文索引
  Part 2 — 指标的处理：指标信息 → 字段-指标映射 → 向量化
"""

import uuid
from dataclasses import asdict
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repo import MetricQdrantRepository


class MetaKnowledgeService:
    """
    元数据知识库构建服务核心

    依赖注入清单（__init__ 参数）:
      meta_mysql_repository  — 写元数据库（table_info / column_info / metric_info / column_metric）
      dw_mysql_repository    — 读数仓（查字段类型、查字段取值示例）
      column_qdrant_repository — 字段向量索引（Qdrant）
      metric_qdrant_repository — 指标向量索引（Qdrant）
      embedding_client       — 文本向量化服务（HuggingFace TEI）
      value_es_repository    — 字段取值全文检索（ES）
    """

    def __init__(self,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 embedding_client: HuggingFaceEndpointEmbeddings,
                 value_es_repository: ValueESRepository,
                 metric_qdrant_repository: MetricQdrantRepository):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def build(self, config_path: Path):
        """
        主入口：读取 YAML 配置，完成全量同步。

        配置解析 → 表处理（MySQL + Qdrant + ES） → 指标处理（MySQL + Qdrant）
        """
        logger.info(f"🚀 开始基于配置构建元数据知识库: {config_path}")

        # ── 0. 加载 & 校验 YAML 配置文件 ──
        if not config_path.exists():
            logger.error(f"❌ 配置文件不存在: {config_path}")
            raise FileNotFoundError(f"找不到指定的配置文件: {config_path}")

        try:
            # OmegaConf 的套路：load → structured(生成Schema) → merge → to_object(强类型)
            context = OmegaConf.load(config_path)
            schema = OmegaConf.structured(MetaConfig)
            meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
            logger.info("✅ 配置文件解析并合并成功")
        except Exception as e:
            logger.error(f"❌ 解析 YAML 配置文件失败: {e}")
            raise

        # ================================================================
        #  Part 1 — 表的处理
        #   table_info (MySQL) + column_info (MySQL + Qdrant) + value_info (ES)
        # ================================================================
        if meta_config.tables:
            logger.info(f"📦 扫描到 {len(meta_config.tables)} 张表的配置，准备同步...")

            table_infos: list[TableInfo] = []
            column_infos: list[ColumnInfo] = []

            # 1a. 遍历每张表，从数仓获取真实类型和示例值，组装实体
            for table in meta_config.tables:
                logger.info(f"  -> 处理表: {table.name} [角色: {table.role}]")

                # 组装 TableInfo 实体
                table_info = TableInfo(
                    id=table.name,
                    name=table.name,
                    role=table.role,
                    description=table.description,
                )
                table_infos.append(table_info)

                # 从数仓查询：这张表每个字段的真实数据类型
                column_types = await self.dw_mysql_repository.get_column_types(table.name)

                if table.columns:
                    for column in table.columns:
                        # 从数仓查询：这个字段的真实取值示例（前10条，用于前端展示）
                        column_values = await self.dw_mysql_repository.get_column_values(
                            table.name, column.name
                        )

                        # 组装 ColumnInfo 实体
                        # id 格式: "表名.字段名"（如 fact_order.order_amount）
                        column_info = ColumnInfo(
                            id=f"{table.name}.{column.name}",
                            name=column.name,
                            type=column_types[column.name],
                            role=column.role,
                            examples=column_values,
                            description=column.description,
                            alias=column.alias,
                            table_id=table.name,
                        )
                        column_infos.append(column_info)

            # 1b. 写入 MySQL（先删后插，保证幂等）
            async with self.meta_mysql_repository.session.begin():
                await self.meta_mysql_repository.save_table_infos(table_infos)
                await self.meta_mysql_repository.save_column_infos(column_infos)

            # 1c. 字段向量化 → 写入 Qdrant
            await self.column_qdrant_repository.ensure_collection()

            # 组装待向量化的文本列表
            # 每个字段生成多条文本：字段名、字段描述、每个别名
            # 这样用"销量"、"购买数量"、"件数"搜都能命中同一个字段
            points: list[dict] = []
            for column_info in column_infos:
                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': column_info.name,          # 如 "order_amount"
                    'payload': asdict(column_info),             # 原始数据存 payload，搜索命中后原样返回
                })
                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': column_info.description,   # 如 "订单金额"
                    'payload': asdict(column_info),
                })
                for alia in column_info.alias:
                    points.append({
                        'id': uuid.uuid4(),
                        'embedding_text': alia,                  # 如 "销售额"、"收入"
                        'payload': asdict(column_info),
                    })

            # 分批调用 Embedding 服务（避免一次请求过大导致超时/断连）
            embeddings: list[list[float]] = []
            embedding_texts = [point['embedding_text'] for point in points]
            embedding_batch_size = 20       # 每批 20 条文本一起向量化
            for i in range(0, len(embedding_texts), embedding_batch_size):
                batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
                batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
                embeddings.extend(batch_embeddings)

            ids = [point['id'] for point in points]
            payloads = [point['payload'] for point in points]
            await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

            # 1d. 维度字段取值 → 全文索引（ES）
            # 只有 YAML 中配置了 sync: true 的字段才会进入 ES
            # 例如省份名、品类名这类用户可能直接输入的值
            await self.value_es_repository.ensure_index()

            value_infos: list[ValueInfo] = []
            for table in meta_config.tables:
                for column in table.columns:
                    if column.sync:
                        # 取该字段的全部实际值（上限 10w 条）
                        current_column_values = await self.dw_mysql_repository.get_column_values(
                            table.name, column.name, limit=100000
                        )
                        # 每条取值对应一个 ValueInfo
                        # id 格式: "表名.字段名.取值"（如 dim_region.province.广东省）
                        current_values_infos = [
                            ValueInfo(
                                id=f"{table.name}.{column.name}.{current_column_value}",
                                value=current_column_value,
                                column_id=f"{table.name}.{column.name}",
                            )
                            for current_column_value in current_column_values
                        ]
                        value_infos.extend(current_values_infos)

            await self.value_es_repository.index(value_infos)

        else:
            logger.warning("⚠️ 配置中未找到 tables 节点")

        # ================================================================
        #  Part 2 — 指标的处理
        #   metric_info (MySQL) + column_metric (MySQL) + Qdrant 向量
        # ================================================================
        if meta_config.metrics:
            logger.info(f"📊 扫描到 {len(meta_config.metrics)} 个核心指标配置，准备同步...")

            metric_infos: list[MetricInfo] = []
            column_metrics: list[ColumnMetric] = []

            for metric in meta_config.metrics:
                logger.info(f"  -> 处理指标: {metric.name}")

                # 组装 MetricInfo 实体
                metric_info = MetricInfo(
                    id=metric.name,
                    name=metric.name,
                    description=metric.description,
                    relevant_columns=metric.relevant_columns,   # 如 ["fact_order.order_amount"]
                    alias=metric.alias,
                )
                metric_infos.append(metric_info)

                # 建立 字段 ↔ 指标 多对多映射
                # 如：fact_order.order_amount ↔ GMV
                for column in metric.relevant_columns:
                    column_metric = ColumnMetric(
                        column_id=column,
                        metric_id=metric.name,
                    )
                    column_metrics.append(column_metric)

            # 2a. 写入 MySQL
            async with self.meta_mysql_repository.session.begin():
                await self.meta_mysql_repository.save_metric_infos(metric_infos)
                await self.meta_mysql_repository.save_column_metrics(column_metrics)

            # 2b. 指标向量化 → 写入 Qdrant
            # 逻辑和上面字段向量化完全一致：指标名 + 描述 + 别名 各自向量化
            await self.metric_qdrant_repository.ensure_collection()

            points: list[dict] = []
            for metric_info in metric_infos:
                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': metric_info.name,
                    'payload': asdict(metric_info),
                })
                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': metric_info.description,
                    'payload': asdict(metric_info),
                })
                if metric_info.alias:
                    for alias_name in metric_info.alias:
                        points.append({
                            'id': uuid.uuid4(),
                            'embedding_text': alias_name,
                            'payload': asdict(metric_info),
                        })

            if points:
                embeddings: list[list[float]] = []
                embedding_texts = [point['embedding_text'] for point in points]
                embedding_batch_size = 20

                logger.info(
                    f"⏳ 准备为 {len(embedding_texts)} 条指标文本生成向量，"
                    f"批次大小: {embedding_batch_size}..."
                )

                for i in range(0, len(embedding_texts), embedding_batch_size):
                    batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
                    batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
                    embeddings.extend(batch_embeddings)

                ids = [point['id'] for point in points]
                payloads = [point['payload'] for point in points]
                await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)
                logger.info("✅ 业务指标向量索引构建完毕！全线竣工！🎉")

        else:
            logger.info("ℹ️ 配置中未找到 metrics 节点，跳过指标同步")

        logger.info("🎉 元数据知识库构建流程执行完毕！")
