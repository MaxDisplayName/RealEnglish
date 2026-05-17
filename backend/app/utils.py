import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import UserModel
from app.crud import get_user_by_device_id, get_user_by_id

# ── Security ──
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Dependencies ──
def get_current_user(
    authorization: str = Header(None),
    x_device_id: str = Header(None, alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> UserModel:
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
            if user:
                return user
    if x_device_id:
        user = get_user_by_device_id(db, x_device_id)
        if user:
            return user
    raise HTTPException(status_code=401, detail="未登录，请先登录或提供设备 ID")


def get_optional_user(
    authorization: str = Header(None),
    x_device_id: str = Header(None, alias="X-Device-Id"),
    db: Session = Depends(get_db),
) -> UserModel | None:
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
            if user:
                return user
    if x_device_id:
        user = get_user_by_device_id(db, x_device_id)
        if user:
            return user
    return None


def require_teacher_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可访问此接口")
    return current_user


def require_student_role(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可访问此接口")
    return current_user


def require_bound_student(current_user: UserModel = Depends(require_student_role)) -> UserModel:
    """仅允许已绑定教师的学生访问。"""
    if not current_user.teacher_id:
        raise HTTPException(status_code=403, detail="请绑定教师邀请码后使用此功能")
    return current_user


# ── Level Assigner ──
def assign_level(correct_count: int, total: int = 10) -> str:
    """定级：A=高级(>=75%), B=中级(50-74%), C=初级(<50%)"""
    ratio = correct_count / total
    if ratio >= 0.75:
        return "A"
    elif ratio >= 0.5:
        return "B"
    else:
        return "C"


# ── Device ID ──
def get_device_id(x_device_id: str = Header(None)) -> str | None:
    return x_device_id


# ── File Upload ──
LOCAL_STORAGE_DIR = Path("storage/audio")
logger_upload = logging.getLogger("file_upload")


def _ensure_local_dir():
    LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


async def upload_to_oss(local_path: str, remote_filename: str) -> str | None:
    _ensure_local_dir()
    try:
        dest = LOCAL_STORAGE_DIR / remote_filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        return f"/storage/audio/{remote_filename}"
    except Exception as e:
        logger_upload.error(f"文件上传失败: {e}")
        return None


# ── Logging ──
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logging(app_name: str = "realenglish") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(console)

    all_handler = RotatingFileHandler(os.path.join(LOG_DIR, f"{app_name}.log"), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    all_handler.setLevel(logging.DEBUG)
    all_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d — %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(all_handler)

    error_handler = RotatingFileHandler(os.path.join(LOG_DIR, f"{app_name}_error.log"), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d — %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(error_handler)

    logger = logging.getLogger(app_name)
    logger.info("日志系统初始化完成，日志目录: %s", LOG_DIR)
    return logger
