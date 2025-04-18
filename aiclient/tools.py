# This module contains openai's tools mapping and wrapper functions for the tools.
# Wrapper functions handle exceptions from the budget app and produce results for the openai's client

from sqlalchemy.exc import NoResultFound
from budget.database import Session
from budget.repositories.account_repository import AccountRepository
from budget.repositories.transaction_repository import TransactionRepository
from budget.schemas import (
    TransactionTopupCreateSchema, 
    TransactionWithdrawalCreateSchema,
    TransactionPurchaseCreateSchema,
    TransactionTransferCreateSchema
)
from . import logger
from tg_bot.utils import notify_admin


account_repository = AccountRepository(Session)
transaction_repo = TransactionRepository(Session)


async def get_account_by_id(**kwargs) -> dict:
    try:
        account = await account_repository.get_account_by_id(**kwargs)
    except NoResultFound:
        {"status": "No account found"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}
    return account.model_dump()


async def get_accounts_by_user_id(**kwargs) -> list:
    try:
        accounts = await account_repository.get_accounts_by_user_id(**kwargs)
        return [account.model_dump() for account in accounts]
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def get_user_balance(**kwargs) -> dict:
    try:
        balance = await account_repository.get_user_balance(**kwargs)
        return {"balance": balance}
    except NoResultFound:
        return {"status": "No user found"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def get_transaction(**kwargs) -> dict:
    try:
        transaction = await transaction_repo.get_transaction(**kwargs)
    except NoResultFound:
        return {"status": "Transaction not found"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}
    return transaction.model_dump()


async def list_transactions(**kwargs) -> list:
    try:
        transactions = await transaction_repo.list_transactions(**kwargs)
        return [transaction.model_dump() for transaction in transactions]
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def create_topup(**kwargs) -> dict:
    if 'transaction' not in kwargs:
        raise ValueError('Check tools config')
    try:
        validated_kwargs = TransactionTopupCreateSchema(**kwargs['transaction'])
        await transaction_repo.create_topup(validated_kwargs)
        return {"status": "Success"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def create_withdraw(**kwargs) -> dict:
    if 'transaction' not in kwargs:
        raise ValueError('Check tools config')
    try:
        validated_kwargs = TransactionWithdrawalCreateSchema(**kwargs['transaction'])
        await transaction_repo.create_withdraw(validated_kwargs)
        return {"status": "Success"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def create_purchase(**kwargs) -> dict:
    if 'transaction' not in kwargs:
        raise ValueError('Check tools config')
    try:
        validated_kwargs = TransactionPurchaseCreateSchema(**kwargs['transaction'])
        await transaction_repo.create_purchase(validated_kwargs)
        return {"status": "Success"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def create_transfer(**kwargs) -> dict:
    if 'transaction' not in kwargs:
        raise ValueError('Check tools config')
    try:
        validated_kwargs = TransactionTransferCreateSchema(**kwargs['transaction'])
        await transaction_repo.create_transfer(validated_kwargs)
        return {"status": "Success"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


async def delete_transaction(**kwargs) -> dict:
    try:
        await transaction_repo.delete_transaction(**kwargs)
        return {"status": "Success"}
    except Exception as e:
        logger.error(str(e))
        await notify_admin(str(e))
        return {"status": "Some error occurred. The team is already looking into it."}


tools_mapping = {
    "get_account_by_id": get_account_by_id,
    "get_accounts_by_user_id": get_accounts_by_user_id,
    "get_user_balance": get_user_balance,
    "get_transaction": get_transaction,
    "list_transactions": list_transactions,
    "create_topup": create_topup,
    "create_withdraw": create_withdraw,
    "create_purchase": create_purchase,
    "create_transfer": create_transfer,
    "delete_transaction": delete_transaction
}