from pydantic import BaseModel
from models.transactions_model import TransactionsModel


class AccountsModel(BaseModel):
    account_name: str
    account_number: str
    transactions: TransactionsModel
    