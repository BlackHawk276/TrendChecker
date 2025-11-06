"""
Authentication router for user registration, login, and token management.
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, SubscriptionTier, SubscriptionStatus
from app.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ErrorResponse,
    MessageResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import AuthService, get_current_user

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    }
)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Strong password (min 8 chars, uppercase, number, special char)
    - **full_name**: User's full name

    Creates a user with:
    - Free tier subscription
    - 14-day trial period
    - Email verification token
    - Auto-generated API key
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = AuthService.hash_password(user_data.password)

    # Create new user
    new_user = User(
        id=uuid.uuid4(),
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        subscription_tier=SubscriptionTier.FREE,
        subscription_status=SubscriptionStatus.TRIALING,
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
        searches_limit=settings.get_search_limit("free"),
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

    # Generate tokens
    access_token = AuthService.create_access_token(
        user_id=new_user.id,
        email=new_user.email,
        subscription_tier=new_user.subscription_tier.value
    )

    refresh_token = AuthService.create_refresh_token(user_id=new_user.id)

    # TODO: Send verification email with token
    # verification_token = AuthService.create_verification_token()
    # Store verification_token in database or cache
    # Send email with verification link

    return AuthResponse(
        user=UserResponse.model_validate(new_user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=AuthService.get_token_expiration_seconds("access")
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
    }
)
async def login(
    credentials: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """
    Login with email and password.

    Returns access token, refresh token, and user information.
    """
    # Authenticate user
    user = await AuthService.authenticate_user(
        email=credentials.email,
        password=credentials.password,
        db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        # Don't fail login if timestamp update fails
        pass

    # Generate tokens
    access_token = AuthService.create_access_token(
        user_id=user.id,
        email=user.email,
        subscription_tier=user.subscription_tier.value
    )

    refresh_token = AuthService.create_refresh_token(user_id=user.id)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=AuthService.get_token_expiration_seconds("access")
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    }
)
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using a refresh token.

    Returns a new access token.
    """
    try:
        # Verify refresh token
        payload = AuthService.verify_token(token_data.refresh_token)
        token_type = payload.get("type")

        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Please use a refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch user from database
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate new access token
        access_token = AuthService.create_access_token(
            user_id=user.id,
            email=user.email,
            subscription_tier=user.subscription_tier.value
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=AuthService.get_token_expiration_seconds("access")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user information.

    Requires valid access token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def logout(
    current_user: User = Depends(get_current_user)
) -> MessageResponse:
    """
    Logout current user.

    Note: With JWT tokens, the token remains valid until expiration.
    For complete logout, implement token blacklisting with Redis.

    Client should discard the token after logout.
    """
    # TODO: If using Redis, add token to blacklist
    # redis_client.setex(f"blacklist:{token}", expiration, "1")

    return MessageResponse(
        message="Successfully logged out. Please discard your tokens."
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid verification token"},
        404: {"model": ErrorResponse, "description": "Token not found or expired"},
    }
)
async def verify_email(
    verification_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Verify user's email address using verification token.

    The verification token should be sent to the user's email during registration.
    """
    # TODO: Implement token storage and validation
    # This is a placeholder implementation

    # In production, you would:
    # 1. Store verification tokens in database or Redis with user_id and expiration
    # 2. Look up the token
    # 3. Verify it hasn't expired
    # 4. Mark user as verified

    # For now, we'll accept any token and mark the current user as verified
    # You should implement proper token storage and validation

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email verification not fully implemented. Requires token storage system."
    )

    # Example implementation:
    # token_data = await get_verification_token_from_redis(verification_data.verification_token)
    # if not token_data:
    #     raise HTTPException(status_code=404, detail="Token not found or expired")
    #
    # result = await db.execute(select(User).where(User.id == token_data.user_id))
    # user = result.scalar_one_or_none()
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")
    #
    # user.is_verified = True
    # await db.commit()
    #
    # return MessageResponse(message="Email verified successfully")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid current password"},
    }
)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Change user's password.

    Requires:
    - Valid access token
    - Current password for verification
    - New password meeting strength requirements
    """
    # Verify current password
    if not AuthService.verify_password(
        password_data.current_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Hash new password
    new_hashed_password = AuthService.hash_password(password_data.new_password)

    # Update password
    current_user.hashed_password = new_hashed_password
    current_user.updated_at = datetime.utcnow()

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )

    return MessageResponse(
        message="Password changed successfully. Please login with your new password."
    )


@router.post(
    "/regenerate-api-key",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    }
)
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Regenerate user's API key.

    This will invalidate the old API key.
    """
    new_api_key = current_user.regenerate_api_key()

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate API key: {str(e)}"
        )

    return MessageResponse(
        message=f"API key regenerated successfully. New key: {new_api_key}"
    )
