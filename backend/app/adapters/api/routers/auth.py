"""
Authentication API endpoints matching Blueprint Section 8.1.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.api.dependencies import get_current_user, require_role
from app.adapters.api.schemas.common import LoginRequest, TokenResponse, UserCreate, UserOut
from app.adapters.persistence.database import get_db
from app.adapters.persistence.repositories import SqlAlchemyUserRepo
from app.adapters.security.jwt_service import create_access_token
from app.adapters.security.password import hash_password, verify_password
from app.domain.entities import Role, User
from app.domain.errors import AuthenticationError, ValidationError

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    repo = SqlAlchemyUserRepo(db)
    user = repo.get_user_by_email(request.email)
    if not user:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("User account has been deactivated")

    token = create_access_token(user.user_id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/register", response_model=UserOut)
def register(
    request: UserCreate,
    current_admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    repo = SqlAlchemyUserRepo(db)
    existing = repo.get_user_by_email(request.email)
    if existing:
        raise ValidationError("User with this email already exists")

    hashed = hash_password(request.password)
    user = User(
        name=request.name,
        email=request.email.lower().strip(),
        password_hash=hashed,
        role=request.role,
    )
    saved = repo.create_user(user)
    return UserOut(
        user_id=saved.user_id,
        name=saved.name,
        email=saved.email,
        role=saved.role,
        is_active=saved.is_active,
        created_at=saved.created_at,
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        user_id=current_user.user_id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
