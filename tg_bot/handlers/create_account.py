# This module contains the conversation between telegram and a user
# The goal of this conversation is to collect data about new account
# than the user about to create and then create an account

from telegram import Update, constants
from telegram.ext import (
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)

from budget.database import Session
from budget.schemas import AccountCreateSchema
from budget.repositories.account_repository import AccountRepository
from .. import logger
from ..utils import notify_admin


ACCOUNT_NAME, ACCOUNT_TYPE, ACCOUNT_CURRENCY, ACCOUNT_INIT_BALANCE, CREATE_ACCOUNT_CHECK = range(5)


async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    user = context.user_data.get('db_user')
    if not user:
        await update.message.reply_text('Что-то не так. Попробуй начать с команды /start')
        return ConversationHandler.END
    
    await update.message.reply_text("Сейчас заполним небольшой опросник, чтобы создать счет. Если передумаешь, просто нажми /cancel")
    await update.message.reply_text("Укажи название счета")
    return ACCOUNT_NAME



async def create_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    context.user_data['new_account'] = {}
    context.user_data['new_account']['name'] = update.message.text
    await update.message.reply_text("Хорошо! Теперь выбери тип счета")
    # Посадить кнопки
    return ACCOUNT_TYPE


async def create_account_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    # изменить на указанный тип счета
    context.user_data['new_account']['type_id'] = 1
    await update.message.reply_text("Очень хорошо! Теперь укажи код валюты, напимер: USD, EUR")
    return ACCOUNT_CURRENCY


async def create_account_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    context.user_data['new_account']['currency'] = update.message.text
    await update.message.reply_text("Отлично! Осталось только указать начальный баланс. \nЭто сколько у тебя сейчас денег на счете. \nЕсли у тебя долг, то напиши отрицательное число.")
    return ACCOUNT_INIT_BALANCE


async def create_account_init_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    context.user_data['new_account']['balance'] = update.message.text
    await update.message.reply_text(
        f"""Замечательно! Теперь проверь все ли верно записано.\n
        **Название счета:** {context.user_data['new_account'].get('name')}\n
        **Тип:** {context.user_data['new_account'].get('type')}\n
        **Валюта:** {context.user_data['new_account'].get('currency')}\n
        **Баланс:** {context.user_data['new_account'].get('balance')}"""
    )
    return CREATE_ACCOUNT_CHECK


async def create_account_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    response = update.message.text
    if response.strip().lower() == 'да':
        account_repo = AccountRepository(Session)
        account = AccountCreateSchema(user_id=context.user_data['db_user'].id, **context.user_data['new_account'])
        try:
            await account_repo.create_account(account)
            await update.message.reply_text('Збс! Счет успешно создан! Теперь можешь продолжить общение.')
            return ConversationHandler.END
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            await update.message.reply_text("Some error occurred. The team is already looking into it.")
            return ConversationHandler.END
    elif response.strip().lower() == 'нет':
        await update.message.reply_text('Ничего страшного, попробуй снова! Укажи название счета')
        return ACCOUNT_NAME
    else:
        await update.message.reply_text('Укажи **да** или **нет**')
        return CREATE_ACCOUNT_CHECK


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ок, если передумаешь — просто напиши /create_account")
    return ConversationHandler.END


create_account_handler = ConversationHandler(
    entry_points=[CommandHandler("create_account", create_account)],
    states={
        ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_name)],
        ACCOUNT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_type)],
        ACCOUNT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_currency)],
        ACCOUNT_INIT_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_init_balance)],
        CREATE_ACCOUNT_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_check)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
