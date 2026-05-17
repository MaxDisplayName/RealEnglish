# RealEnglish 后端代码编写规范

> 本规范适用于项目后端（Python 3.10+ / FastAPI / SQLAlchemy）的所有代码编写，要求 AI 生成的代码严格遵循。

## 1. 技术栈与工具

- **语言**: Python 3.10+
- **框架**: FastAPI
- **ORM**: SQLAlchemy (1.4+，建议使用 2.0 风格)
- **数据库**: PostgreSQL (开发可用 SQLite)
- **迁移工具**: Alembic
- **数据校验**: Pydantic (v2)
- **依赖管理**: pip + requirements.txt (或 Poetry)
- **代码检查**: flake8, black, isort (项目根目录配置)

## 2. 命名规范

| 类型          | 命名规则         | 示例                                    |
| ------------- | ---------------- | --------------------------------------- |
| 文件名        | 小写下划线       | `user_service.py`                       |
| 类名          | PascalCase       | `UserModel`, `QuestionGenerator`        |
| 函数/方法     | 小写下划线       | `get_user_by_id()`, `create_question()` |
| 变量          | 小写下划线       | `user_id`, `is_active`                  |
| 常量          | UPPER_SNAKE_CASE | `MAX_CONNECTIONS`                       |
| 私有属性/方法 | 单下划线开头     | `_internal_call()`                      |

## 3. 代码风格

- 遵循 **PEP 8**。
- 每行最多 88 个字符（与 Black 默认一致）。
- 使用 `black` 自动格式化，`isort` 管理导入顺序。
- 函数和类必须包含 **docstring**（Google 风格或 NumPy 风格）。

```python
def get_user_by_device(db: Session, device_id: str) -> UserModel | None:
    """
    根据设备 ID 获取用户。

    Args:
        db: 数据库会话。
        device_id: 设备唯一标识。

    Returns:
        用户实例或 None。
    """
    return db.query(UserModel).filter(UserModel.device_id == device_id).first()
```

## 4. 类型注解

所有函数参数和返回值必须使用类型注解。

使用 Optional, List, Dict 等（Python 3.9+ 推荐使用内置 list, dict, | None）。

```python
def process_audio(audio_data: bytes, user_id: str) -> dict[str, float]:
    pass
```

## 5. API 设计规范

### 5.1 路由与版本

所有 API 路径以 /api/v1 开头。

资源命名使用复数：/users, /questions。

使用 HTTP 方法语义：

GET：获取资源

POST：创建资源

PUT/PATCH：更新资源

DELETE：删除资源

### 5.2 请求与响应模型

使用 Pydantic 定义请求体 (*Request) 和响应体 (*Response)。

响应统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 5.3 错误处理

使用 HTTP 状态码：400（参数错误），401（未授权），404（不存在），500（内部错误）。

业务异常使用自定义 HTTPException：

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="User not found")
```

## 6. 数据库规范

### 6.1 ORM 模型定义

所有模型继承自 Base（由 declarative_base() 生成）。

表名使用复数小写：users, video_clips。

字段使用 Column 定义，必须指定类型和约束（nullable, default 等）。

```python
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID

class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id = Column(String(36), unique=True, nullable=False, index=True)
    level = Column(String(1), nullable=False, default='B')
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 6.2 事务与会话

每个请求使用独立的数据库会话（依赖注入）。

CRUD 函数接收 Session 参数，不直接创建会话。

使用 db.commit() 和 db.rollback() 显式控制事务。

### 6.3 迁移

所有表结构变更通过 Alembic 生成迁移脚本。

禁止手动修改数据库。

## 7. 核心服务集成规范

### 7.1 DeepSeek API

封装在 core/ai_client.py，提供统一接口：

```python
async def generate_questions(dialogue: str, difficulty: str) -> list[dict]
async def generate_feedback(transcript: str, score: dict) -> str
必须设置超时（httpx.Timeout），并实现重试机制（最多 3 次）。

记录调用日志（请求 token 数，响应等）。
```

### 7.2 讯飞语音评测

WebSocket 签名逻辑封装在 utils/ws_signature.py。

提供异步函数 evaluate_audio(audio_base64: str, reference_text: str) -> dict。

处理可能的网络错误，返回降级结果（评分默认 60 分）。

### 7.3 文件上传（OSS）

口语录音文件先存储到临时目录，再上传 OSS，返回可访问的 URL。

上传失败时记录错误但不中断主流程（仍保存数据库记录，标记音频缺失）。

## 8. 环境变量配置

使用 pydantic_settings 或 python-dotenv 加载 .env。

配置类示例：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    deepseek_api_key: str
    xf_appid: str
    xf_apikey: str
    xf_apisecret: str
    database_url: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## 9. 测试规范

单元测试使用 pytest。

对核心业务函数（定级、出题、评分）必须编写测试。

API 测试使用 httpx.AsyncClient 或 TestClient。

## 10. 日志与监控

使用 logging 模块，配置按等级输出。

生产环境记录 INFO 级别以上日志。

错误日志必须包含请求 ID（可从中间件生成）。

## 11. GIT 提交前检查

运行 black 和 isort 格式化代码。

运行 flake8 检查无严重问题。

确保所有测试通过。

最后更新: 2026-05-02
维护者: RealEnglish 开发团队
