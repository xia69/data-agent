from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name) -> dict[str, str]:
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()
        # 示例结构: [{'Field': 'order_id', 'Type': 'varchar(30)', 'Null': 'NO'}, {'Field': 'customer_id', 'Type': 'varchar(20)', 'Null': 'YES'}]

        return {row['Field']: row['Type'] for row in result_dict}

    async def get_column_values(self, table_name, column_name, limit=10):
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]