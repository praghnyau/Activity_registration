import enum
from datetime import datetime
from sqlalchemy import Enum, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RegistrationStatus(str, enum.Enum):
    registered = "registered"
    withdrawn = "withdrawn"
    cancelled = "cancelled"


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("student_id", "activity_id", name="uq_registration_student_activity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[RegistrationStatus] = mapped_column(Enum(RegistrationStatus), nullable=False, default=RegistrationStatus.registered)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    student: Mapped["User"] = relationship(back_populates="registrations")
    activity: Mapped["Activity"] = relationship(back_populates="registrations")
