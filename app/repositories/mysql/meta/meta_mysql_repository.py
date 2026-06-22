from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_table_infos(self, table_infos: list[TableInfo]):
        # 💡 add_all 是同步操作，不要在它前面加 await；但方法本身需要声明为 async def 供 Service 层 await
        self.session.add_all([TableInfoMapper.to_model(table_info) for table_info in table_infos])

    async def save_column_infos(self, column_infos: list[ColumnInfo]):
        self.session.add_all([ColumnInfoMapper.to_model(column_info) for column_info in column_infos])