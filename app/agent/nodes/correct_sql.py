import asyncio

import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_load import load_prompt


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("修正SQL中...")

    query = state["query"]
    sql = state["sql"]
    error = state.get("error", "")

    # 复用 generate_sql 的紧凑表结构
    from app.agent.nodes.generate_sql import _build_schema_text
    table_schema_text = _build_schema_text(state["table_infos"])

    metric_infos_str = yaml.dump(state["metric_infos"], allow_unicode=True, sort_keys=False)
    date_info_str = yaml.dump(state["date_info"], allow_unicode=True)
    db_info_str = yaml.dump(state["db_info"], allow_unicode=True)

    logger.info(f"修正前 SQL: {sql}")
    logger.info(f"错误信息: {error}")

    prompt_text = load_prompt("correct_sql.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | StrOutputParser()
    corrected: str = await chain.ainvoke({
        "query": query,
        "sql": sql,
        "error": error,
        "table_infos": table_schema_text,
        "metric_infos": metric_infos_str,
        "date_info": date_info_str,
        "db_info": db_info_str,
    })

    logger.info(f"修正后 SQL: {corrected}")
    return {"sql": corrected}
