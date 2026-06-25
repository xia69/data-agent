import asyncio

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_load import load_prompt


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("召回字段中...")

    query = state["query"]
    jieba_keywords: list[str] = state["keywords"]
    column_qdrant_repo = runtime.context["column_qdrant_repository"]

    # --- 1. LLM 扩展关键词 ---
    prompt_text = load_prompt("extend_keywords_for_column_recall.prompt")
    chain = ChatPromptTemplate.from_template(prompt_text) | llm | JsonOutputParser()
    optimized: list[str] = await chain.ainvoke({"query": query})

    # --- 2. 合并去重，写回 state ---
    keywords = list(set(jieba_keywords + optimized))
    logger.info(f"结巴关键词: {jieba_keywords}")
    logger.info(f"LLM扩展词: {optimized}")
    logger.info(f"最终召回关键词: {keywords}")

    # --- 3. 向量化 + Qdrant 检索 ---
    embedding_client = runtime.context["embedding_client"]
    retrieved_column_infos: list[ColumnInfo] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        vector = await embedding_client.aembed_query(keyword)          # 文本 → 向量
        columns = await column_qdrant_repo.search(vector, score_threshold=0.6, limit=10)
        for payload in columns:
            col = ColumnInfo(**payload)                                # dict → 实体
            if col.id not in seen_ids:
                seen_ids.add(col.id)                                   # 按 id 去重
                retrieved_column_infos.append(col)

    logger.info(f"字段召回结果: {len(retrieved_column_infos)} 个字段")
    logger.info(f"召回字段: {[c.id for c in retrieved_column_infos]}")
    return {"retrieved_column_infos": retrieved_column_infos}
