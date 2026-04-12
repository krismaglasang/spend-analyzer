import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from agents import function_tool
from dotenv import load_dotenv

from models.statements import PersistResult, QueryTransactionsResult, Statement

load_dotenv()

MAX_ROWS = 500
ALLOWED_RELATIONS = {"accounts", "transactions"}

FORBIDDEN_SQL_PATTERNS = [
    r";",  # block multiple statements
    r"--",  # block inline comments
    r"/\*",  # block block comments
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bCOPY\b",
    r"\bMERGE\b",
    r"\bCALL\b",
    r"\bVACUUM\b",
    r"\bANALYZE\b",
    r"\bpg_catalog\b",
    r"\binformation_schema\b",
    r"\bpg_\w+\b",
]


def _get_db(envvar: str) -> str:
    dsn = os.getenv(envvar)
    if not dsn:
        raise ValueError(f"{envvar} not set")
    return dsn


@function_tool
def persist_transactions(statement: Statement) -> PersistResult:

    accounts_processed = 0
    transactions_inserted = 0
    transactions_skipped = 0

    dsn = _get_db("DATABASE_URL")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for account in statement.accounts:
                cur.execute(
                    """
                    insert into accounts (account_name, account_number)
                    values (%s, %s)
                    on conflict (account_number) do update set account_name = excluded.account_name
                    returning id;
                    """,
                    (account.account_name, account.account_number),
                )

                account_id = cur.fetchone()[0]
                accounts_processed += 1

                for transaction in account.transactions:
                    cur.execute(
                        """
                        insert into transactions (account_id, transaction_date, amount, other_party, other_party_account)
                        values (%s, %s, %s, %s, %s)
                        on conflict on constraint transactions_natural_key do nothing;
                        """,
                        (
                            account_id,
                            transaction.transaction_date,
                            transaction.amount,
                            transaction.other_party,
                            transaction.other_party_account,
                        ),
                    )
                    if cur.rowcount == 1:
                        transactions_inserted += 1
                    else:
                        transactions_skipped += 1

    return PersistResult(
        accounts_processed=accounts_processed,
        transactions_inserted=transactions_inserted,
        transactions_skipped=transactions_skipped,
        status=(
            "success"
            if transactions_inserted > 0 and transactions_skipped == 0
            else "partial"
            if transactions_inserted > 0 and transactions_skipped > 0
            else "no_new_data"
        ),
    )


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _validate_and_prepare_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty")

    cleaned = sql.strip()

    if not re.match(r"^(select|with)\b", cleaned, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            raise ValueError(f"Forbidden SQL pattern detected: {pattern}")

    relation_pattern = (
        r"\b(" + "|".join(re.escape(name) for name in ALLOWED_RELATIONS) + r")\b"
    )
    if not re.search(relation_pattern, cleaned, flags=re.IGNORECASE):
        raise ValueError(
            "Query must reference at least one approved analytics view: "
            + ", ".join(sorted(ALLOWED_RELATIONS))
        )

    if not re.search(r"\blimit\s+\d+\b", cleaned, flags=re.IGNORECASE):
        cleaned = f"{cleaned.rstrip()} LIMIT {MAX_ROWS}"

    return cleaned


@function_tool
def query_transactions(sql: str) -> QueryTransactionsResult:
    """
    Execute a read-only analytics SQL query against approved finance tables.

    Use this tool when you need flexible financial analysis that cannot be handled
    by a fixed function, such as:
    - "How much did I spend last month?"
    - "How much money went to this account?"
    - "Who were my top merchants this year?"
    - "Show my spending by month."

    The query must be valid PostgreSQL SQL.

    Approved tables and schema:

    Table: accounts
    - Purpose: one row per account
    - Columns:
      - id INTEGER PRIMARY KEY
      - account_name TEXT NOT NULL
      - account_number TEXT NOT NULL UNIQUE
      - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    Table: transactions
    - Purpose: one row per transaction
    - Columns:
      - id INTEGER PRIMARY KEY
      - account_id INTEGER NOT NULL
      - transaction_date DATE NOT NULL
      - amount NUMERIC(12,2) NOT NULL
      - other_party TEXT
      - other_party_account TEXT
      - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    Join rules:
    - transactions.account_id references accounts.id
    - When joining transactions to accounts, use:
      transactions.account_id = accounts.id

    Business meaning:
    - Use transactions.transaction_date for date filtering and time grouping.
    - Use transactions.amount for totals, averages, and counts involving money.
    - Use transactions.other_party when the user asks about merchants, payees, counterparties, or who money went to / came from.
    - Use transactions.other_party_account when the user asks about the counterparty account number.
    - Use accounts.account_name or accounts.account_number when the user asks about a specific owned account.
    - Do not invent columns such as merchant_name, category, balance, transaction_type, debit_credit_flag, or account_name inside the transactions table.
    - account_name is in the accounts table, not the transactions table.
    - account_number is in the accounts table, not the transactions table.
    - account_id is in the transactions table and must be joined to accounts.id.

    SQL dialect requirements:
    - Generate PostgreSQL syntax only.
    - Prefer PostgreSQL conventions where appropriate, such as:
      - ILIKE for case-insensitive text matching
      - DATE_TRUNC(...) for time grouping
      - CURRENT_DATE or NOW() for current date/time logic
      - INTERVAL syntax such as INTERVAL '1 month'
      - CAST(... AS ...) or ::type for casting
      - LIMIT for row limiting
    - Do not use non-PostgreSQL syntax such as:
      - MySQL: DATE_SUB(), STR_TO_DATE(), IFNULL()
      - SQL Server: TOP, GETDATE(), ISNULL()
      - backticks for identifiers
      - SQLite-specific date syntax unless it is also valid PostgreSQL
    - Do not terminate your PostgreSQL queries with ';'

    Rules:
    - Only generate a single SELECT query.
    - Only query the approved tables listed above.
    - Prefer aggregations for "how much", "total", "average", and "count" questions.
    - Add date filters when the user asks about a period.
    - Select only the columns needed to answer the question.
    - Do not attempt INSERT, UPDATE, DELETE, MERGE, UPSERT, DDL, schema inspection, or admin SQL.
    - Do not query information_schema, pg_catalog, or other system tables.
    - Do not modify the database in any way.
    - Do not reference any table or column not explicitly listed in this description.

    Query-writing guidance:
    - If the user asks about spending from one of the user's accounts, usually join transactions to accounts and filter on accounts.account_name or accounts.account_number.
    - If the user asks about merchants or counterparties, usually group or filter by transactions.other_party.
    - If the user asks for trends over time, usually group by DATE_TRUNC(...) on transactions.transaction_date.
    - If the user asks for outgoing spend, use the sign convention stored in the data. In this app, spending/outgoing transactions are typically filtered with amount < 0, and incoming money with amount > 0.

    Examples:

    Question: "How much did I spend last month?"
    SQL:
    SELECT COALESCE(SUM(tr.amount), 0) AS total_spent
    FROM transactions AS tr
    WHERE tr.amount < 0
      AND tr.transaction_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
      AND tr.transaction_date < DATE_TRUNC('month', CURRENT_DATE)

    Question: "Show my spending by month."
    SQL:
    SELECT DATE_TRUNC('month', tr.transaction_date) AS month,
           SUM(tr.amount) AS total_spent
    FROM transactions AS tr
    WHERE tr.amount < 0
    GROUP BY 1
    ORDER BY 1

    Question: "Who were my top merchants this year?"
    SQL:
    SELECT tr.other_party,
           SUM(ABS(tr.amount)) AS total_spent
    FROM transactions AS tr
    WHERE tr.amount < 0
      AND tr.transaction_date >= DATE_TRUNC('year', CURRENT_DATE)
    GROUP BY tr.other_party
    ORDER BY total_spent DESC
    LIMIT 10

    Question: "How much went from my Everyday account to AMEX?"
    SQL:
    SELECT COALESCE(SUM(tr.amount), 0) AS total_amount
    FROM transactions AS tr
    INNER JOIN accounts AS ac
      ON tr.account_id = ac.id
    WHERE ac.account_name = 'Everyday'
      AND tr.other_party = 'AMEX'
      AND tr.amount < 0

    Question: "Show transactions for account number 02-1234-1234567-000 in March 2026."
    SQL:
    SELECT tr.transaction_date,
           tr.amount,
           tr.other_party,
           tr.other_party_account
    FROM transactions AS tr
    INNER JOIN accounts AS ac
      ON tr.account_id = ac.id
    WHERE ac.account_number = '02-1234-1234567-000'
      AND tr.transaction_date >= DATE '2026-03-01'
      AND tr.transaction_date < DATE '2026-04-01'
    ORDER BY tr.transaction_date ASC, tr.id ASC
    """
    dsn = _get_db("DATABASE_URL_READ_ONLY")
    safe_sql = _validate_and_prepare_sql(sql)

    with psycopg.connect(
        dsn,
        options="-c default_transaction_read_only=on -c statement_timeout=5000",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(safe_sql)

            if cur.description is None:
                raise ValueError("Query did not return a result set")

            columns = [col.name for col in cur.description]
            raw_rows = cur.fetchall()

    rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        row_dict = {
            columns[i]: _serialize_value(raw_row[i]) for i in range(len(columns))
        }
        rows.append(row_dict)

    return QueryTransactionsResult(
        row_count=len(rows),
        truncated=len(rows) >= MAX_ROWS,
        executed_sql=safe_sql,
        columns=columns,
        rows=rows,
        successful_query=sql,
    )
