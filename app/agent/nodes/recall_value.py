import asyncio

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.sse_event import progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_load import load_prompt


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer(progress("召回取值", "running"))

    query = state["query"]
    keywords: list[str] = state["keywords"]
    value_es_repo = runtime.context["value_es_repository"]

    # --- 1. LLM 扩展关键词 ---
    prompt_text = load_prompt("extend_keywords_for_value_recall.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | JsonOutputParser()
    optimized: list[str] = await chain.ainvoke({"query": query})

    # --- 2. 合并去重 ---
    keywords = list(set(keywords + optimized))
    logger.info(f"结巴关键词: {state['keywords']}")
    logger.info(f"LLM扩展词: {optimized}")
    logger.info(f"最终取值召回关键词: {keywords}")

    # --- 3. ES 全文检索 ---
    retrieved_value_infos: list[ValueInfo] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        values = await value_es_repo.search(keyword, size=10)
        for payload in values:
            value = ValueInfo(**payload)
            if value.id not in seen_ids:
                seen_ids.add(value.id)
                retrieved_value_infos.append(value)
    # 日志输出
    logger.info(f"取值召回结果: {len(retrieved_value_infos)} 条")
    logger.info(f"召回取值: {[v.value for v in retrieved_value_infos]}")
    writer(progress("召回取值", "success"))
    return {"retrieved_value_infos": retrieved_value_infos}
