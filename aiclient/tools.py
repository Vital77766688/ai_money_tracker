# This module contains openai's tools mapping and wrapper functions for the tools.
# Wrapper functions handle exceptions from the budget app and produce results for the openai's client

from core.uow import UnitOfWork
from core.schemas import Filter
from core.database import Session
from budget.repositories import AccountRepository, TransactionRepository
from budget.services import AccountService, TransactionService, CurrencyService
from budget.schemas import (
    AccountUpdateSchema,
    TransactionCreateInputSchema,
    TransactionPurchaseCreateInputSchema,
    TransactionTransferCreateInputSchema
)
from budget.exceptions import (
    AccountNotFound,
    AccountAlreadyExists,
    TransactionNotFound,
)
from . import logger
from tg_bot.utils import notify_admin


uow = UnitOfWork(session=Session, repositories={
    'accounts': AccountRepository,
    'transactions': TransactionRepository
})


async def get_account(**kwargs) -> dict:
    async with uow:
        service = AccountService(uow)
        try:
            account = await service.get_account(**kwargs)
            return account.model_dump()
        except AccountNotFound:
            return {"status": "No account found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def list_accounts(**kwargs) -> list:
    filters = kwargs.pop('filters', None)
    if filters:
        filters = Filter.model_validate(filters)
    async with uow:
        service = AccountService(uow)
        try:
            accounts = await service.list_accounts(filters=filters, **kwargs)
            return [account.model_dump() for account in accounts]
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}        


async def update_account(**kwargs) -> dict:
    async with uow:
        service = AccountService(uow)
        try:
            account = await service.update_account(
                account_data=AccountUpdateSchema(**kwargs['account_data'])
            )
            await uow.commit()
            return account.model_dump()
        except AccountNotFound:
            return {"status": "No account found"}
        except AccountAlreadyExists:
            return {"status": "Account already exists"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def get_user_balance(**kwargs) -> float:
    async with uow:
        service = AccountService(uow)
        try:
            return await service.get_user_balance(**kwargs)
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}   


async def get_transaction(**kwargs) -> dict:
    async with uow:
        service = TransactionService(uow)
        try:
            transaction = await service.get_transaction(**kwargs)
            return transaction.model_dump()
        except TransactionNotFound:
            return {"status": "Transaction not found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def list_transactions(**kwargs) -> list:
    filters = kwargs.pop('filters', None)
    if filters:
        filters = Filter.model_validate(filters)
    async with uow:
        service = TransactionService(uow)
        try:
            transactions = await service.list_transactions(filters=filters, **kwargs)
            return [transaction.model_dump() for transaction in transactions]
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def create_topup(**kwargs) -> dict:
    async with uow:
        service = TransactionService(uow)
        try:
            transaction = await service.create_topup(
                transaction_data=TransactionCreateInputSchema(**kwargs['transaction_data'])
            )
            await uow.commit()
            return transaction.model_dump()
        except AccountNotFound:
            return {"status": "No account found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def create_withdraw(**kwargs) -> dict:
    async with uow:
        service = TransactionService(uow)
        try:
            transaction = await service.create_withdraw(
                transaction_data=TransactionCreateInputSchema(**kwargs['transaction_data'])
            )
            await uow.commit()
            return transaction.model_dump()
        except AccountNotFound:
            return {"status": "No account found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def create_purchase(**kwargs) -> dict:
    async with uow:
        service = TransactionService(uow)
        try:
            transaction = await service.create_purchase(
                transaction_data=TransactionPurchaseCreateInputSchema(**kwargs['transaction_data'])
            )
            await uow.commit()
            return transaction.model_dump()
        except AccountNotFound:
            return {"status": "No account found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def create_transfer(**kwargs) -> dict:
    async with uow:
        service = TransactionService(uow)
        try:
            transaction = await service.create_transfer(
                transaction_data=TransactionTransferCreateInputSchema(**kwargs['transaction_data'])
            )
            await uow.commit()
            return transaction.model_dump()
        except AccountNotFound:
            return {"status": "No account found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def delete_transaction(**kwargs) -> dict:
    async with uow:
        service = TransactionService(uow)
        try:
            await service.delete_transaction(**kwargs)
            await uow.commit()
        except TransactionNotFound:
            return {"status": "Transaction not found"}
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


async def get_currency_rate(**kwargs) -> float:
    async with uow:
        service = CurrencyService(uow)
        try:
            return await service.get_currency_rate(**kwargs)
        except Exception as e:
            logger.error(str(e))
            await notify_admin(str(e))
            return {"status": "Some error occurred. The team is already looking into it."}


tools_mapping = {
    "get_account": get_account,
    "list_accounts": list_accounts,
    "update_account": update_account,
    "get_user_balance": get_user_balance,
    "get_transaction": get_transaction,
    "list_transactions": list_transactions,
    "create_topup": create_topup,
    "create_withdraw": create_withdraw,
    "create_purchase": create_purchase,
    "create_transfer": create_transfer,
    "delete_transaction": delete_transaction,
    "get_currency_rate": get_currency_rate
}