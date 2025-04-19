import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, field_serializer, model_serializer


class UserCreateSchema(BaseModel):
    name: str
    telegram_id: int


class UserSchema(UserCreateSchema):
    id: int


class AccountTypeSchema(BaseModel):
    id: int
    type_name: str


class AccountCreateSchema(BaseModel):
    user_id: int
    name: str = Field(None, max_length=50)
    type_id: int
    currency: str = Field(None, max_length=3)
    balance: float | None = None

    @field_serializer('currency', mode="plain")
    def serialize_currency(self, value: str) -> str:
        return value.upper()


class AccountSchema(AccountCreateSchema):
    type_name: str
    balance: float
    id: int
    created_at: str  # Use str for date representation in JSON

    @field_validator("created_at", mode="before")
    @classmethod
    def serialize_created_at(cls, value: datetime.datetime) -> str:
        return value.strftime("%Y-%m-%d")


class CategoryCreateSchema(BaseModel):
    name: str


class CategorySchema(CategoryCreateSchema):
    id: int


class VendorCreateSchema(BaseModel):
    name: str


class VendorSchema(VendorCreateSchema):
    id: int


class ItemCreateSchema(BaseModel):
    name: str
    category_id: int
    vendor_id: int
    price: float


class ItemSchema(ItemCreateSchema):
    id: int


class TransactionTypesEnum(int, Enum):
    TOPUP = 1
    WITHDRAW = 2
    TRANSFER = 3
    PURCHASE = 4
    DELETE = 5


class TranasctionCreateSchema(BaseModel):
    account_id: int
    amount: float
    currency: str
    amount_in_account_currency: float | None = None
    transaction_date: str | None = None
    description: str | None = None

    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_transaction_date(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                datetime.datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD.")
        return value

    def _ser_model(self, type_id: int) -> dict:
        return {
            "type_id": type_id,
            "account_id": self.account_id,
            "amount": self.amount,
            "currency": self.currency,
            "amount_in_account_currency": self.amount_in_account_currency,
            "transaction_date": self.transaction_date,
            "description": self.description,
            "deleted_at": None
        }


class TransactionTopupCreateSchema(TranasctionCreateSchema):
    @model_serializer(mode="plain")
    def ser_model(self) -> dict:
        type_id = TransactionTypesEnum.TOPUP.value
        self.amount = abs(self.amount)
        self.amount_in_account_currency = abs(self.amount_in_account_currency) \
            if self.amount_in_account_currency is not None \
            else self.amount
        
        return self._ser_model(type_id)


class TransactionWithdrawalCreateSchema(TranasctionCreateSchema):
    @model_serializer(mode="plain")
    def ser_model(self) -> dict:
        type_id = TransactionTypesEnum.WITHDRAW.value
        self.amount = -abs(self.amount)
        self.amount_in_account_currency = -abs(self.amount_in_account_currency) \
            if self.amount_in_account_currency is not None \
            else self.amount
        
        return self._ser_model(type_id)


class TransactionPurchaseCreateSchema(TranasctionCreateSchema):
    description: str

    @model_serializer(mode="plain")
    def ser_model(self) -> dict:
        type_id = TransactionTypesEnum.PURCHASE.value
        self.amount = -abs(self.amount)
        self.amount_in_account_currency = -abs(self.amount_in_account_currency) \
            if self.amount_in_account_currency is not None \
            else self.amount
        
        return self._ser_model(type_id)


class TransactionTransferCreateSchema(TranasctionCreateSchema):
    account_to_id: int
    amount_to: float | None = None
    currency_to: str | None = None
    amount_in_account_currency_to: float | None = None

    @model_serializer(mode="plain")
    def ser_model(self) -> dict:
        type_id = TransactionTypesEnum.TRANSFER.value
        self.amount = -abs(self.amount)
        self.amount_in_account_currency = -abs(self.amount_in_account_currency) \
            if self.amount_in_account_currency is not None \
            else self.amount
        from_model = self._ser_model(type_id=type_id)

        amount_to = abs(self.amount_to) if self.amount_to is not None else abs(self.amount)
        currency_to = self.currency_to if self.currency_to is not None else self.currency
        amount_in_account_currency_to = abs(self.amount_in_account_currency_to) \
            if self.amount_in_account_currency_to is not None \
            else amount_to

        to_model = {
            "type_id": type_id,
            "account_id": self.account_to_id,
            "amount": amount_to,
            "currency": currency_to,
            "amount_in_account_currency": amount_in_account_currency_to,
            "transaction_date": self.transaction_date,
            "description": self.description,
        }

        return {'from': from_model, 'to': to_model}


class TransactionSchema(BaseModel):
    id: int
    type_id: int
    type_name: str
    account_id: int
    account_name: str
    amount: float
    currency: str
    amount_in_account_currency: float
    transaction_date: str

    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_transaction_date(cls, value: datetime.date) -> str:
        return value.strftime("%Y-%m-%d")
        

class TransactionDetailsSchema(TransactionSchema):
    description: str | None = None
