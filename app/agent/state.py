from typing import TypedDict, List

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo

class ColumnInfoState(TypedDict):
    name: str
    type: str
    role: str
    examples: list
    description: str
    alias: List[str]
class TableInfoState(TypedDict):
    name: str
    role: str
    description: str
    columns: List[ColumnInfoState]

class MetricInfoState(TypedDict):
    name: str
    description: str
    relevant_columns: List[str]
    alias: List[str]

class DateInfoState(TypedDict):
    date: str
    weekday: str
    quarter: str

class DBInfoState(TypedDict):
    dialect: str
    version: str

class DataAgentState(TypedDict, total=False):
    query: str                            # 用户的自然语言查询
    keywords: list[str]                   # 提取的关键词
    retrieved_column_infos: list[ColumnInfo]   # 召回的字段列表
    retrieved_metric_infos: list[MetricInfo]   # 召回的指标列表
    retrieved_value_infos: list[ValueInfo]     # 召回的字段取值列表

    table_infos: list[TableInfoState]
    metric_infos: list[MetricInfoState]

    date_info: DateInfoState
    db_info: DBInfoState

    sql: str          # 生成的 SQL
    result: list[dict]  # SQL 执行结果

    error: str                            # 校验SQL输出的错误信息