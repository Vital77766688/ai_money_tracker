import datetime
from typing import List, Dict, Any
from thefuzz import process, fuzz
from core.schemas import Filter
from core.exceptions import (
    InstanceNotFound, 
    ConstraintsViolation, 
    FilterFieldNotAllowed, 
    FilterOperationNotAllowed
)
from budget.uow import UnitOfWork
from budget.enums import TransactionTypesEnum
from budget.schemas import (
    UserCreateSchema,
    UserReadSchema,
    AccountCreateSchema,
    AccountUpdateInputSchema,
    AccountUpdateSchema,
    AccountReadSchema,
    CurrencyReadSchema,
    TransactionTypeReadSchema,
    TransactionCreateSchema,
    TransactionTransferFromCreateSchema,
    TransactionTransferToCreateSchema,
    TransactionCreateInputSchema,
    TransactionPurchaseCreateInputSchema,
    TransactionTransferCreateInputSchema,
    TransactionReadSchema
)
from budget.exceptions import (
    UserNotFound, 
    UserAlreadyExists,
    AccountNotFound,
    AccountAlreadyExists,
    CurrencyNotFound,
    TransactionNotFound
)


class BaseService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow


class UserService(BaseService):
    async def create_user(self, user_data: UserCreateSchema) -> UserReadSchema:
        try:
            user = await self.uow.users.create(user_data)
            return UserReadSchema.model_validate(user)
        except ConstraintsViolation:
            raise UserAlreadyExists

    async def get_user_by_telegram_id(self, telegram_id: int) -> UserReadSchema:
        try:
            user = await self.uow.users.get_by_telegram_id(telegram_id=telegram_id)
            return UserReadSchema.model_validate(user)
        except InstanceNotFound:
            raise UserNotFound


class AccountService(BaseService):
    async def create_account(self, account_data: AccountCreateSchema) -> AccountReadSchema:
        try:
            account = await self.uow.accounts.create(account_data)
            return AccountReadSchema.model_validate(account)
        except ConstraintsViolation:
            raise AccountAlreadyExists

    async def get_account(self, account_id: int, user_id: int) -> AccountReadSchema:
        user_filter = Filter.model_validate([{'field': 'user_id', 'op': '=', 'value': user_id}])
        try:
            account = await self.uow.accounts.get(id=account_id, filters=user_filter)
            return AccountReadSchema.model_validate(account)
        except InstanceNotFound:
            raise AccountNotFound

    async def list_accounts(self, user_id: int, filters: Filter=None, limit: int=10, offset: int=0) -> List[AccountReadSchema]:
        filters: List = filters.model_dump() if filters else []
        filters.append({'field': 'user_id', 'op': '=', 'value': user_id})
        accounts = await self.uow.accounts.list(filters=Filter.model_validate(filters), limit=limit, offset=offset)
        return [
            AccountReadSchema.model_validate(account)
            for account in accounts
        ]

    async def update_account(self, account_data: AccountUpdateInputSchema) -> AccountReadSchema:
        account_data_dict = account_data.model_dump()
        account_id = account_data_dict.pop('id')
        user_id = account_data_dict.pop('user_id')
        user_filter = Filter.model_validate([{'field': 'user_id', 'op': '=', 'value': user_id}])
        try:
            account = await self.uow.accounts.update(
                id=account_id, 
                item_data=AccountUpdateSchema.model_validate(account_data_dict),
                filters=user_filter
            )
            return AccountReadSchema.model_validate(account)
        except InstanceNotFound:
            raise AccountNotFound
        except ConstraintsViolation:
            raise AccountAlreadyExists

    async def get_user_balance(self, user_id: int) -> float:
        return await self.uow.accounts.get_user_balance(user_id=user_id)

    async def find_currency(self, name: str) -> CurrencyReadSchema:
        currencies = await self.uow.accounts.list_currencies()

        # Trying to find similar value
        choices = [f'{c.iso_code.upper()}:{c.name.upper()}' for c in currencies]
        similarities = process.extract(name.strip().upper(), choices, scorer=fuzz.partial_token_sort_ratio, limit=1)
        currency, prob = similarities[0]

        # Consider that there're no rows returtn
        if prob <= 50:
            raise CurrencyNotFound
        iso_code, _ = currency.split(':')

        # Returning the value without upper() and slicers
        currency = [f"{c.name}" for c in currencies if c.iso_code==iso_code][0]
        return CurrencyReadSchema(name=currency, iso_code=iso_code)



