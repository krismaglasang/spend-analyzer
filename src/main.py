import asyncio

from agents import Runner

from app_agents.finance_agent import finance_agent
from utils.pdf_reader import extract_text


async def main(input: list[str]):
    result = await Runner.run(
        starting_agent=finance_agent,
        # input=f"Extract the accounts and transactions from this BNZ statement - {input} and store them in the database.",
        input="""
        How much went out of my AMEX account and into AMERICAN EXPRESS?
        """,
    )
    print(result)
    return result


if __name__ == "__main__":
    asyncio.run(main(extract_text()))
