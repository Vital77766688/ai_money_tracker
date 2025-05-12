from enum import StrEnum


class TransactionTypesEnum(StrEnum):
    TOPUP = 'Topup'
    WITHDRAW = 'Withdraw'
    TRANSFER = 'Transfer'
    PURCHASE = 'Purchase'
