"""
简化的认证 API
直接在主应用中注册，避免路由注册问题
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT 配置
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 创建路由
auth_router = APIRouter(tags=["Authentication"])


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """初始化认证数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # 创建默认管理员账号
    try:
        password_hash = pwd_context.hash("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", password_hash, "admin")
        )
        print("✅ 创建默认管理员账号：admin / admin123")
    except sqlite3.IntegrityError:
        pass  # 账号已存在
    
    conn.commit()
    conn.close()


def create_access_token(data: Dict[str, Any]) -> str:
    """生成 JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@auth_router.post("/api/auth/login")
async def login(request: Dict[str, Any]):
    """用户登录"""
    username = request.get("username")
    password = request.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    
    if not pwd_context.verify(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 更新最后登录时间
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    
    # 生成 token
    access_token = create_access_token({"sub": row["username"], "role": row["role"]})
    
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": row["username"],
            "role": row["role"]
        }
    }


@auth_router.get("/api/auth/me")
async def get_current_user_info():
    """获取当前用户信息（简化版，实际应使用 JWT）"""
    return {"status": "success", "message": "请使用 JWT token 认证"}


# 初始化数据库
init_auth_db()
