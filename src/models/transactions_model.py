from pydantic import BaseModel
from datetime import date

class TransactionsModel(BaseModel):
    date: date
    amount: float
    other_party: str
    other_party_account: str