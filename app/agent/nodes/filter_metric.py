import asyncio
import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_load import load_prompt


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("筛选指标中...")

    query = state["query"]
    metric_infos = state["metric_infos"]

    # 只把指标名和别名序列化，减轻 token
    metric_names = [m["name"] for m in metric_infos]
    metric_str = json.dumps(metric_names, ensure_ascii=False)
    logger.info(f"候选指标: {metric_str}")

    prompt_text = load_prompt("filter_metric_info.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | JsonOutputParser()
    selected: list[str] = await chain.ainvoke({"query": query, "metric_infos": metric_str})
    logger.info(f"LLM 选定: {selected}")

    filtered = [m for m in metric_infos if m["name"] in selected]
    logger.info(f"过滤后: {len(filtered)} 个指标")
    return {"metric_infos": filtered}
