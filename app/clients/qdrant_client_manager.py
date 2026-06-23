from qdrant_client import AsyncQdrantClient
from app.conf.app_config import QdrantConfig, app_config

class QdrantClientManager:
    """Qdrant 向量库客户端管理器
    统一封装连接创建、地址拼接、连接关闭能力，全局单例使用
    """
    def __init__(self, config: QdrantConfig):
        """
        初始化管理器
        :param config: Qdrant 连接配置实例
        """
        # Qdrant 客户端实例，初始未连接为 None
        self.client: AsyncQdrantClient | None = None
        # 保存向量库配置信息
        self.config: QdrantConfig = config

    def _get_url(self) -> str:
        """私有方法：拼接 Qdrant 服务完整访问地址"""
        return f"http://{self.config.host}:{self.config.port}"

    def init(self) -> None:
        """创建并初始化 Qdrant 客户端连接"""
        self.client = AsyncQdrantClient(url=self._get_url())

    async def close(self) -> None:
        """关闭客户端连接，释放资源"""
        await self.client.close()

# 基于全局配置实例化管理器，项目全局单例
qdrant_client_manager = QdrantClientManager(app_config.qdrant)
