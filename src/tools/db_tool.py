from agents import function_tool

from models.statements import Statement


@function_tool
def persist_transactions(statement: Statement):
    for account in statement.accounts:
        print(account.account_name, account.account_number)
        for transaction in account.transactions:
            print(transaction)


@function_tool
def query_transactions():
    pass
