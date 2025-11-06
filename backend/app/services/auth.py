"""
Authentication service for user authentication, JWT token management, and password hashing.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, SubscriptionStatus

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


class AuthService:
    """
    Authentication service for managing user authentication and JWT tokens.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain text password using bcrypt with cost factor 12.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        user_id: UUID,
        email: str,
        subscription_tier: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token for the user.

        Args:
            user_id: User's UUID
            email: User's email
            subscription_tier: User's subscription tier
            expires_delta: Optional custom expiration timedelta

        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Default: 7 days
            expire = datetime.utcnow() + timedelta(days=7)

        to_encode = {
            "sub": str(user_id),  # Subject - user ID
            "email": email,
            "subscription_tier": subscription_tier,
            "exp": expire,
            "iat": datetime.utcnow(),  # Issued at
            "type": "access"
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: UUID) -> str:
        """
        Create a JWT refresh token for the user.
        Refresh tokens have longer expiration (30 days).

        Args:
            user_id: User's UUID

        Returns:
            Encoded JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=30)

        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> dict:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string to verify

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def create_verification_token() -> str:
        """
        Create a secure random token for email verification.

        Returns:
            URL-safe random token string
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        FastAPI dependency to get the current authenticated user.

        Args:
            token: JWT token from Authorization header
            db: Database session

        Returns:
            Current authenticated User object

        Raises:
            HTTPException: If token is invalid or user not found/inactive
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # Verify and decode token
        try:
            payload = AuthService.verify_token(token)
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            if user_id is None:
                raise credentials_exception

            # Ensure it's an access token, not a refresh token
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type. Please use an access token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        except JWTError:
            raise credentials_exception

        # Fetch user from database
        try:
            result = await db.execute(
                select(User).where(User.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

        if user is None:
            raise credentials_exception

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user

    @staticmethod
    async def get_current_verified_user(
        current_user: User = Depends(lambda: AuthService.get_current_user)
    ) -> User:
        """
        FastAPI dependency to get current user and ensure they are verified.

        Args:
            current_user: Current authenticated user

        Returns:
            Verified User object

        Raises:
            HTTPException: If user is not verified
        """
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required. Please verify your email address."
            )
        return current_user

    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.

        Args:
            email: User's email
            password: Plain text password
            db: Database session

        Returns:
            User object if authentication succeeds, None otherwise
        """
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Verify password
        if not AuthService.verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    def get_token_expiration_seconds(token_type: str = "access") -> int:
        """
        Get token expiration time in seconds.

        Args:
            token_type: Type of token ("access" or "refresh")

        Returns:
            Expiration time in seconds
        """
        if token_type == "refresh":
            return 30 * 24 * 60 * 60  # 30 days
        else:
            return 7 * 24 * 60 * 60  # 7 days


# Convenience function for getting current user in routes
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Convenience function to get current user.
    Can be used directly as a FastAPI dependency.
    """
    return await AuthService.get_current_user(token=token, db=db)


async def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Convenience function to get current verified user.
    Can be used directly as a FastAPI dependency.
    """
    return await AuthService.get_current_verified_user(current_user=current_user)
