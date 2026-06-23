import uuid
from dataclasses import asdict
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repo import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository


class MetaKnowledgeService:
    def __init__(self,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 embedding_client: HuggingFaceEndpointEmbeddings,
                 value_es_repository: ValueESRepository):
        self.meta_mysql_repository: MetaMySQLRepository = meta_mysql_repository
        self.dw_mysql_repository: DWMySQLRepository = dw_mysql_repository
        self.column_qdrant_repository: ColumnQdrantRepository = column_qdrant_repository
        self.embedding_client: HuggingFaceEndpointEmbeddings = embedding_client
        self.value_es_repository: ValueESRepository = value_es_repository

    async def build(self, config_path: Path):
        logger.info(f"🚀 开始基于配置构建元数据知识库: {config_path}")
        if not config_path.exists():
            logger.error(f"❌ 配置文件不存在: {config_path}")
            raise FileNotFoundError(f"找不到指定的配置文件: {config_path}")
        try:
            context = OmegaConf.load(config_path)
            schema = OmegaConf.structured(MetaConfig)
            meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
            logger.info("✅ 配置文件解析并合并成功")
        except Exception as e:
            logger.error(f"❌ 解析 YAML 配置文件失败: {e}")
            raise
        # 1. 表的处理
        if meta_config.tables:
            logger.info(f"📦 扫描到 {len(meta_config.tables)} 张表的配置，准备同步...")

            table_infos: list[TableInfo] = []
            column_infos: list[ColumnInfo] = []
            for table in meta_config.tables:
                logger.info(f"  -> 处理表: {table.name} [角色: {table.role}]")
                # 1.1表信息与字段信息入meta数据库
                # table -> table_info
                table_info = TableInfo(
                    id=table.name,
                    name=table.name,
                    role=table.role,
                    description=table.description
                )
                table_infos.append(table_info)
                # 查字段类型
                column_types = await self.dw_mysql_repository.get_column_types(table.name)

                if table.columns:
                    for column in table.columns:
                        # 查字段取值示例
                        column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name)

                        # column -> column_info
                        column_info = ColumnInfo(
                            id=f"{table.name}.{column.name}",
                            name=column.name,
                            type=column_types[column.name],
                            role=column.role,
                            examples=column_values,
                            description=column.description,
                            alias=column.alias,
                            table_id=table.name
                        )
                        column_infos.append(column_info)

            # 对应代码中循环结束后，将收集到的列表物理保存到 MySQL 的操作
            async with self.meta_mysql_repository.session.begin():
                await self.meta_mysql_repository.save_table_infos(table_infos)
                await self.meta_mysql_repository.save_column_infos(column_infos)

            # 对字段信息建立向量索引
            await self.column_qdrant_repository.ensure_collection()
            points: list[dict] = []
            for column_info in column_infos:
                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': column_info.name,
                    'payload': asdict(column_info)
                })

                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': column_info.description,
                    'payload': asdict(column_info)
                })

                for alia in column_info.alias:
                    points.append({
                        'id': uuid.uuid4(),
                        'embedding_text': alia,
                        'payload': asdict(column_info)
                    })
            # 批量向量化
            # # 向量化
            embeddings: list[list[float]] = []
            embedding_texts = [point['embedding_text'] for point in points]
            embedding_batch_size = 20
            for i in range(0, len(embedding_texts), embedding_batch_size):
                batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
                batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
                embeddings.extend(batch_embeddings)
            # 提取点位对应的唯一 IDs 和元数据 Payloads
            ids = [point['id'] for point in points]
            payloads = [point['payload'] for point in points]

            # 将向量数据批量 Upsert 进 Qdrant
            await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

            # 指定维度字段，建立全文索引
            # # 2.3 对指定的维度字段取值建立全文索引
            await self.value_es_repository.ensure_index()

            value_infos: list[ValueInfo] = []
            for table in meta_config.tables:
                for column in table.columns:
                    if column.sync:
                        # 查询字段取值
                        current_column_values = await self.dw_mysql_repository.get_column_values(
                            table.name,
                            column.name,
                            limit=100000
                        )

                        current_values_infos = [
                            ValueInfo(
                                id=f"{table.name}.{column.name}.{current_column_value}",
                                value=current_column_value,
                                column_id=f"{table.name}.{column.name}"
                            )
                            for current_column_value in current_column_values
                        ]
                        value_infos.extend(current_values_infos)

            await self.value_es_repository.index(value_infos)

        else:
            logger.warning("⚠️ 配置中未找到 tables 节点")


            # 1.2 字段信息Qdrant向量化

            # 1.3 字段取值全文索引

        # 2. 指标的处理
        if meta_config.metrics:
            logger.info(f"📊 扫描到 {len(meta_config.metrics)} 个核心指标配置，准备同步...")
            for metric in meta_config.metrics:
                logger.info(f"  -> 处理指标: {metric.name}")

                # TODO: 入库指标信息 (metric.name, metric.description, metric.relevant_columns, metric.alias)
                pass
        else:
            logger.info("ℹ️ 配置中未找到 metrics 节点，跳过指标同步")

        logger.info("🎉 元数据知识库构建流程执行完毕！")