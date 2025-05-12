from typing import List
from sqlalchemy import select, func
from sqlalchemy.orm import contains_eager
from sqlalchemy.exc import NoResultFound
from core.schemas import Filter
from core.repositories import BaseRepository
from core.exceptions import InstanceNotFound
from budget.models import User, Account, Currency, Transaction, TransactionType
from budget.schemas import (
    UserCreateSchema,
    UserUpdateSchema,
    AccountCreateSchema,
    AccountUpdateSchema,
    TransactionCreateSchema,
    TransactionUpdateSchema,
    TransactionReadSchema
) 


class UserRepository(BaseRepository[User, UserCreateSchema, UserUpdateSchema]):
    model = User
    allowed_fields = {
        'username': (User.name, None),
        'telegram_id': (User.telegram_id, None)
    }

    async def get_by_telegram_id(self, telegram_id: int) -> User:
        stmt = select(User).filter(User.telegram_id==telegram_id)
        user = await self._select(stmt)
        try:
            return user.scalar_one()
        except NoResultFound:
            raise InstanceNotFound


class AccountRepository(BaseRepository[Account, AccountCreateSchema, AccountUpdateSchema]):
    model = Account
    allowed_fields = {
        'id': (Account.id, None),
        'user_id': (Account.user_id, None),
        'account_name': (Account.name, None),
        'currency': (Account.currency, None),
        'is_active': (Account.is_active, None)
    }

    async def get_user_balance(self, user_id: int) -> float:
        stmt = select(func.sum(self.model.balance)).filter(self.model.user_id==user_id)
        balance = await self._select(stmt)
        return balance.scalar_one_or_none() or 0.        
    
    async def list_currencies(self) -> Currency:
        currencies = await self._select(select(Currency.iso_code, Currency.name))
        return currencies.all()


class TransactionRepository(BaseRepository[Transaction, TransactionCreateSchema, TransactionUpdateSchema]):
    model = Transaction
    allowed_fields = {
        'id': (Transaction.id, None),
        'type': (TransactionType.type_name, 'type'),
        'user_id': (Account.user_id, 'account'),
        'account_id': (Transaction.account_id, None),
        'transaction_date': (Transaction.transaction_date, None),
        'reference_transaction_id': (Transaction.reference_transaction_id, None)
    }

    async def get_transaction_type(self, name: str) -> int:
        stmt = select(TransactionType).where(TransactionType.type_name==name)
        type_ = await self._select(stmt)
        return type_.scalar_one()

    async def getDTO(self, user_id: int, account_id: int, transaction_id: int) -> TransactionReadSchema:
        stmt = select(Transaction) \
            .join(Transaction.type) \
            .join(Transaction.account) \
            .options(
                contains_eager(Transaction.type), 
                contains_eager(Transaction.account)
            ) \
            .where(
                Transaction.id==transaction_id, 
                Account.id==account_id, 
                Account.user_id==user_id,
                Transaction.is_deleted == False
            )
        transaction = await self._select(stmt)
        try:
            return TransactionReadSchema.model_validate(transaction.scalar_one())
        except NoResultFound:
            raise InstanceNotFound
        
    async def listDTO(self, user_id: int, filters: Filter=None, limit: int=10, offset: int=0) -> List[TransactionReadSchema]:
        stmt = select(Transaction) \
            .join(Transaction.type) \
            .join(Transaction.account) \
            .options(
                contains_eager(Transaction.type),
                contains_eager(Transaction.account)
            ) \
            .where(
                Account.user_id==user_id,
                Transaction.is_deleted == False
            ) \
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc()) \
            .limit(limit).offset(offset)
        if filters:
            where_clause, joins = self._build_filter(filters)
            stmt = self._apply_joins(stmt, joins, False)
            stmt = stmt.where(where_clause)
        transactions = await self._select(stmt)
        return [
            TransactionReadSchema.model_validate(transaction)
            for transaction in transactions.scalars().all()
        ] 
        
