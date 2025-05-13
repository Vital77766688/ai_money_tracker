import datetime
from pydantic import BaseModel, Field, model_validator, model_serializer, field_serializer, ConfigDict
from budget.enums import TransactionTypesEnum


class UserCreateSchema(BaseModel):
    name: str
    telegram_id: int


class UserUpdateSchema(BaseModel):
    ...


class UserReadSchema(BaseModel):
    id: int
    name: str
    telegram_id: int

    model_config = ConfigDict(
        from_attributes=True
    )


class AccountCreateSchema(BaseModel):
    user_id: int
    name: str = Field(..., max_length=20)
    description: str | None = Field(None, max_length=255)
    currency: str = Field(..., min_length=3, max_length=3)
    balance: float


class AccountUpdateSchema(BaseModel):
    name: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=255)


class AccountUpdateInputSchema(AccountUpdateSchema):
    id: int
    user_id: int


class AccountReadSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    currency: str
    balance: float
    created_at: datetime.datetime
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )

    @field_serializer('created_at')
    def serializer_created_at(self, value: datetime.datetime) -> str:
        return value.strftime('%Y-%m-%d %H:%M:%S')


class CurrencyReadSchema(BaseModel):
    iso_code: str
    name: str


class TransactionTypeReadSchema(BaseModel):
    id: int
    type_name: TransactionTypesEnum

    model_config = ConfigDict(
        from_attributes=True
    )


class TransactionCreateSchema(BaseModel):
    type: TransactionTypeReadSchema
    account: AccountReadSchema
    amount: float
    currency: str = Field(..., min_length=3, max_length=3)
    amount_in_account_currency: float | None = None
    transaction_date: datetime.datetime | None = None
    description: str | None = None

    @model_validator(mode='after')
    def validate_model(self):
        if self.account.currency != self.currency and self.amount_in_account_currency is None:
            raise ValueError('If `account currency` and `transaction currency` are different then `amount_in_account_currency` must be provided')
        return self

    def _return_serialized(self, amount: float, amount_in_account_currency: float):
        return {
            'type_id': self.type.id,
            'account_id': self.account.id,
            'amount': amount,
            'currency': self.currency,
            'amount_in_account_currency': amount_in_account_currency,
            'transaction_date': self.transaction_date,
            'description': self.description
        }

    @model_serializer(mode='plain')
    def serialize_model(self):
        positive = lambda x: abs(x)
        negative = lambda x: -1 * abs(x)
        if self.type.type_name in [TransactionTypesEnum.TOPUP]:
            amount = positive(self.amount)
            amount_in_account_currency = positive(self.amount_in_account_currency or self.amount)
        elif self.type.type_name in [TransactionTypesEnum.WITHDRAW, TransactionTypesEnum.PURCHASE]:
            amount = negative(self.amount)
            amount_in_account_currency = negative(self.amount_in_account_currency or self.amount)
        else:
            raise ValueError("Can't serialize amount")
        return self._return_serialized(amount=amount, amount_in_account_currency=amount_in_account_currency)


class TransactionTransferFromCreateSchema(TransactionCreateSchema):
    @model_serializer(mode='plain')
    def serialize_model(self):
        amount = -1 * abs(self.amount)
        amount_in_account_currency = -1 * abs(self.amount_in_account_currency or self.amount)
        return self._return_serialized(amount=amount, amount_in_account_currency=amount_in_account_currency)


class TransactionTransferToCreateSchema(TransactionCreateSchema):
    @model_serializer(mode='plain')
    def serialize_model(self):
        amount = abs(self.amount)
        amount_in_account_currency = abs(self.amount_in_account_currency or self.amount)
        return self._return_serialized(amount=amount, amount_in_account_currency=amount_in_account_currency)


class TransactionCreateInputSchema(BaseModel):
    user_id: int
    account_id: int
    amount: float
    currency: str = Field(..., min_length=3, max_length=3)
    amount_in_account_currency: float | None = None
    transaction_date: datetime.date | None = None
    description: str | None = None


class TransactionPurchaseCreateInputSchema(TransactionCreateInputSchema):
    description: str


class TransactionTransferCreateInputSchema(TransactionCreateInputSchema):
    account_id_to: int
    amount_in_account_currency_to: float | None = None



class TransactionUpdateSchema(BaseModel):
    ...


class TransactionReadSchema(BaseModel):
    id: int
    type: TransactionTypeReadSchema
    account: AccountReadSchema
    amount: float
    currency: str
    amount_in_account_currency: float
    transaction_date: datetime.date

    model_config = ConfigDict(
        from_attributes=True
    )

    @field_serializer('transaction_date')
    def serializer_transaction_date(self, value: datetime.datetime) -> str:
        return value.strftime('%Y-%m-%d %H:%M:%S')
