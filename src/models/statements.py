from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    transaction_date: date
    amount: Decimal
    other_party: str | None = None
    other_party_account: str | None = None


class Account(BaseModel):
    account_name: str
    account_number: str
    transactions: list[Transaction]


class Statement(BaseModel):
    accounts: list[Account]


class PersistResult(BaseModel):
    accounts_processed: int
    transactions_inserted: int
    transactions_skipped: int
    status: Literal["success", "partial", "no_new_data"]


class QueryTransactionsResult(BaseModel):
    row_count: int
    truncated: bool
    executed_sql: str
    columns: list[str]
    rows: list[dict[str, Any]] = Field(default_factory=list)
    successful_query: str
