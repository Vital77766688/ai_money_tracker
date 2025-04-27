# This module contains the conversation between telegram and a user
# The goal of this conversation is to collect data about new account
# than the user about to create and then create an account

import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, constants
from telegram.ext import (
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)
from pydantic import ValidationError
from sqlalchemy.exc import NoResultFound

from budget.database import Session
from budget.schemas import AccountCreateSchema
from budget.repositories.account_repository import AccountRepository
from . import get_user


(
    CREATE_ACCOUNT, 
    ACCOUNT_NAME, 
    ACCOUNT_DESCRIPTION, 
    ACCOUNT_CURRENCY, 
    ACCOUNT_INIT_BALANCE, 
    CREATE_ACCOUNT_CHECK
) = range(6)


async def raise_for_conversation(update, context, exc):
    context.error = exc
    handler = list(context.application.error_handlers.keys())[0]
    await handler(update, context)
    return ConversationHandler.END


validation_messages = {
    'AccountCreateSchema': {
        'name': {
            'string_too_long': '*Название счета* не должно превышать 20 символов',
        },
        'currency': {
            'string_too_long': '*Код валюты* должен быть ровно 3 символа (например: USD, EUR и тд.)',
            'string_too_short': '*Код валюты* должен быть ровно 3 символа (например: USD, EUR и тд.)',
        },
        'balance': {
            'float_parsing': '*Баланс* должен быть числом',
        }
    }
}

def get_validation_error_message(errors: ValidationError) -> list[str]:
    result = []
    schema = errors.title
    for error in errors.errors():
        loc = '.'.join(error['loc'])
        msg = error['msg']
        err_type = error['type']
        try:
            result.append(validation_messages[schema][loc][err_type])
        except KeyError:
            result.append(f"*{loc}*: {msg}")
    return result


