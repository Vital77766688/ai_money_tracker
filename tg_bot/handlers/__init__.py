# This package contains all handlers for telegram commands, messages and conversations

import datetime
from telegram import Update, constants
from telegram.ext import ContextTypes

from core.uow import UnitOfWork
from budget.database import Session
from budget.schemas import UserCreateSchema
from budget.repositories import UserRepository
from budget.services import UserService
from budget.exceptions import UserNotFound
from aiclient.ai_client import Client
from aiclient.utils import load_user_prompt

from ..error_handler import NoUserFoundException


uow = UnitOfWork(Session, repositories={'users': UserRepository})


async def get_user(context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    """
    Utility function that checks if a user in the tg context
    And if there's no one then it queries from the DB
    """
    if context.user_data.get('db_user'):
        return context.user_data['db_user']

    async with uow:
        service = UserService(uow)
        try:
            user = await service.get_user_by_telegram_id(telegram_id)
            context.user_data['db_user'] = user
            return user
        except UserNotFound:
            raise NoUserFoundException


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command start check if a user is registered.
    If not then register them (saves user in the DB).
    Then greets the user.
    """
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    try:
        user = await get_user(context, update.effective_user.id)
        await update.message.reply_text(context.bot_data['messages'].user_welcome_back.format(user_name=user.name))
    except NoUserFoundException:
        async with uow:
            service = UserService(uow)
            user = await service.create_user(UserCreateSchema(name=update.effective_user.first_name, telegram_id=update.effective_user.id))
            await uow.commit()
            context.user_data['db_user'] = user
            await update.message.reply_text(context.bot_data['messages'].user_registered_success)



async def ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    ai_handler - activates the openai client and handles all user's messages if the user is registered
    """
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    user = await get_user(context, update.effective_user.id)
            
    if not context.user_data.get('ai_client'):
        ai_context = {
            'user': user,
            'date': datetime.datetime.now().strftime('%Y-%m-%d')
        }
        prompt = load_user_prompt()
        context.user_data['ai_client'] = Client(prompt, ai_context)

    message = update.message.text
    ai_client: Client = context.user_data.get('ai_client')

    reply = await ai_client.chat(message)
    await update.message.reply_text(reply)
