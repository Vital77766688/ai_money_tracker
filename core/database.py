import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

async_connection_url = URL.create(
    "mssql+aioodbc",
    username=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOSTNAME'),
    database=os.getenv('DB_DATABASE'),
    query={
        "driver": "ODBC Driver 17 for SQL Server",
        "autocommit": "False",
        "trusted_connection": os.getenv('DB_TRUSTED_CONNECTION')
    },
)


connection_url = URL.create(
    "mssql+pyodbc",
    username=os.getenv('DB_USERNAME'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOSTNAME'),
    database=os.getenv('DB_DATABASE'),
    query={
        "driver": "ODBC Driver 17 for SQL Server",
        "autocommit": "False",
        "trusted_connection": os.getenv('DB_TRUSTED_CONNECTION')
    },
)

SyncSession = sessionmaker(
    bind=create_engine(connection_url, echo=True),
)

Session = async_sessionmaker(
    bind=create_async_engine(async_connection_url, echo=True),
)


class Base(DeclarativeBase):
    ...
