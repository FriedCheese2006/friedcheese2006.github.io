import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # OIDC subject claim
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    state = relationship("UserState", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserState(Base):
    __tablename__ = "user_states"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tabs = Column(Text, nullable=True)      # JSON blob
    settings = Column(Text, nullable=True)  # JSON blob
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="state")