class CreateAccountMessages:
    user_not_found = "Что-то не так. Попробуй начать с команды /start"
    create_account_ready = """
Сейчас заполним небольшой опросник, чтобы создать счет.
Если передумаешь, просто нажми /cancel\n
Готов?\n
Ответь *Да* или *Нет*
"""
    create_account_name = """
Укажи название счета.\n
Не более 20 символов
"""
    create_account_description = """
Хорошо! Теперь заполни описание.\n
Не более 50 символов (можно оставить пустым)
"""
    create_account_currency = """
Очень хорошо! Какая у счета будет валюта?\n
Введите название валюты или ее 3-х символьный код
"""
    create_account_balance = """
Отлично! Осталось только указать начальный баланс.
Если у тебя долг, то напиши отрицательное число.\n
Нужно ввести число с разделителем или без него
"""
    create_account_reject = """
Ок, ну если что команда для создания нового счета вот /create\\_account
"""
    create_account_wrong = """
Укажи *Да* или *Нет*\n
Также ты можешь отменить создание счета. Вот команда для этого /cancel
"""
    create_account_try_again = """
Попробуем снова?\n
Ответь *Да* или *Нет*
"""
    create_account_cancel = """
Ок, если передумаешь — просто напиши /create\\_account
"""
    create_account_success = """
Круто! Счет создан!\n
Если хочешь создать еще один тапни /create\\_account
"""
    create_account_system_error = """Что-то поломалось. Мы уже смотрим, повтори позже"""
    no_currency_found = """Не могу найти такую валюту, попробуй ввести подробнее или 3-х значный код, если знаешь"""

    @classmethod
    def create_account_validated(cls, account: dict) -> str:
        balance = f"{float(account['balance']):,.2f}".replace(',', ' ').replace('.', ',')
        return f"""
Замечательно! Теперь проверь все ли верно записано.\n
*Название счета:* {account.get('name')}
*Описание:* {account['description'] if account.get('description') else ''}
*Валюта:* {account.get('currency_name')} ({account.get('currency')})
*Баланс:* {balance}\n
Ответь *Да* или *Нет*
"""
    
    @classmethod
    def create_account_validation_error(cls, errors: ValidationError) -> str:
        msg = "Есть ошибки при заполнении опросника. Исправьте их и продолжим.\n\n"
        # for error in errors:
        #     account[error['loc'][0]] = None
        #     msg += f"*{error['loc'][0]}:* {error['msg']}\n"
        for error in get_validation_error_message(errors):
            msg += f"- {error}\n"
        msg += '\nТакже ты можешь отменить создание счета командой /cancel'
        return msg


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    _ = await get_user(context, update.effective_user.id)
    context.user_data['new_account'] = {}    
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[["Да", "Нет"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_markdown(
        CreateAccountMessages.create_account_ready,
        reply_markup=reply_markup
    )
    return CREATE_ACCOUNT


async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text
    if response.strip().lower() == 'да':
        reply_markup = ReplyKeyboardRemove()
        if context.user_data['new_account'].get('name'):
            reply_markup = ReplyKeyboardMarkup(
                keyboard=[[context.user_data['new_account']['name']]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
        await update.message.reply_markdown(CreateAccountMessages.create_account_name, reply_markup=reply_markup)
        return ACCOUNT_NAME
    elif response.strip().lower() == 'нет':
        await update.message.reply_markdown(
            CreateAccountMessages.create_account_reject,
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    reply_markup = ReplyKeyboardMarkup(
        keyboard=[["Да", "Нет"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_markdown(
        CreateAccountMessages.create_account_wrong,
        reply_markup=reply_markup
    )
    return CREATE_ACCOUNT


async def create_account_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    context.user_data['new_account']['name'] = update.message.text

    reply_markup = ReplyKeyboardMarkup(keyboard=[['Пропустить']], resize_keyboard=True, one_time_keyboard=True)
    if context.user_data['new_account'].get('description'):
        reply_markup = ReplyKeyboardMarkup(
            keyboard=[[context.user_data['new_account']['description']]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    await update.message.reply_markdown(
        CreateAccountMessages.create_account_description, 
        reply_markup=reply_markup
    )
    # Посадить кнопки
    return ACCOUNT_DESCRIPTION


async def create_account_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    text = update.message.text
    context.user_data['new_account']['description'] = text if text != 'Пропустить' else None

    reply_markup = ReplyKeyboardRemove()
    if context.user_data['new_account'].get('currency_user_input'):
        reply_markup = ReplyKeyboardMarkup(
            keyboard=[[context.user_data['new_account']['currency_user_input']]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    await update.message.reply_markdown(
        CreateAccountMessages.create_account_currency,
        reply_markup=reply_markup
    )
    return ACCOUNT_CURRENCY


async def create_account_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    repo = AccountRepository(Session)
    try:
        currency = await repo.find_currency_by_name(update.message.text)
    except NoResultFound:
        await update.message.reply_markdown(
            CreateAccountMessages.no_currency_found,
            reply_markup=ReplyKeyboardRemove()
        )
        return ACCOUNT_CURRENCY

    context.user_data['new_account']['currency_user_input'] = update.message.text
    context.user_data['new_account']['currency'] = currency.iso_code
    context.user_data['new_account']['currency_name'] = currency.name

    reply_markup = ReplyKeyboardRemove()
    if context.user_data['new_account'].get('balance'):
        reply_markup = ReplyKeyboardMarkup(
            keyboard=[[context.user_data['new_account']['balance']]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    await update.message.reply_markdown(
        CreateAccountMessages.create_account_balance,
        reply_markup=reply_markup
    )
    return ACCOUNT_INIT_BALANCE


async def create_account_init_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    context.user_data['new_account']['balance'] = update.message.text.replace(',', '.')

    reply_markup = ReplyKeyboardMarkup(
        keyboard=[["Да", "Нет"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    user_id = context.user_data['db_user'].id
    account_data = context.user_data['new_account']
    try:
        context.user_data['validated_account'] = AccountCreateSchema(user_id=user_id, **account_data)
        await update.message.reply_markdown(
            CreateAccountMessages.create_account_validated(account_data),
            reply_markup=reply_markup
        )
        return CREATE_ACCOUNT_CHECK
    except ValidationError as e:
        await update.message.reply_markdown(
            CreateAccountMessages.create_account_validation_error(e)
        )
        await asyncio.sleep(1)
        await update.message.reply_markdown(
            CreateAccountMessages.create_account_try_again,
            reply_markup=reply_markup
        )
        return CREATE_ACCOUNT


async def create_account_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=constants.ChatAction.TYPING)
    response = update.message.text
    if response.strip().lower() == 'да':
        repo = AccountRepository(Session)
        try:
            await repo.create_account(context.user_data['validated_account'])
            await update.message.reply_markdown(
                CreateAccountMessages.create_account_success, 
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        except Exception as e:
            # Is there more elegant way to perform conversation end with global error_handler?
            return await raise_for_conversation(update, context, e)
    elif response.strip().lower() == 'нет':
        await update.message.reply_markdown(
            CreateAccountMessages.create_account_reject, 
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        await update.message.reply_markdown(
            CreateAccountMessages.create_account_wrong,
            reply_markup = ReplyKeyboardMarkup(
                keyboard=[["Да", "Нет"]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
        )
        return CREATE_ACCOUNT_CHECK


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_markdown(
        CreateAccountMessages.create_account_cancel, 
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


create_account_handler = ConversationHandler(
    entry_points=[CommandHandler("create_account", start)],
    states={
        CREATE_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account)],
        ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_name)],
        ACCOUNT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_description)],
        ACCOUNT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_currency)],
        ACCOUNT_INIT_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_init_balance)],
        CREATE_ACCOUNT_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account_check)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
