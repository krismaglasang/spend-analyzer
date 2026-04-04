import asyncio

from agents import Runner

from app_agents.statement_extraction_agent import statement_extraction_agent
from utils.pdf_reader import extract_text


async def main(input: list[str]):
    result = await Runner.run(
        starting_agent=statement_extraction_agent,
        input=f"Extract the accounts and transactions from this BNZ statement - {input} and store them in the database.",
    )
    print(result)
    return result


if __name__ == "__main__":
    asyncio.run(main(extract_text()))
