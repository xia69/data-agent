import asyncio

from langgraph.runtime import Runtime
from sqlalchemy import text

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("校验SQL中...")

    sql: str = state["sql"]
    logger.info(f"待校验 SQL: {sql}")

    dw_mgr = runtime.context["dw_mysql_client_manager"]
    try:
        async with dw_mgr.session_factory() as session:
            await session.execute(text(sql))
        error = None
        logger.info("SQL 校验通过")
    except Exception as e:
        error = str(e)
        logger.error(f"SQL 校验失败: {error}")

    return {"error": error}
