from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from src.models.expense_extract_file import ExpenseExtractFile
import asyncio

load_dotenv()

@function_tool
def get_expense_categories(expense_extract_file: ExpenseExtractFile):
    """ Takes the user's expenses and returns a logical category of where each expense belongs
        Example: category 1 = sports expenses
                 category 2 = rent
                 category 3 = car expenses

    Args:
        expense_extract_file (ExpenseExtractFile): The object containing the parsed expense file
    """

categorizer_agent = Agent(
    name="Categorizer agent",
    handoff_description="Specialist agent for categorizing expenses and determing outgoings per category",
    instructions="",
    tools=[get_expense_categories]
)

statistics_agent = Agent(
    name="Statistics agent",
    handoff_description="Specialist agent for calculating sums, averages, medians, etc of income and expenses",
    instructions=""
)

spending_habits_agent = Agent(
    name="Spending habits agent",
    handoff_description="Specialist agent that identifies patterns, habits in spending, and determines savings opportunities or extra cash for investment opportunities",
    instructions=""
)

database_agent = Agent(
    name="Database agent",
    handoff_description="Specialist agent for querying the spend-analyzer database",
    instructions=""
)

orchestrator_agent = Agent(
    name="Orchestrator agent",
    instructions="",
    handoffs=[statistics_agent, categorizer_agent, database_agent, spending_habits_agent]
)
    

async def main():
    result = await Runner.run(starting_agent=orchestrator_agent, input="What can you do?")
    result.

if __name__ == "__main__":
    asyncio.run(main())


