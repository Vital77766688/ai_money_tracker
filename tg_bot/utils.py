import os
from dotenv import load_dotenv
from telegram import Bot


async def notify_admin(msg: str) -> None:
    recipient = 793074650
    await Bot(os.getenv('TG_BOT_TOKEN')).sendMessage(chat_id=recipient, text=f"ALARM!\n{msg}")
