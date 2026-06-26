import asyncio

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.sse_event import progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_load import load_prompt

async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer(progress("召回指标", "running"))

    query = state["query"]
    keywords: list[str] = state["keywords"]
    embedding_client = runtime.context["embedding_client"]
    metric_qdrant_repo = runtime.context["metric_qdrant_repository"]

    # --- 1. LLM 扩展关键词 ---
    prompt_text = load_prompt("extend_keywords_for_metric_recall.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | JsonOutputParser()
    optimized: list[str] = await chain.ainvoke({"query": query})

    from app.entities.metric_info import MetricInfo

    # --- 2. 合并去重 ---
    keywords = list(set(keywords + optimized))
    logger.info(f"结巴关键词: {state['keywords']}")
    logger.info(f"LLM扩展词: {optimized}")
    logger.info(f"最终指标召回关键词: {keywords}")

    # --- 3. 向量化 + Qdrant 检索 ---
    retrieved_metric_infos: list[MetricInfo] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        vector = await embedding_client.aembed_query(keyword)
        metrics = await metric_qdrant_repo.search(vector, score_threshold=0.6, limit=10)
        for payload in metrics:
            metric = MetricInfo(**payload)
            if metric.id not in seen_ids:
                seen_ids.add(metric.id)
                retrieved_metric_infos.append(metric)

    logger.info(f"指标召回结果: {len(retrieved_metric_infos)} 个指标")
    logger.info(f"召回指标: {[m.id for m in retrieved_metric_infos]}")
    writer(progress("召回指标", "success"))
    return {"retrieved_metric_infos": retrieved_metric_infos}


