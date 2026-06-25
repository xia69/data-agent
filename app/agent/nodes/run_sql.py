import asyncio

from langgraph.runtime import Runtime
from sqlalchemy import text

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("执行SQL中...")

    sql: str = state["sql"]
    dw_mgr = runtime.context["dw_mysql_client_manager"]

    async with dw_mgr.session_factory() as session:
        result = await session.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()

    data = [dict(zip(columns, row)) for row in rows]
    logger.info(f"SQL 结果: {len(data)} 行")
    logger.info(f"数据: {data}")

    return {"result": data}
