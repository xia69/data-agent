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


def _build_schema_text(table_infos: list) -> str:
    """把 table_infos 压缩成 LLM 友好格式，突出主外键关系"""
    lines = []
    # 先收集所有列，找出跨表同名的外键关系
    pk_map: dict[str, str] = {}  # column_name -> table_name
    for t in table_infos:
        for c in t["columns"]:
            if c["role"] == "primary_key":
                pk_map[c["name"]] = t["name"]

    for t in table_infos:
        cols_str = []
        for c in t["columns"]:
            extra = ""
            if c["role"] == "foreign_key" and c["name"] in pk_map:
                extra = f"  ← 关联 {pk_map[c['name']]}.{c['name']}"
            elif c["role"] == "primary_key":
                extra = "  [主键]"
            cols_str.append(
                f"    {c['name']} ({c['type']}) [{c['role']}] — {c['description']}{extra}"
            )
        lines.append(
            f"表: {t['name']} [{t['role']}] — {t['description']}\n"
            + "\n".join(cols_str)
        )
    return "\n\n".join(lines)


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("生成SQL中...")

    query = state["query"]
    table_schema_text = _build_schema_text(state["table_infos"])
    logger.info(f"表结构:\n{table_schema_text}")

    metric_infos_str = yaml.dump(state["metric_infos"], allow_unicode=True, sort_keys=False)
    date_info_str = yaml.dump(state["date_info"], allow_unicode=True)
    db_info_str = yaml.dump(state["db_info"], allow_unicode=True)

    prompt_text = load_prompt("generate_sql.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | StrOutputParser()
    sql: str = await chain.ainvoke({
        "query": query,
        "table_infos": table_schema_text,
        "metric_infos": metric_infos_str,
        "date_info": date_info_str,
        "db_info": db_info_str,
    })

    logger.info(f"生成的 SQL:\n{sql}")
    writer(f"SQL: {sql}")
    return {"sql": sql}
