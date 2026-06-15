from dataclasses import dataclass
from pathlib import Path

from omegaconf import OmegaConf


# ==================== 1. 基础配置子类定义 ====================

@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str

@dataclass
class Console:
    enable: bool
    level: str

@dataclass
class LoggingConfig:
    file: File
    console: Console

# 数据库配置
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int

@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str

@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str

@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str

# ==================== 2. 根配置根类定义 ====================

@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig

# ==================== 3. OmegaConf 加载与强类型转化 ====================

# 定位 yaml 文件的绝对路径（当前文件往上跳两级下的 conf/app_config.yaml）
config_file = Path(__file__).parents[2] / 'conf' / 'app_config.yaml'

# 加载原始的 yaml 字典内容
context = OmegaConf.load(config_file)

# 基于 dataclass 生成强类型的结构化 Schema
schema = OmegaConf.structured(AppConfig)

# 合并 Schema 与真实数据，并一步到位转化为纯正的、带智能提示的 AppConfig 对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

# ==================== 4. 测试打印（验证提取是否成功） ====================
if __name__ == "__main__":
    print(f"成功加载数据库 dw: {app_config.db_dw.database}")
    print(f"大模型名称: {app_config.llm.model_name}")
    print(f"日志级别: {app_config.logging.file.level}")
