import os
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler,
    MessageHandler, 
    Application,
    filters
)
from tg_bot.handlers import start, ai_handler
from tg_bot.error_handler import error_handler
from tg_bot.handlers.create_account import create_account_handler
from tg_bot.messages import Messages

load_dotenv()


def build_app() -> Application:
    app = ApplicationBuilder().token(os.getenv('TG_BOT_TOKEN')).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(create_account_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_handler))
    app.add_error_handler(error_handler)
    app.bot_data['messages'] = Messages()

    return app
