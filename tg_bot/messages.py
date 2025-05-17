from sqlalchemy import select
from core.database import SyncSession
from tg_bot.models import TgMessage


class Messages:
    def __init__(self):
        with SyncSession() as session:
            messages = session.execute(select(TgMessage)).scalars().all()

        for message in messages:
            setattr(self, message.code, message.message)

        return None
