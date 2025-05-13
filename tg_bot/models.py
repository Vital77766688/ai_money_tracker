from typing import List, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, BigInteger, String, Text, Float, Date, DateTime, ForeignKey, UniqueConstraint,  func

# Move this to core
from budget.database import Base


class TgMessage(Base):
    __tablename__ = "tg_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
