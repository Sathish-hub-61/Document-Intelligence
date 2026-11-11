"""
SQLAlchemy repository implementations satisfying application ports.
"""
from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from app.application.ports import UserRepoPort
from app.adapters.persistence.models import UserModel
from app.domain.entities import Role, User


class SqlAlchemyUserRepo(UserRepoPort):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, model: UserModel) -> User:
        return User(
            user_id=model.user_id,
            name=model.name,
            email=model.email,
            password_hash=model.password_hash,
            role=model.role if isinstance(model.role, Role) else Role(model.role),
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def create_user(self, user: User) -> User:
        model = UserModel(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        model = self.db.query(UserModel).filter(UserModel.user_id == user_id).first()
        return self._to_domain(model) if model else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        model = self.db.query(UserModel).filter(UserModel.email == email.lower().strip()).first()
        return self._to_domain(model) if model else None

    def list_users(self) -> List[User]:
        models = self.db.query(UserModel).all()
        return [self._to_domain(m) for m in models]
