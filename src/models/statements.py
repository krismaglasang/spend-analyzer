from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class Transaction(BaseModel):
    transaction_date: date
    amount: Decimal
    other_party: str
    other_party_account: str


class Account(BaseModel):
    account_name: str
    account_number: str
    transactions: list[Transaction]


class Statement(BaseModel):
    accounts: list[Account]


class PersistResult(BaseModel):
    inserted_count: int
    skipped_count: int
    status: Literal["success", "partial", "failed"]
