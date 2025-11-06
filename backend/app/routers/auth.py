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
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth import AuthService, get_current_user
from app.services.email_service import EmailService
from app.services.redis_service import RedisService

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

    # Generate and store verification token
    verification_token = AuthService.create_verification_token()
    await RedisService.store_verification_token(
        user_id=str(new_user.id),
        token=verification_token,
        expires_in=86400  # 24 hours
    )

    # Send verification email (async, non-blocking)
    try:
        await EmailService.send_verification_email(
            to_email=new_user.email,
            full_name=new_user.full_name or new_user.email,
            verification_token=verification_token
        )
    except Exception as e:
        # Log error but don't fail registration
        print(f"Failed to send verification email: {str(e)}")

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
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user)
) -> MessageResponse:
    """
    Logout current user and blacklist the token.

    The token will be added to Redis blacklist and will no longer be valid.
    """
    from app.services.auth import oauth2_scheme

    # Calculate token expiration
    expiration = AuthService.get_token_expiration_seconds("access")

    # Blacklist the token
    await RedisService.blacklist_token(token, expiration)

    return MessageResponse(
        message="Successfully logged out. Your token has been invalidated."
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

    The verification token is sent to the user's email during registration.
    """
    # Get user_id from verification token
    user_id_str = await RedisService.get_verification_token(
        verification_data.verification_token
    )

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification token not found or expired"
        )

    # Get user from database
    try:
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id_str))
        )
        user = result.scalar_one_or_none()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already verified
    if user.is_verified:
        return MessageResponse(message="Email already verified")

    # Mark user as verified
    user.is_verified = True
    user.updated_at = datetime.utcnow()

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify email: {str(e)}"
        )

    # Delete the verification token
    await RedisService.delete_verification_token(verification_data.verification_token)

    return MessageResponse(message="Email verified successfully")


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

    # Send confirmation email
    try:
        await EmailService.send_password_changed_email(
            to_email=current_user.email,
            full_name=current_user.full_name or current_user.email
        )
    except Exception as e:
        print(f"Failed to send password changed email: {str(e)}")

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


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Email not found"},
    }
)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Request password reset for a user.

    Sends a password reset email with a token to the user's email address.
    The token expires in 1 hour.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request_data.email)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    # But only send email if user exists
    if user:
        # Generate reset token
        reset_token = AuthService.create_verification_token()

        # Store reset token in Redis
        await RedisService.store_reset_token(
            user_id=str(user.id),
            token=reset_token,
            expires_in=3600  # 1 hour
        )

        # Send password reset email
        try:
            await EmailService.send_password_reset_email(
                to_email=user.email,
                full_name=user.full_name or user.email,
                reset_token=reset_token
            )
        except Exception as e:
            print(f"Failed to send password reset email: {str(e)}")

    return MessageResponse(
        message="If your email is registered, you will receive a password reset link shortly."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired reset token"},
        404: {"model": ErrorResponse, "description": "Token not found"},
    }
)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Reset user's password using reset token.

    The reset token is sent to the user's email via the forgot-password endpoint.
    Tokens expire after 1 hour.
    """
    # Get user_id from reset token
    user_id_str = await RedisService.get_reset_token(reset_data.reset_token)

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset token not found or expired"
        )

    # Get user from database
    try:
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id_str))
        )
        user = result.scalar_one_or_none()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Hash new password
    new_hashed_password = AuthService.hash_password(reset_data.new_password)

    # Update password
    user.hashed_password = new_hashed_password
    user.updated_at = datetime.utcnow()

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )

    # Delete the reset token
    await RedisService.delete_reset_token(reset_data.reset_token)

    # Send confirmation email
    try:
        await EmailService.send_password_changed_email(
            to_email=user.email,
            full_name=user.full_name or user.email
        )
    except Exception as e:
        print(f"Failed to send password changed email: {str(e)}")

    return MessageResponse(
        message="Password reset successfully. You can now login with your new password."
    )
