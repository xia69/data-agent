"""
DataAgent 的 LangGraph 工作流图定义
=====================================
这个文件是整个 Agent 的"骨架"——定义了节点（做什么）以及后续的边（谁先谁后）。
"""

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

# StateGraph: LangGraph 的核心构造器
#   - state_schema: 共享状态结构，所有节点都能读写
#   - context_schema: 运行时注入的资源（LLM 客户端、向量库连接等），只读、一次注入
graph_builder = StateGraph(state_schema=DataAgentState, context_schema=DataAgentContext)
# 加节点
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
# 加边
