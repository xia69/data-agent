from typing import TypedDict

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class DataAgentState(TypedDict, total=False):
    query: str                            # 用户的自然语言查询
    keywords: list[str]                   # 提取的关键词
    retrieved_column_infos: list[ColumnInfo]   # 召回的字段列表
    retrieved_metric_infos: list[MetricInfo]   # 召回的指标列表
    retrieved_value_infos: list[ValueInfo]     # 召回的字段取值列表
    error: str                            # 校验SQL输出的错误信息