# -*- coding: utf-8 -*-
"""
用户认证模块
支持 JWT 认证，所有账号由超级管理员内设
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# JWT 配置
SECRET_KEY = secrets.token_hex(32)  # 生产环境应存储在环境变量中
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 天

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthManager:
    """用户认证管理器"""
    
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',  -- 'admin' 或 'user'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # 创建默认超级管理员账号（如果不存在）
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            admin_password = self.get_password_hash("admin123")  # 默认密码，首次登录后必须修改
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", admin_password, "admin")
            )
            logger.info("创建默认超级管理员账号：admin / admin123")
        
        conn.commit()
        conn.close()
    
    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_user(self, username: str, password: str, role: str = "user") -> Dict[str, Any]:
        """创建用户（仅超级管理员可调用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            password_hash = self.get_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            conn.commit()
            
            user_id = cursor.lastrowid
            return {
                "status": "success",
                "user_id": user_id,
                "username": username,
                "role": role
            }
        except sqlite3.IntegrityError:
            return {
                "status": "error",
                "message": "用户名已存在"
            }
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户登录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        user_id, username, password_hash, role, is_active = row
        
        if not is_active:
            return None
        
        if not self.verify_password(password, password_hash):
            return None
        
        return {
            "id": user_id,
            "username": username,
            "role": role
        }
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """生成 JWT token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return payload
        except JWTError:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, role, created_at, last_login, is_active FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "username": row[1],
            "role": row[2],
            "created_at": row[3],
            "last_login": row[4],
            "is_active": bool(row[5])
        }
    
    def list_users(self) -> list:
        """列出所有用户（仅超级管理员可调用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, username, role, created_at, last_login, is_active FROM users ORDER BY id"
        )
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "created_at": row[3],
                "last_login": row[4],
                "is_active": bool(row[5])
            })
        
        return users
    
    def update_user_password(self, username: str, new_password: str) -> Dict[str, Any]:
        """修改用户密码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self.get_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (password_hash, username)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return {"status": "error", "message": "用户不存在"}
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "密码修改成功"}
    
    def update_user_status(self, username: str, is_active: bool) -> Dict[str, Any]:
        """启用/禁用用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET is_active = ? WHERE username = ?",
            (1 if is_active else 0, username)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return {"status": "error", "message": "用户不存在"}
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "用户状态更新成功"}
    
    def update_last_login(self, username: str):
        """更新最后登录时间"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
            (username,)
        )
        
        conn.commit()
        conn.close()
    
    def delete_user(self, username: str) -> Dict[str, Any]:
        """删除用户（仅超级管理员可调用）"""
        if username == "admin":
            return {"status": "error", "message": "不能删除超级管理员账号"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        
        if cursor.rowcount == 0:
            conn.close()
            return {"status": "error", "message": "用户不存在"}
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "用户删除成功"}

