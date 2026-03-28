from pydantic import BaseModel


class ExpenseExtractFile(BaseModel):
    expenses: list
    amounts: list
    