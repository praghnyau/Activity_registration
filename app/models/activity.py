import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, Enum, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ActivityStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    full = "full"
    registration_closed = "registration_closed"
    groups_proposed = "groups_proposed"
    groups_formed = "groups_formed"
    cancelled = "cancelled"
    completed = "completed"


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_size: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    formation_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ActivityStatus] = mapped_column(Enum(ActivityStatus), nullable=False, default=ActivityStatus.draft, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    created_by_user: Mapped["User"] = relationship(back_populates="created_activities")
    resources: Mapped[list["Resource"]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    groups: Mapped[list["Group"]] = relationship(back_populates="activity", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Activity id={self.id} title={self.title!r} status={self.status}>"
