# This package contains all handlers for telegram commands, messages and conversations

import datetime
from telegram import Update, constants
from telegram.ext import ContextTypes
from sqlalchemy.exc import NoResultFound

from budget.database import Session
from budget.schemas import UserCreateSchema
from budget.repositories.user_repository import UserRepository
from aiclient.ai_client import Client

from .. import logger
from ..utils import notify_admin


repo: UserRepository = UserRepository(Session)

async def get_user(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Utility function that checks if a user in the tg context
    And if there's no one then it queries from the DB
    """
    if context.user_data['db_user']:
        return 
    user = None
    try:
        user = await repo.get_user_by_telegram_id(telegram_id)
    except NoResultFound:
        pass
    context.user_data['db_user'] = user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command start check if a user is registered.
    If not then register them (saves user in the DB).
    Then greets the user.
    """
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    await get_user(context, update.effective_user.id)
    user = context.user_data['db_user']

    if not user:
        try:
            await repo.create_user(UserCreateSchema(name=update.effective_user.first_name, telegram_id=update.effective_user.id))
            await update.message.reply_text("Готово! Теперь можешь писать мне любые сообщения 👌. Если не знаешь что делать просто спроси и я тебе все расскажу")
            return
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            await update.message.reply_text("Some error occurred. The team is already looking into it.")
            return

    await update.message.reply_text(f"С возвращением, {user.name}!")



async def ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    ai_handler - activates the openai client and handles all user's messages if the user is registered
    """
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    await get_user(context, update.effective_user.id)
    user = context.user_data['db_user']
        
    if not user:
        await update.message.reply_text("Чтобы начать, пожалуйста нажми /start 👋")
        return
    
    if not context.user_data.get('ai_client'):
        ai_context = {
            'user': user,
            'date': datetime.datetime.now().strftime('%Y-%m-%d')
        }
        context.user_data['ai_client'] = Client(ai_context)

    message = update.message.text
    ai_client: Client = context.user_data.get('ai_client')
    try:
        reply = await ai_client.chat(message)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        await update.message.reply_text("Some error occurred. The team is already looking into it.")
        return
