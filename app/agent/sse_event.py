"""SSE 事件格式化工具，生成前端可消费的结构化进度/结果/错误事件"""
import json


def progress(step: str, status: str) -> str:
    """status: running | success | error"""
    return json.dumps({"type": "progress", "step": step, "status": status}, ensure_ascii=False)


def result(data: list) -> str:
    return json.dumps({"type": "result", "data": data}, ensure_ascii=False)


def error(message: str) -> str:
    return json.dumps({"type": "error", "message": message}, ensure_ascii=False)
