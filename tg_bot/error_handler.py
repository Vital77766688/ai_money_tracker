from telegram import Update
from telegram.ext import ContextTypes

from .utils import notify_admin
from . import logger


class NoUserFoundException(Exception):
    ...


GLOBAL_EXCEPTION_RESPONSES = {
    NoUserFoundException: "Чтобы начать, пожалуйста нажми /start 👋",
}


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    err_type = type(context.error)
    if err_type in GLOBAL_EXCEPTION_RESPONSES:
        await update.message.reply_text(GLOBAL_EXCEPTION_RESPONSES[err_type])
    else:
        logger.error(str(context.error))
        await notify_admin(str(context.error))
        await update.message.reply_text("Some error occurred. The team is already looking into it.")