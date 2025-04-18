# This project is AI powered personal finance assistant.
# The main packages are: 
#     1. tg-bot - utilizes python-telgram-bot library
#     2. aiclinet - based on openai library
#     3. budget - uses mainly sqlalchemy, pydantic and alembic libraries

# 2025-04-18
# Vitaliy Ponomaryov

from tg_bot.bot import build_app


def main() -> None:
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
