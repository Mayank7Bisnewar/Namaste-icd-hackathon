"""
OAuth 2.0 Authentication System with Mock ABHA Integration

This module provides authentication and authorization functionality including
JWT token management, password hashing, and mock ABHA OAuth 2.0 integration.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import User, get_db

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    """JWT Token response model"""
    access_token: str
    token_type: str
    expires_in: int
    abha_id: Optional[str] = None
    user_id: Optional[int] = None


class TokenData(BaseModel):
    """JWT Token data model"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    abha_id: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: str
    full_name: str
    password: str
    abha_id: Optional[str] = None


class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    abha_id: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]


class ABHATokenRequest(BaseModel):
    """ABHA Token request model"""
    abha_id: str
    auth_method: str = "otp"  # otp, password, biometric
    otp: Optional[str] = None
    password: Optional[str] = None


class ABHAUserInfo(BaseModel):
    """ABHA User info model"""
    abha_id: str
    name: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    address: Optional[Dict[str, Any]] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Try bcrypt first
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback to simple SHA256 for demo
        import hashlib
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_access_token(token: str) -> Optional[TokenData]:
    """Verify and decode a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        abha_id: str = payload.get("abha_id")
        role: str = payload.get("role")
        
        if username is None:
            return None
        
        token_data = TokenData(
            username=username,
            user_id=user_id,
            abha_id=abha_id,
            role=role
        )
        return token_data
    except jwt.PyJWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user with username/password"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_access_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return current_user
    
    return role_checker


class ABHAAuthService:
    """Mock ABHA Authentication Service"""
    
    def __init__(self):
        self.base_url = os.getenv("ABHA_BASE_URL", "https://dev.abdm.gov.in")
        self.client_id = os.getenv("ABHA_CLIENT_ID", "mock_client_id")
        self.client_secret = os.getenv("ABHA_CLIENT_SECRET", "mock_client_secret")
        self.redirect_uri = os.getenv("ABHA_REDIRECT_URI", "http://localhost:8000/auth/callback")
        
        # Mock user database for demo
        self.mock_users = {
            "14-1234-5678-9012": {
                "abha_id": "14-1234-5678-9012",
                "name": "Rajesh Kumar",
                "email": "rajesh.kumar@example.com",
                "mobile": "+91-9876543210",
                "gender": "M",
                "birth_year": 1985,
                "address": {
                    "state": "Karnataka",
                    "district": "Bangalore",
                    "pincode": "560001"
                }
            },
            "14-5678-9012-3456": {
                "abha_id": "14-5678-9012-3456",
                "name": "Priya Sharma",
                "email": "priya.sharma@example.com",
                "mobile": "+91-9876543211",
                "gender": "F",
                "birth_year": 1990,
                "address": {
                    "state": "Maharashtra",
                    "district": "Mumbai",
                    "pincode": "400001"
                }
            },
            "14-9012-3456-7890": {
                "abha_id": "14-9012-3456-7890",
                "name": "Dr. Amit Patel",
                "email": "amit.patel@hospital.com",
                "mobile": "+91-9876543212",
                "gender": "M",
                "birth_year": 1975,
                "address": {
                    "state": "Gujarat",
                    "district": "Ahmedabad",
                    "pincode": "380001"
                }
            }
        }
    
    def get_authorization_url(self, state: str) -> str:
        """Get ABHA OAuth authorization URL"""
        # In real implementation, this would redirect to ABHA OAuth server
        return f"{self.base_url}/oauth2/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={state}&scope=profile"
    
    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access token (mock implementation)"""
        # Mock token response
        if code.startswith("mock_code_"):
            abha_id = code.replace("mock_code_", "")
            if abha_id in self.mock_users:
                return {
                    "access_token": f"abha_token_{abha_id}",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "profile",
                    "abha_id": abha_id
                }
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization code"
        )
    
    async def get_user_info(self, access_token: str) -> ABHAUserInfo:
        """Get user info from ABHA token (mock implementation)"""
        if access_token.startswith("abha_token_"):
            abha_id = access_token.replace("abha_token_", "")
            if abha_id in self.mock_users:
                user_data = self.mock_users[abha_id]
                return ABHAUserInfo(**user_data)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ABHA token"
        )
    
    async def authenticate_with_otp(self, abha_id: str, otp: str) -> Dict[str, Any]:
        """Authenticate user with ABHA ID and OTP (mock implementation)"""
        # Mock OTP validation (any 6-digit OTP is valid for demo)
        if len(otp) == 6 and otp.isdigit() and abha_id in self.mock_users:
            return {
                "access_token": f"abha_token_{abha_id}",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "profile",
                "abha_id": abha_id
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ABHA ID or OTP"
        )


class UserService:
    """User service for managing users"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if username already exists
        if self.db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        if self.db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if ABHA ID already exists
        if user_data.abha_id and self.db.query(User).filter(User.abha_id == user_data.abha_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ABHA ID already registered"
            )
        
        # Create new user
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            abha_id=user_data.abha_id,
            hashed_password=get_password_hash(user_data.password),
            is_active=True,
            is_verified=bool(user_data.abha_id)  # Auto-verify if ABHA ID provided
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_user_by_abha_id(self, abha_id: str) -> Optional[User]:
        """Get user by ABHA ID"""
        return self.db.query(User).filter(User.abha_id == abha_id).first()
    
    def link_abha_id(self, user_id: int, abha_id: str) -> User:
        """Link ABHA ID to existing user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if ABHA ID already exists
        if self.db.query(User).filter(User.abha_id == abha_id, User.id != user_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ABHA ID already linked to another account"
            )
        
        user.abha_id = abha_id
        user.is_verified = True
        self.db.commit()
        self.db.refresh(user)
        
        return user


# Initialize ABHA service
abha_service = ABHAAuthService()


def create_token_response(user: User) -> Token:
    """Create token response for user"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "abha_id": user.abha_id,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        abha_id=user.abha_id,
        user_id=user.id
    )
