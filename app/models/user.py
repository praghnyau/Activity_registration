import enum
from datetime import datetime
from sqlalchemy import String, Enum, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    administrator = "administrator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    # Bumped on password change. Sessions are signed cookies with no server-side
    # store, so this is what makes "log out other sessions" possible: a cookie
    # carrying an older version is rejected.
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    registrations: Mapped[list["Registration"]] = relationship(back_populates="student")
    group_memberships: Mapped[list["GroupMember"]] = relationship(back_populates="student")
    created_activities: Mapped[list["Activity"]] = relationship(back_populates="created_by_user")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
