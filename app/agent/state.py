from typing import TypedDict


class DataAgentState(TypedDict, total=False):
    query: str       # 用户的自然语言查询
    keywords: str    # 提取的关键词
    error: str       # 校验SQL输出的错误信息