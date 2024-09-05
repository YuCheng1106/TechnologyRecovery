from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import settings
import os

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    future=True,
    pool_size=10,           # 设置连接池大小
    max_overflow=20,        # 超出连接池大小后的额外连接数
    pool_timeout=30         # 连接池获取连接的超时时间
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


async def get_db_session():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
