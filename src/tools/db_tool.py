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

    Rules:
    - Only generate SELECT queries.
    - Only query approved analytics tables, not raw tables.
    - Prefer aggregations for "how much", "total", "average", and "count" questions.
    - Add date filters when the user asks about a period.
    - Select only the columns needed to answer the question.
    - Do not attempt INSERT, UPDATE, DELETE, DDL, schema inspection, or admin SQL.

    Approved tables:
    - accounts
    - transactions
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
