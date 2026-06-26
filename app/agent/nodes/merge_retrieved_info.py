import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.sse_event import progress
from app.agent.state import DataAgentState
from app.core.log import logger
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer(progress("合并召回信息", "running"))

    retrieved_column_infos = state["retrieved_column_infos"]
    retrieved_metric_infos = state["retrieved_metric_infos"]
    retrieved_value_infos = state["retrieved_value_infos"]

    # --- 1. 收集所有需要的字段 ID ---
    column_ids: set[str] = {c.id for c in retrieved_column_infos}
    for metric in retrieved_metric_infos:
        for col_id in metric.relevant_columns:
            column_ids.add(col_id)

    table_ids: set[str] = {c.table_id for c in retrieved_column_infos}

    # --- 2. 从 MySQL 拿完整的字段和表信息 ---
    meta_mgr = runtime.context["meta_mysql_client_manager"]
    async with meta_mgr.session_factory() as session:
        repo = MetaMySQLRepository(session)

        columns = await repo.get_column_infos_by_ids(list(column_ids))
        tables = await repo.get_table_infos_by_ids(list(table_ids))

        # 拉取每张表的所有字段（补全主键、外键）
        all_columns: list = list(columns)
        existing_col_ids = {c.id for c in all_columns}
        for tid in table_ids:
            full_columns = await repo.get_all_columns_by_table_id(tid)
            for col in full_columns:
                if col.id not in existing_col_ids:
                    all_columns.append(col)
                    existing_col_ids.add(col.id)

    table_info_map = {t.id: t for t in tables}
    logger.info(f"MySQL 补全: {len(all_columns)} 个字段(含主外键), {len(tables)} 张表")

    # --- 3. 取值按 column_id 分组 ---
    value_map: dict[str, list[str]] = {}
    for v in retrieved_value_infos:
        value_map.setdefault(v.column_id, []).append(v.value)

    # --- 4. 按表分组，组装 table_infos ---
    table_map: dict[str, dict] = {}
    for col in all_columns:
        tid = col.table_id
        table = table_info_map.get(tid)

        if tid not in table_map:
            table_map[tid] = {
                "name": tid,
                "role": table.role if table else "",
                "description": table.description if table else "",
                "columns": [],
            }

        examples = list(set(col.examples + value_map.get(col.id, [])))
        col_state = {
            "name": col.name,
            "type": col.type,
            "role": col.role,
            "examples": examples,
            "description": col.description,
            "alias": col.alias,
        }
        table_map[tid]["columns"].append(col_state)

    table_infos = list(table_map.values())
    logger.info(f"合并结果: {len(table_infos)} 张表, {len(retrieved_metric_infos)} 个指标")

    # --- 5. 构建 metric_infos ---
    metric_infos = [
        {"name": m.name, "description": m.description, "relevant_columns": m.relevant_columns, "alias": m.alias}
        for m in retrieved_metric_infos
    ]

    writer(progress("合并召回信息", "success"))
    return {"table_infos": table_infos, "metric_infos": metric_infos}
