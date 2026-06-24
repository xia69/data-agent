from typing import TypedDict

from app.entities.column_info import ColumnInfo


class DataAgentState(TypedDict, total=False):
    query: str                   # 用户的自然语言查询
    keywords: list[str]          # 提取的关键词
    retrieved_column_infos: list[ColumnInfo]  # 召回的字段列表
    error: str                   # 校验SQL输出的错误信息