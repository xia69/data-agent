import asyncio

from langgraph.runtime import Runtime
from sqlalchemy import text

from app.agent.context import DataAgentContext
from app.agent.sse_event import progress, result as result_event
from app.agent.state import DataAgentState
from app.core.log import logger


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer(progress("执行SQL", "running"))

    sql: str = state["sql"]
    dw_mgr = runtime.context["dw_mysql_client_manager"]

    async with dw_mgr.session_factory() as session:
        result = await session.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()

    data = [dict(zip(columns, row)) for row in rows]
    logger.info(f"SQL 结果: {len(data)} 行")
    logger.info(f"数据: {data}")

    writer(progress("执行SQL", "success"))
    writer(result_event(data))
    return {"result": data}
