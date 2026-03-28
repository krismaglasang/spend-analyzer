from app_agents.orchestrator_agent import orchestrator_agent
from agents import Runner
import asyncio

async def main():
    result = await Runner.run(
        starting_agent=orchestrator_agent,
        input="Here's a file containing accounts and transaction records. Extract information and store in db: dummy.pdf")
    print(result)
    return result

if __name__ == "__main__":
    asyncio.run(main())