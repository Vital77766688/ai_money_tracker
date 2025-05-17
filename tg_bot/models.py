from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Text


from core.database import Base


class TgMessage(Base):
    __tablename__ = "tg_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
