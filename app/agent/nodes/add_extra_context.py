import asyncio
from datetime import date

from langgraph.runtime import Runtime
from sqlalchemy import text

from app.agent.context import DataAgentContext
from app.agent.sse_event import progress
from app.agent.state import DataAgentState
from app.core.log import logger


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer(progress("添加额外上下文", "running"))

    today = date.today()
    q = (today.month - 1) // 3 + 1

    date_info = {
        "date": today.isoformat(),
        "weekday": today.strftime("%A"),
        "quarter": f"Q{q}",
    }

    meta_mgr = runtime.context["meta_mysql_client_manager"]
    async with meta_mgr.session_factory() as session:
        r = await session.execute(text("SELECT VERSION()"))
        version = r.scalar()

    db_info = {"dialect": "MySQL", "version": version}

    logger.info(f"日期上下文: {date_info}")
    logger.info(f"数据库上下文: {db_info}")

    writer(progress("添加额外上下文", "success"))
    return {"date_info": date_info, "db_info": db_info}
