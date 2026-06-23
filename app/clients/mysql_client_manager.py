import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker  # 引入异步 session 工厂
)
from app.conf.app_config import DBConfig, app_config


class MysqlClientManager(object):
    def __init__(self, config: DBConfig):
        # 维护engine，底层会创建数据库连接池
        self.engine: AsyncEngine | None = None
        # 维护 session 工厂，提供统一的配置
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.config: DBConfig = config

    def _get_url(self):
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"

    def init(self):
        # 1. 创建 Engine
        self.engine = create_async_engine(self._get_url(), pool_size=20)

        # 2. 创建 Session 工厂
        # bind 绑定 engine，统一配置 autoflush 和 expire_on_commit
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=True,
            expire_on_commit=False
        )

    async def close(self):
        """关闭数据库连接并释放连接池资源"""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            print("[OK] 数据库连接池已安全关闭")

    def get_session(self) -> async_sessionmaker[AsyncSession]:
        """安全获取 session_factory 的方法"""
        if self.session_factory is None:
            raise RuntimeError("🚨 数据库连接池尚未初始化！请确保在应用启动时先调用了 .init() 方法。")
        return self.session_factory


# 一个dw数仓，一个元数据
meta_mysql_client_manager = MysqlClientManager(app_config.db_meta)
dw_mysql_client_manager = MysqlClientManager(app_config.db_dw)

# test数据库连接
if __name__ == '__main__':
    dw_mysql_clientManager.init()

    async def test():
        # 3. 业务代码中，直接调用工厂方法即可生成带有预设配置的 session
        async with dw_mysql_clientManager.get_session()() as session:
            sql = "select * from fact_order limit 5"  # 加个 limit 稍微保护一下测试输出
            result = await session.execute(text(sql))
            rows = result.fetchall()

            if rows:
                print(rows[0])
                print(rows[1])
            else:
                print("⚠️ 查无数据")
    asyncio.run(test())