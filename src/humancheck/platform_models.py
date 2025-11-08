"""Platform and multi-tenancy models."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Organization(Base):
    """Organization for multi-tenancy."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    teams: Mapped[list["Team"]] = relationship(
        "Team", back_populates="organization", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(
        "Agent", back_populates="organization", cascade="all, delete-orphan"
    )
    routing_rules: Mapped[list["RoutingRule"]] = relationship(
        "RoutingRule", back_populates="organization", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"


class User(Base):
    """User/reviewer in the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default=UserRole.REVIEWER.value, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    team_memberships: Mapped[list["TeamMembership"]] = relationship(
        "TeamMembership", back_populates="user", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship("Decision", back_populates="reviewer")
    assignments: Mapped[list["ReviewAssignment"]] = relationship(
        "ReviewAssignment", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class Team(Base):
    """Team of reviewers."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="teams")
    memberships: Mapped[list["TeamMembership"]] = relationship(
        "TeamMembership", back_populates="team", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["ReviewAssignment"]] = relationship(
        "ReviewAssignment", back_populates="team"
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}')>"


class TeamMembership(Base):
    """Membership of users in teams."""

    __tablename__ = "team_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="team_memberships")
    team: Mapped["Team"] = relationship("Team", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<TeamMembership(id={self.id}, user_id={self.user_id}, team_id={self.team_id})>"


class Agent(Base):
    """AI Agent registry."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="agents")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', framework='{self.framework}')>"


class RoutingRule(Base):
    """Routing rules for intelligent review assignment."""

    __tablename__ = "routing_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False)  # JSON rules
    assign_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    assign_to_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="routing_rules"
    )
    assign_to_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assign_to_user_id])
    assign_to_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[assign_to_team_id])
    assignments: Mapped[list["ReviewAssignment"]] = relationship(
        "ReviewAssignment", back_populates="rule"
    )

    def __repr__(self) -> str:
        return f"<RoutingRule(id={self.id}, name='{self.name}', priority={self.priority})>"


# Import to avoid circular dependency
from .models import Decision, Review, ReviewAssignment
