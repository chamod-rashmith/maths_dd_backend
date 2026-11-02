"""
SQLAlchemy 2.0 ORM model for Sri Lankan Administrative Districts.
Static reference lookup data for student regional profiling, provincial leaderboards, and Z-Score rankings.
"""

from typing import TYPE_CHECKING, List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class District(Base):
    """Sri Lankan Administrative District lookup table."""

    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_si: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ta: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="district",
    )

    def __repr__(self) -> str:
        return f"<District(id='{self.id}', name_en='{self.name_en}', province='{self.province}')>"