class TransactionService(BaseService):
    async def get_transaction(self, user_id: int, account_id: int, transaction_id: int) -> TransactionReadSchema:
        try:
            return await self.uow.transactions.getDTO(user_id=user_id, account_id=account_id, transaction_id=transaction_id)
        except InstanceNotFound:
            raise TransactionNotFound

    async def list_transactions(self, user_id: int, filters: Filter=None, limit: int=10, offset: int=0) -> List[TransactionReadSchema]:
        return await self.uow.transactions.listDTO(user_id=user_id, filters=filters, limit=limit, offset=offset)

    async def _create_transaction(self, type_: TransactionTypeReadSchema, transaction_data_dict: Dict[str, Any]) -> TransactionReadSchema:
        user_id = transaction_data_dict.pop('user_id')
        account_id = transaction_data_dict.pop('account_id')
        try:
            user_filter = Filter.model_validate([{'field': 'user_id', 'op': '=', 'value': user_id}])
            account = await self.uow.accounts.get(id=account_id, filters=user_filter)
        except InstanceNotFound:
            raise AccountNotFound

        transaction = await self.uow.transactions.create(
            item_data=TransactionCreateSchema(
                type=TransactionTypeReadSchema.model_validate(type_),
                account=account,
                **transaction_data_dict
            )
        )
        account.balance += transaction.amount
        return TransactionReadSchema.model_validate(transaction)

    async def create_topup(self, transaction_data=TransactionCreateInputSchema) -> TransactionReadSchema:
        type_ = await self.uow.transactions.get_transaction_type(name=TransactionTypesEnum.TOPUP)
        return await self._create_transaction(
            type_=TransactionTypeReadSchema.model_validate(type_),
            transaction_data_dict=transaction_data.model_dump()
        )

    async def create_withdraw(self, transaction_data=TransactionCreateInputSchema):
        type_ = await self.uow.transactions.get_transaction_type(name=TransactionTypesEnum.WITHDRAW)
        return await self._create_transaction(
            type_=TransactionTypeReadSchema.model_validate(type_),
            transaction_data_dict=transaction_data.model_dump()
        )

    async def create_purchase(self, transaction_data=TransactionPurchaseCreateInputSchema):
        type_ = await self.uow.transactions.get_transaction_type(name=TransactionTypesEnum.PURCHASE)
        return await self._create_transaction(
            type_=TransactionTypeReadSchema.model_validate(type_),
            transaction_data_dict=transaction_data.model_dump()
        )

    async def create_transfer(self, transaction_data=TransactionTransferCreateInputSchema) -> TransactionReadSchema:
        type_ = await self.uow.transactions.get_transaction_type(name=TransactionTypesEnum.TRANSFER)
        transaction_data_dict = transaction_data.model_dump()
        user_id = transaction_data_dict.pop('user_id')
        account_id = transaction_data_dict.pop('account_id')
        account_id_to = transaction_data_dict.pop('account_id_to')
        accounts = await self.uow.accounts.list(
            filters = Filter.model_validate([
                {'field': 'user_id', 'op': '=', 'value': user_id},
                {'field': 'id', 'op': 'in', 'value': [account_id, account_id_to]}
            ]),
            limit=2
        )
        try:
            transaction_from = await self.uow.transactions.create(
                item_data=TransactionTransferFromCreateSchema(
                    type=type_,
                    account=[account for account in accounts if account.id==account_id][0],
                    **transaction_data_dict
                )
            )
            _ = transaction_data_dict.pop('amount_in_account_currency')
            transaction_to = await self.uow.transactions.create(
                item_data=TransactionTransferToCreateSchema(
                    type=type_,
                    account=[account for account in accounts if account.id==account_id_to][0],
                    amount_in_account_currency=transaction_data_dict.pop('amount_in_account_currency_to', None),
                    **transaction_data_dict
                )
            )
            transaction_from.reference_transaction_id=transaction_to.id
            transaction_to.reference_transaction_id=transaction_from.id
            [account for account in accounts if account.id==account_id][0].balance += transaction_from.amount
            [account for account in accounts if account.id==account_id_to][0].balance += transaction_to.amount
            return TransactionReadSchema.model_validate(transaction_from)
        except IndexError:
            raise AccountNotFound

    async def update_transaction(self) -> None:
        raise NotImplementedError

    async def delete_transaction(self, user_id: int, account_id: int, transaction_id: int) -> None:
        try:
            transaction = await self.uow.transactions.get(
                id=transaction_id, 
                filters=Filter.model_validate([
                    {'field': 'user_id', 'op': '=', 'value': user_id},
                    {'field': 'account_id', 'op': '=', 'value': account_id}
                ])
            )
        except InstanceNotFound:
            raise TransactionNotFound
        
        reference_transactions = await self.uow.transactions.list(
            filters=Filter.model_validate([
                {'field': 'reference_transaction_id', 'op': '=', 'value': transaction_id}
            ])
        )

        transaction.is_deleted = True
        transaction.deleted_at = datetime.datetime.now()
        account = await self.uow.accounts.get(id=transaction.account_id)
        account.balance -= transaction.amount
        for ref_transaction in reference_transactions:
            ref_transaction.is_deleted = True
            ref_transaction.deleted_at = datetime.datetime.now()
            ref_account = await self.uow.accounts.get(id=ref_transaction.account_id)
            ref_account.balance -= ref_transaction.amount
