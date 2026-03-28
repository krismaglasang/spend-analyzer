from models.accounts_model import AccountsModel
from models.transactions_model import TransactionsModel
from agents import function_tool


@function_tool
def load_to_db():
    print("successfully loaded to db")

