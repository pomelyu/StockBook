from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    response_description="成功取得 access token 與 refresh token",
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    以 username / password 登入，取得 JWT token pair。

    - **access_token**：用於所有需要認證的 API 請求，放在 `Authorization: Bearer <token>` header
    - **refresh_token**：access token 過期後，用來換發新的 token pair（呼叫 `POST /auth/refresh`）
    - 帳號不存在或密碼錯誤時回傳 **401**
    - 帳號被停用（`is_active=false`）時回傳 **403**
    """
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    response_description="成功換發新的 access token 與 refresh token",
)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    使用 refresh token 換發新的 token pair。

    - 必須傳入 **refresh_token**（不可用 access_token 呼叫此端點）
    - 成功後同時回傳新的 access token 與 refresh token
    - Token 無效、過期或類型錯誤時回傳 **401**
    """
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise exc
        user_id: str = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc

    import uuid

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise exc

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    response_description="目前登入的使用者資訊",
)
async def me(current_user: User = Depends(get_current_user)):
    """
    回傳目前登入使用者的基本資料。

    - 需在 header 帶有效的 `Authorization: Bearer <access_token>`
    - Token 無效或過期時回傳 **401**
    """
    return current_user
