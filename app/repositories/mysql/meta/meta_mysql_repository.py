from sqlalchemy import and_, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.column_metric import ColumnMetricMySQL
from app.models.metric_info import MetricInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_table_infos(self, table_infos: list[TableInfo]):
        ids = [ti.id for ti in table_infos]
        if ids:
            await self.session.execute(delete(TableInfoMySQL).where(TableInfoMySQL.id.in_(ids)))
        self.session.add_all([TableInfoMapper.to_model(table_info) for table_info in table_infos])

    async def save_column_infos(self, column_infos: list[ColumnInfo]):
        ids = [ci.id for ci in column_infos]
        if ids:
            await self.session.execute(delete(ColumnInfoMySQL).where(ColumnInfoMySQL.id.in_(ids)))
        self.session.add_all([ColumnInfoMapper.to_model(column_info) for column_info in column_infos])

    async def save_metric_infos(self, metric_infos: list[MetricInfo]):
        ids = [mi.id for mi in metric_infos]
        if ids:
            await self.session.execute(delete(MetricInfoMySQL).where(MetricInfoMySQL.id.in_(ids)))
        self.session.add_all([MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos])

    async def save_column_metrics(self, column_metrics: list[ColumnMetric]):
        conditions = [
            and_(
                ColumnMetricMySQL.column_id == cm.column_id,
                ColumnMetricMySQL.metric_id == cm.metric_id,
            )
            for cm in column_metrics
        ]
        if conditions:
            await self.session.execute(delete(ColumnMetricMySQL).where(or_(*conditions)))
        self.session.add_all([ColumnMetricMapper.to_model(column_metric) for column_metric in column_metrics])

    async def get_column_infos_by_ids(self, column_ids: list[str]) -> list[ColumnInfo]:
        if not column_ids:
            return []
        from sqlalchemy import select
        result = await self.session.execute(
            select(ColumnInfoMySQL).where(ColumnInfoMySQL.id.in_(column_ids))
        )
        return [ColumnInfoMapper.to_entity(row) for row in result.scalars()]

    async def get_table_infos_by_ids(self, table_ids: list[str]) -> list[TableInfo]:
        if not table_ids:
            return []
        from sqlalchemy import select
        result = await self.session.execute(
            select(TableInfoMySQL).where(TableInfoMySQL.id.in_(table_ids))
        )
        return [TableInfoMapper.to_entity(row) for row in result.scalars()]

    async def get_all_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:
        from sqlalchemy import select
        result = await self.session.execute(
            select(ColumnInfoMySQL).where(ColumnInfoMySQL.table_id == table_id)
        )
        return [ColumnInfoMapper.to_entity(row) for row in result.scalars()]