from sqlalchemy import select, func, and_
from sqlalchemy.exc import NoResultFound
from . import BaseRepository
from .transaction_repository import TransactionRepository
from budget.models import Account, AccountType, Transaction
from budget.schemas import AccountCreateSchema, AccountSchema, TransactionTopupCreateSchema, TransactionWithdrawalCreateSchema


class AccountRepository(BaseRepository):
    async def create_account(self, account: AccountCreateSchema) -> None:
        """
        Creates new account and inserts transaction with inital balance.
        TODO: Think of the way to create an account and transaction inside one transaction
        """
        async with self.session() as session:
            new_account = Account(**account.model_dump())
            session.add(new_account)
            await session.commit()
            await session.refresh(new_account)
        transaction_repo = TransactionRepository(self.session)
        if account.balance > 0:
            transaction = TransactionTopupCreateSchema(
                account_id=new_account.id,
                amount=account.balance,
                currency=account.currency,
                description='Init Transaction'
            )
            await transaction_repo.create_topup(transaction)
        elif account.balance < 0:
            transaction = TransactionWithdrawalCreateSchema(
                account_id=new_account.id,
                amount=account.balance,
                currency=account.currency,
                description='Init Transaction'
            )
            await transaction_repo.create_withdraw(transaction)

    async def get_account_by_id(self, id: int, user_id: int) -> AccountSchema:
        """
        Return accounts details.
        Balances is calculated as sum of amounts of all transactions
        """
        async with self.session() as session:
            account = await session.execute(
                select(Account.user_id,
                       Account.name,
                       Account.type_id,
                       Account.currency,
                       AccountType.type_name,
                       func.coalesce(func.sum(Transaction.amount), 0.).label('balance'),
                       Account.id,
                       Account.created_at) \
                .filter_by(id=id, user_id=user_id)
                .join(AccountType) \
                .join(Transaction, and_(
                        Transaction.account_id==Account.id, 
                        Transaction.is_deleted==False
                    ), isouter=True
                ) \
                .group_by(
                    Account.user_id,
                    Account.name,
                    Account.type_id,
                    Account.currency,
                    AccountType.type_name,
                    Account.id,
                    Account.created_at
                )
            )
            return AccountSchema.model_validate(account.one(), from_attributes=True)
        
    async def get_accounts_by_user_id(self, user_id: int) -> list[AccountSchema]:
        async with self.session() as session:
            accounts = await session.execute(
                select(Account.user_id,
                       Account.name,
                       Account.type_id,
                       Account.currency,
                       AccountType.type_name,
                       func.coalesce(func.sum(Transaction.amount), 0.).label('balance'),
                       Account.id,
                       Account.created_at) \
                .filter_by(user_id=user_id) \
                .join(AccountType)
                .join(Transaction, and_(
                        Transaction.account_id==Account.id, 
                        Transaction.is_deleted==False
                    ), isouter=True
                ) \
                .group_by(
                    Account.user_id,
                    Account.name,
                    Account.type_id,
                    Account.currency,
                    AccountType.type_name,
                    Account.id,
                    Account.created_at
                ) \
                .order_by(Account.created_at.asc())
            )
            return [AccountSchema.model_validate(account, from_attributes=True) 
                    for account in accounts.all()]
        
    async def get_user_balance(self, user_id: int) -> float:
        async with self.session() as session:
            balance = await session.execute(
                select(func.sum(Transaction.amount).label('balance')) \
                .join_from(Account, Transaction) \
                .filter(
                    Account.user_id==user_id,
                    Transaction.is_deleted==False
                )
            )
            balance = balance.scalar_one()
            if balance is None:
                raise NoResultFound
            return balance
