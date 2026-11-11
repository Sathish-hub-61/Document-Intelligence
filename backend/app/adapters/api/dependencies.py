"""
FastAPI authentication and authorization dependencies.
Enforces that user role and active status are read freshly from the database on every request.
"""
from typing import Callable, List
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.adapters.persistence.database import get_db
from app.adapters.persistence.repositories import SqlAlchemyUserRepo
from app.adapters.security.jwt_service import decode_access_token
from app.domain.entities import Role, User
from app.domain.errors import AuthenticationError, ForbiddenError

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts Bearer token from header, decodes user_id, and fetches fresh user
    record from the database. Role is NEVER trusted solely from token payload.
    """
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Missing Authorization header or Bearer token")

    token = credentials.credentials
    user_id = decode_access_token(token)

    repo = SqlAlchemyUserRepo(db)
    user = repo.get_user_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found or deleted")

    if not user.is_active:
        raise AuthenticationError("User account has been deactivated")

    return user


def require_role(*allowed_roles: Role) -> Callable[[User], User]:
    """
    Dependency factory returning a validator that asserts the caller's role
    matches one of the allowed_roles (Admins always pass).
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == Role.ADMIN:
            return current_user
        if current_user.role not in allowed_roles:
            raise ForbiddenError(f"Role '{current_user.role.value}' is not authorized to access this resource")
        return current_user

    return role_checker
