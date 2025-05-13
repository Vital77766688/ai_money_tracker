from telegram import Update
from telegram.ext import ContextTypes

from .utils import notify_admin
from . import logger


class NoUserFoundException(Exception):
    ...


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    err_type = type(context.error)
    if err_type in [NoUserFoundException]:
        await update.message.reply_text(context.bot_data['messages'].user_not_found)
    else:
        logger.error(str(context.error))
        await notify_admin(str(context.error))
        await update.message.reply_text(context.bot_data['messages'].default_error_message)
