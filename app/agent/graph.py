"""
DataAgent 的 LangGraph 工作流图定义
=====================================
这个文件是整个 Agent 的"骨架"——定义了节点（做什么）以及后续的边（谁先谁后）。
"""
from pathlib import Path

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agent.context import DataAgentContext
from app.agent.nodes import (
    add_extra_context,
    correct_sql,
    extract_keywords,
    filter_metric,
    filter_table,
    generate_sql,
    merge_retrieved_info,
    recall_column,
    recall_metric,
    recall_value,
    run_sql,
    validate_sql,
)
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.qdrant.column_qdrant_repo import ColumnQdrantRepository

# StateGraph: LangGraph 的核心构造器
#   - state_schema: 共享状态结构，所有节点都能读写
#   - context_schema: 运行时注入的资源（LLM 客户端、向量库连接等），只读、一次注入
graph_builder = StateGraph(state_schema=DataAgentState, context_schema=DataAgentContext)
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("filter_table", filter_table)
graph_builder.add_node("filter_metric", filter_metric)
graph_builder.add_node("recall_column", recall_column)
graph_builder.add_node("recall_metric", recall_metric)
graph_builder.add_node("recall_value", recall_value)
graph_builder.add_node("merge_retrieved_info", merge_retrieved_info)
graph_builder.add_node("add_extra_context", add_extra_context)
graph_builder.add_node("generate_sql", generate_sql)
graph_builder.add_node("validate_sql", validate_sql)
graph_builder.add_node("correct_sql", correct_sql)
graph_builder.add_node("run_sql", run_sql)
# edge
graph_builder.add_edge(START, "extract_keywords")
graph_builder.add_edge("extract_keywords", "recall_column")
graph_builder.add_edge("extract_keywords", "recall_value")
graph_builder.add_edge("extract_keywords", "recall_metric")
graph_builder.add_edge("recall_column", "merge_retrieved_info")
graph_builder.add_edge("recall_value", "merge_retrieved_info")
graph_builder.add_edge("recall_metric", "merge_retrieved_info")
graph_builder.add_edge("merge_retrieved_info", "filter_table")
graph_builder.add_edge("merge_retrieved_info", "filter_metric")
graph_builder.add_edge("filter_table", "add_extra_context")
graph_builder.add_edge("filter_metric", "add_extra_context")
graph_builder.add_edge("add_extra_context", "generate_sql")
graph_builder.add_edge("generate_sql", "validate_sql")
# 条件edge
graph_builder.add_conditional_edges(
                    source="validate_sql",
                    path=lambda state: "correct_sql" if state.get('error') else "run_sql",
                    path_map={"run_sql":"run_sql", "correct_sql":"correct_sql"})

graph_builder.add_edge("correct_sql", "run_sql")
graph_builder.add_edge("run_sql", END)

# 编译
graph = graph_builder.compile()
# png_bytes = graph.get_graph().draw_mermaid_png()
# Path("agent_graph.png").write_bytes(png_bytes)
# print("流程图已保存: agent_graph.png")

if __name__ == '__main__':
    import asyncio

    async def test():

        # 引入基建
        qdrant_client_manager.init()
        embedding_client_manager.init()

        state = DataAgentState(query="华北地区销售总额")
        context = DataAgentContext(
            column_qdrant_repository=ColumnQdrantRepository(qdrant_client_manager.client),
            embedding_client=embedding_client_manager.client,
        )

        print("开始测试 Agent 图...")
        async for chunk in graph.astream(state, context=context, stream_mode="custom"):
            if chunk:
                print(chunk)

        print("测试完毕")
        await qdrant_client_manager.close()

    asyncio.run(test())