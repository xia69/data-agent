import sys
from pathlib import Path
from loguru import logger
from app.conf.app_config import app_config

# 定义统一的日志输出格式
# <green>...</green> 等标签用于在支持颜色的控制台中高亮显示特定字段
# {time}: 精确到毫秒的时间戳
# {level: <8}: 日志级别（如 INFO, DEBUG），左对齐并占用 8 个字符宽度，保证日志整齐
# {name}:{function}:{line}: 触发日志的模块名、函数名和所在行号，方便快速定位代码
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 【关键操作】移除 loguru 默认初始化的处理器
# loguru 在导入时会自动配置一个向控制台输出的默认 handler。
# 必须先 remove 掉，否则后面加上我们自定义的控制台 handler 时，同一条日志会被打印两次。
logger.remove()

# ==========================================
# 1. 配置控制台（终端）日志输出
# ==========================================
if app_config.logging.console.enable:
    logger.add(
        sink=sys.stdout,  # 输出目标：标准输出流（即终端控制台）
        level=app_config.logging.console.level,  # 触发级别：低于此级别的日志将被忽略（例如配了 INFO，就不会打印 DEBUG）
        format=log_format  # 使用上方定义的格式
    )

# ==========================================
# 2. 配置持久化文件日志输出
# ==========================================
if app_config.logging.file.enable:
    # 将配置文件中的路径字符串转换为 Path 对象，更优雅地处理跨平台路径分隔符
    path = Path(app_config.logging.file.path)
    # 确保日志存储目录存在
    # parents=True: 递归创建多层父目录；exist_ok=True: 如果目录已存在则不报错
    path.mkdir(parents=True, exist_ok=True)

    logger.add(
        sink=path / "app.log",  # 输出目标：拼接出具体的日志文件名（如 logs/app.log）
        level=app_config.logging.file.level,  # 文件日志的触发级别（通常可以比控制台存得更全一些）
        format=log_format,
        rotation=app_config.logging.file.rotation,  # 日志轮转策略：文件多大时切割（如 "500 MB"）或何时切割（如 "00:00" 每天午夜）
        retention=app_config.logging.file.retention,  # 日志清理策略：旧日志保留多久（如 "10 days" 超过 10 天的旧文件会被自动删除）
        encoding="utf-8"  # 强制指定 utf-8 编码，防止记录中文时出现乱码
    )