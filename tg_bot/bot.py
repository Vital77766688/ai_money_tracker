import os
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler,
    MessageHandler, 
    Application,
    filters
)
from .handlers import start, ai_handler
from .error_handler import error_handler
from .handlers.create_account import create_account_handler

load_dotenv()


def build_app() -> Application:
    app = ApplicationBuilder().token(os.getenv('TG_BOT_TOKEN')).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(create_account_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_handler))
    app.add_error_handler(error_handler)

    return app
