from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.db import engine, seed_database
from app.models import Base
from app.utils import setup_logging

logger = setup_logging()

app = FastAPI(
    title="RealEnglish API",
    version="0.1.0",
    description="AI 驱动的英语视听说学习平台",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup():
    logger.info("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("开始数据库初始化...")
    await seed_database()
    logger.info("启动完成")


@app.get("/")
def root():
    return {"message": "RealEnglish API is running", "version": "0.1.0"}
