"""
认证 API 路由
处理登录、登出、用户管理
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any

from core.auth import AuthManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

# 初始化认证管理器
auth_manager = AuthManager()

# JWT Bearer 认证
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """获取当前登录用户"""
    token = credentials.credentials
    payload = auth_manager.verify_token(token)
    
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    user = auth_manager.get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    
    return user


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """要求超级管理员权限"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


@router.post("/api/auth/login")
async def login(request: dict):
    """用户登录"""
    username = request.get("username")
    password = request.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    
    user = auth_manager.authenticate_user(username, password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 更新最后登录时间
    auth_manager.update_last_login(username)
    
    # 生成 JWT token
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "role": user["role"]
        }
    }


@router.post("/api/auth/logout")
async def logout():
    """用户登出（客户端需删除 token）"""
    return {"status": "success", "message": "登出成功"}


@router.get("/api/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "status": "success",
        "user": current_user
    }


@router.post("/api/auth/change_password")
async def change_password(
    request: dict,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """修改密码"""
    old_password = request.get("old_password")
    new_password = request.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="旧密码和新密码不能为空")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少6位")
    
    # 验证旧密码
    user = auth_manager.authenticate_user(current_user["username"], old_password)
    if user is None:
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    # 修改密码
    result = auth_manager.update_user_password(current_user["username"], new_password)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {"status": "success", "message": "密码修改成功"}


# 用户管理接口（仅超级管理员）
@router.get("/api/auth/users")
async def list_users(admin_user: Dict[str, Any] = Depends(require_admin)):
    """列出所有用户"""
    users = auth_manager.list_users()
    return {"status": "success", "users": users}


@router.post("/api/auth/users")
async def create_user(
    request: dict,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """创建用户（仅超级管理员）"""
    username = request.get("username")
    password = request.get("password")
    role = request.get("role", "user")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    
    if role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="角色必须是 'admin' 或 'user'")
    
    result = auth_manager.create_user(username, password, role)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.put("/api/auth/users/{username}")
async def update_user(
    username: str,
    request: dict,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """修改用户信息（仅超级管理员）"""
    new_password = request.get("password")
    is_active = request.get("is_active")
    role = request.get("role")
    
    # 修改密码
    if new_password:
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        result = auth_manager.update_user_password(username, new_password)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
    
    # 修改状态
    if is_active is not None:
        result = auth_manager.update_user_status(username, is_active)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
    
    return {"status": "success", "message": "用户信息更新成功"}


@router.delete("/api/auth/users/{username}")
async def delete_user(
    username: str,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """删除用户（仅超级管理员）"""
    result = auth_manager.delete_user(username)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result
