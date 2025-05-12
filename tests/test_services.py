import os
import asyncio
import pytest
import pytest_asyncio
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.engine.url import URL
from core.schemas import Filter
from budget.models import *
from budget.uow import UnitOfWork
from budget.repositories import UserRepository, AccountRepository, TransactionRepository
from budget.services import UserService, AccountService, TransactionService
from budget.schemas import (
    UserCreateSchema,
    AccountCreateSchema,
    AccountUpdateInputSchema,
    TransactionCreateInputSchema,
    TransactionPurchaseCreateInputSchema,
    TransactionTransferCreateInputSchema
)
from budget.exceptions import (
    UserNotFound, 
    UserAlreadyExists,
    AccountNotFound,
    AccountAlreadyExists,
    TransactionNotFound
)



# ---------------- FIXTURES ---------------- #
CONFIG = {**dotenv_values('.env_test')}
print('\n\n\n\n', CONFIG, '\n\n\n\n')

async_connection_url = URL.create(
    "mssql+aioodbc",
    username=CONFIG.get('DB_USERNAME'),
    password=CONFIG.get('DB_PASSWORD'),
    host=CONFIG.get('DB_HOSTNAME'),
    database=CONFIG.get('DB_DATABASE'),
    query={
        "driver": "ODBC Driver 17 for SQL Server",
        "autocommit": "False",
        "trusted_connection": CONFIG.get('DB_TRUSTED_CONNECTION')
    },
)


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(str(async_connection_url), echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def uow(session: AsyncSession):
    return UnitOfWork(
        session=session, 
        repositories={
            'users': UserRepository,
            'accounts': AccountRepository,
            'transactions': TransactionRepository
        }
    )


# ---------------- SEEDS ---------------- #

@pytest_asyncio.fixture
async def seed_user(uow):
    async with uow:
        await uow.session.execute(text("""
        INSERT INTO users(name, telegram_id) VALUES ('test', 123123)
        """))
        await uow.commit()


@pytest_asyncio.fixture
async def seed_accounts(uow):
    async with uow:
        await uow.session.execute(text("""
        INSERT INTO accounts(user_id, name, currency, balance, created_at, is_active) 
        VALUES (1, 'test account 1', 'USD', 0., '2025-05-01', 1)
        """))
        await uow.session.execute(text("""
        INSERT INTO accounts(user_id, name, currency, balance, created_at, is_active) 
        VALUES (1, 'test account 2', 'EUR', 10., '2025-05-01', 1)
        """))
        await uow.commit()


@pytest_asyncio.fixture
async def seed_currency(uow):
    async with uow:
        await uow.session.execute(text("""
        INSERT INTO currencies(iso_code, name) VALUES ('KZT', 'Казахстанский тенге')
        """))
        await uow.commit()


@pytest_asyncio.fixture
async def seed_transaction_types(uow):
    async with uow:
        await uow.session.execute(text("""
        INSERT INTO transaction_types(type_name)
        VALUES ('Topup')
        """))
        await uow.session.execute(text("""
        INSERT INTO transaction_types(type_name)
        VALUES ('Withdraw')
        """))
        await uow.session.execute(text("""
        INSERT INTO transaction_types(type_name)
        VALUES ('Purchase')
        """))
        await uow.session.execute(text("""
        INSERT INTO transaction_types(type_name)
        VALUES ('Transfer')
        """))
        await uow.commit()


@pytest_asyncio.fixture
async def seed_transactions(uow):
    async with uow:
        await uow.session.execute(text("""
        INSERT INTO transactions(type_id, account_id, amount, currency, amount_in_account_currency, transaction_date, is_deleted)
        VALUES (1, 1, 1000., 'USD', 1000., '2025-05-01', 0)
        """))
        await uow.session.execute(text("""
        INSERT INTO transactions(type_id, account_id, amount, currency, amount_in_account_currency, transaction_date, is_deleted)
        VALUES (1, 1, 1000., 'EUR', 800., '2025-05-01', 0)
        """))
        await uow.session.execute(text("""
        INSERT INTO transactions(type_id, account_id, amount, currency, amount_in_account_currency, transaction_date, is_deleted)
        VALUES (1, 2, 800., 'EUR', 800., '2025-05-10', 0)
        """))
        await uow.commit()


# ---------------- TESTS ---------------- #

@pytest.mark.asyncio
async def test_create_and_get_user(uow):
    async with uow:
        service = UserService(uow)
        user_created = await service.create_user(UserCreateSchema(name='test', telegram_id=123123))
        await uow.commit()

        user = await service.get_user_by_telegram_id(telegram_id=user_created.telegram_id)
        assert user.id == 1
        assert user.name == 'test'
        assert user.telegram_id == 123123


@pytest.mark.asyncio
async def test_get_user_fail(uow):
    async with uow:
        service = UserService(uow)
        with pytest.raises(UserNotFound):
            _ = await service.get_user_by_telegram_id(telegram_id=1233333)


@pytest.mark.asyncio
async def test_create_user_fail(uow):
    async with uow:
        service = UserService(uow)
        _ = await service.create_user(UserCreateSchema(name='test', telegram_id=123123))
        with pytest.raises(UserAlreadyExists):
            _ = await service.create_user(UserCreateSchema(name='test', telegram_id=123123))


@pytest.mark.asyncio
async def test_create_and_get_account(uow, seed_user):
    async with uow:
        service = AccountService(uow)
        account_created = await service.create_account(
            account_data=AccountCreateSchema(
                user_id=1,
                name='test account',
                description='test description',
                currency='USD',
                balance=1000.0
            )
        )
        await uow.commit()

        account = await service.get_account(account_id=account_created.id, user_id=1)
        assert account.name == 'test account'
        assert account.currency == 'USD'
        assert account.balance == 1000.0


@pytest.mark.asyncio
async def test_get_account_fail(uow):
    async with uow:
        service = AccountService(uow)
        with pytest.raises(AccountNotFound):
            _ = await service.get_account(account_id=123, user_id=1)


@pytest.mark.asyncio
async def test_create_account_fail(uow, seed_user, seed_accounts):
    async with uow:
        service = AccountService(uow)
        with pytest.raises(AccountAlreadyExists):
            _ = await service.create_account(
                account_data=AccountCreateSchema(
                    user_id=1,
                    name='test account 1',
                    currency='USD',
                    balance=0.
                )
            )


@pytest.mark.asyncio
async def test_list_accounts(uow, seed_user, seed_accounts):
    async with uow:
        service = AccountService(uow)
        accounts = await service.list_accounts(user_id=1)
        assert len(accounts) == 2
        assert accounts[0].balance == 10.
        assert accounts[0].currency == 'EUR'
        assert accounts[1].balance == 0.


@pytest.mark.asyncio
async def test_empty_list_accounts(uow):
    async with uow:
        service = AccountService(uow)
        accounts = await service.list_accounts(user_id=1)
        assert len(accounts) == 0


@pytest.mark.asyncio
async def test_update_account(uow, seed_user, seed_accounts):
    async with uow:
        service = AccountService(uow)
        account_updated = await service.update_account(
            account_data=AccountUpdateInputSchema(
                id=1, 
                user_id=1,
                name='account updated',
                description='account description updated'
            )
        )
        await uow.commit()

        account = await service.get_account(account_id=account_updated.id, user_id=1)
        assert account.id == 1
        assert account.name == 'account updated'
        assert account.description == 'account description updated'


@pytest.mark.asyncio
async def test_update_account_fail(uow, seed_user, seed_accounts):
    async with uow:
        service = AccountService(uow)
        with pytest.raises(AccountNotFound):
            _ = await service.update_account(
                account_data=AccountUpdateInputSchema(
                    id=333,
                    user_id=333,
                    name='No matter'
                )
            )
        with pytest.raises(AccountAlreadyExists):
            _ = await service.update_account(
                account_data=AccountUpdateInputSchema(
                    id=2,
                    user_id=1,
                    name='test account 1'
                )
            )


@pytest.mark.asyncio
async def test_get_user_balance(uow, seed_user, seed_accounts):
    async with uow:
        service = AccountService(uow)
        balance = await service.get_user_balance(user_id=1)
        assert balance == 10.


@pytest.mark.asyncio
async def test_get_user_balance_fail(uow):
    async with uow:
        service = AccountService(uow)
        balance = await service.get_user_balance(user_id=1)
        assert balance == 0.


@pytest.mark.asyncio
async def test_find_currency(uow, seed_currency):
    async with uow:
        service = AccountService(uow)
        currency = await service.find_currency(name='тенге')
        assert currency.iso_code == 'KZT'


@pytest.mark.asyncio
async def test_create_and_get_transaction(uow, seed_user, seed_accounts, seed_transaction_types):
    async with uow:
        service = TransactionService(uow)
        topup_created = await service.create_topup(
            transaction_data=TransactionCreateInputSchema(
                user_id=1,
                account_id=1,
                amount=1000.,
                currency='USD',
                transaction_date='2025-05-01'
            )
        )

        purchase_created = await service.create_purchase(
            transaction_data=TransactionPurchaseCreateInputSchema(
                user_id=1,
                account_id=1,
                amount=1000.,
                currency='EUR',
                amount_in_account_currency=800.,
                transaction_date='2025-05-01',
                description='Beer'
            )
        )
        await uow.commit()

        topup = await service.get_transaction(user_id=1, account_id=1, transaction_id=topup_created.id)
        purchase = await service.get_transaction(user_id=1, account_id=1, transaction_id=purchase_created.id)
        assert topup.amount == 1000.
        assert topup.amount_in_account_currency == 1000.
        assert purchase.amount == -1000.
        assert purchase.amount_in_account_currency == -800. 


@pytest.mark.asyncio
async def test_get_transaction_fail(uow):
    async with uow:
        service = TransactionService(uow)
        with pytest.raises(TransactionNotFound):
            _ = await service.get_transaction(user_id=1, account_id=333, transaction_id=111)


@pytest.mark.asyncio
async def test_list_transactions(uow, seed_user, seed_accounts, seed_transaction_types, seed_transactions):
    async with uow:
        service = TransactionService(uow)
        transactions = await service.list_transactions(user_id=1)
        assert len(transactions) == 3


@pytest.mark.asyncio
async def test_list_transactions_with_filters(uow, seed_user, seed_accounts, seed_transaction_types, seed_transactions):
    async with uow:
        service = TransactionService(uow)
        filters = Filter.model_validate([
            {'field': 'account_id', 'op': '=', 'value': 2},
            {'field': 'type', 'op': '=', 'value': 'Transfer'},
            {'field': 'transaction_date', 'op': '<=', 'value': '2025-05-03'}
        ])
        transactions = await service.list_transactions(user_id=1, filters=filters)
        assert len(transactions) == 0



@pytest.mark.asyncio
async def test_empty_list_transactions(uow, seed_user, seed_accounts):
    async with uow:
        service = TransactionService(uow)
        transactions = await service.list_transactions(user_id=1)
        assert len(transactions) == 0


@pytest.mark.asyncio
async def test_create_transfer(uow, seed_user, seed_accounts, seed_transaction_types):
    async with uow:
        service = TransactionService(uow)
        _ = await service.create_transfer(
            transaction_data=TransactionTransferCreateInputSchema(
                user_id=1,
                account_id=1,
                amount=1000.,
                currency='USD',
                transaction_date='2025-05-01',
                account_id_to=2,
                amount_in_account_currency_to=800
            )
        )
        await uow.commit()
        filters = Filter.model_validate([{'field': 'id', 'op': 'in', 'value': [1, 2]}])
        transactions = await service.list_transactions(user_id=1, filters=filters)
        assert transactions[0].amount_in_account_currency == 800
        assert transactions[0].account.id == 2
        assert transactions[1].amount_in_account_currency == -1000
        assert transactions[1].account.id == 1


@pytest.mark.asyncio
async def test_delete_transaction(uow, seed_user, seed_accounts, seed_transaction_types, seed_transactions):
    async with uow:
        service = TransactionService(uow)
        await service.delete_transaction(user_id=1, account_id=1, transaction_id=1)
        await uow.commit()
        with pytest.raises(TransactionNotFound):
            _ = await service.get_transaction(user_id=1, account_id=1, transaction_id=1)


@pytest.mark.asyncio
async def test_delete_transaction_fail(uow, seed_user, seed_accounts, seed_transaction_types):
    async with uow:
        service = TransactionService(uow)
        with pytest.raises(TransactionNotFound):
            _ = await service.delete_transaction(user_id=1, account_id=1, transaction_id=1)
