import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    database_url: str = "sqlite:///./reelenglish.db"

    # JWT / 认证
    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    access_token_expire_days: int = 7

    # DeepSeek (兼容 OpenAI SDK, 用 openai_api_key 名让 LangSmith 也能读取)
    openai_api_key: str
    deepseek_api_base: str = "https://api.deepseek.com/v1"

    # 科大讯飞
    xf_appid: str = ""
    xf_api_key: str = ""
    xf_api_secret: str = ""

    # LangSmith 监控
    langsmith_tracing: bool = True
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "RealEnglish"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# LangChain/LangSmith 自动追踪从 os.environ 读取配置，
# 因此需要将 pydantic-settings 加载的值回写到环境变量
os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
if settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
if settings.langsmith_endpoint:
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
