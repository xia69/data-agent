import asyncio

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.sse_event import progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_load import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer(progress("筛选表", "running"))

    query = state["query"]
    table_infos = state["table_infos"]

    yaml_str = yaml.dump(table_infos, allow_unicode=True, sort_keys=False)
    logger.info(f"候选表 YAML:\n{yaml_str}")

    prompt_text = load_prompt("filter_table_info.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | JsonOutputParser()
    selected: dict[str, list[str]] = await chain.ainvoke({"query": query, "table_infos": yaml_str})
    logger.info(f"LLM 选定: {selected}")

    # 按 LLM 输出过滤
    filtered = []
    for table in table_infos:
        if table["name"] in selected:
            keep_cols = set(selected[table["name"]])
            filtered_columns = [c for c in table["columns"] if c["name"] in keep_cols]
            filtered.append({**table, "columns": filtered_columns})

    logger.info(f"过滤后: {len(filtered)} 张表")
    writer(progress("筛选表", "success"))
    return {"table_infos": filtered}
