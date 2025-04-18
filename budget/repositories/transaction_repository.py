import datetime
from sqlalchemy import select, update
from . import BaseRepository
from budget.models import Transaction, TransactionType, Account
from budget.schemas import (
    TransactionTopupCreateSchema, TransactionPurchaseCreateSchema,
    TransactionWithdrawalCreateSchema, TransactionTransferCreateSchema,
    TransactionSchema, TransactionDetailsSchema
)


class TransactionRepository(BaseRepository):
    async def get_transaction(self, user_id: int, id: int) -> TransactionDetailsSchema:
        async with self.session() as session:
            transaction = await session.execute(
                select(
                    Transaction.id,
                    Transaction.type_id,
                    TransactionType.type_name,
                    Transaction.account_id,
                    Account.name.label("account_name"),
                    Transaction.amount,
                    Transaction.currency,
                    Transaction.amount_in_account_currency,
                    Transaction.transaction_date,
                    Transaction.description
                ) \
                .filter_by(id=id, is_deleted=False) \
                .join(TransactionType, Transaction.type_id == TransactionType.id) \
                .join(Account, Transaction.account_id == Account.id) \
                .filter_by(user_id=user_id)
             )
            return TransactionDetailsSchema.model_validate(transaction.one(), from_attributes=True)

    async def list_transactions(self, user_id: int, filters: dict={}, limit: int=10, offset=0) -> list[TransactionSchema]:
        async with self.session() as session:
            transactions = await session.execute(
                select(
                    Transaction.id,
                    Transaction.type_id,
                    TransactionType.type_name,
                    Transaction.account_id,
                    Account.name.label("account_name"),
                    Transaction.amount,
                    Transaction.currency,
                    Transaction.amount_in_account_currency,
                    Transaction.transaction_date,
                ) \
                .join(TransactionType, Transaction.type_id == TransactionType.id) \
                .join(Account) \
                .filter_by(user_id=user_id)
                .filter(Transaction.is_deleted==False, **filters) \
                .order_by(Transaction.id.desc()) \
                .limit(limit).offset(offset)
            )
            return [TransactionSchema.model_validate(transaction, from_attributes=True) 
                    for transaction in transactions.all()]
    
    async def delete_transaction(self, id: int, user_id: int) -> None:
        async with self.session() as session:
            await session.execute(
                update(Transaction) \
                .where(Transaction.id==id) \
                .where(Account.user_id==user_id) \
                .values(is_deleted=True, deleted_at=datetime.datetime.now())
            )
            await session.commit()

    async def _create_transaction(self, transaction: dict) -> None:
        async with self.session() as session:
            new_transaction = Transaction(**transaction)
            session.add(new_transaction)
            await session.commit()
        
    async def create_topup(self, transaction: TransactionTopupCreateSchema) -> None:
        await self._create_transaction(transaction.model_dump())

    async def create_withdraw(self, transaction: TransactionWithdrawalCreateSchema) -> None:
        await self._create_transaction(transaction.model_dump())

    async def create_transfer(self, transaction: TransactionTransferCreateSchema) -> None:
        async with self.session() as session:
            from_transaction, to_transaction = transaction.model_dump().values()
            session.add_all([
                Transaction(**from_transaction),
                Transaction(**to_transaction)
            ])
            await session.commit()

    async def create_purchase(self, transaction: TransactionPurchaseCreateSchema) -> None:
        await self._create_transaction(transaction.model_dump())
