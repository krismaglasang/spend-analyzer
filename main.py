import asyncio
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv

load_dotenv()

@function_tool
def fun_fact():
    return "Selenium WebDriver is not a testing tool, but rather a web browser automation tool."

agent = Agent(
    name="Katara", 
    instructions="You are my personal AI assistant",
    tools=[fun_fact])

async def main():
    result = await Runner.run(starting_agent=agent, input="Do you know of any fun fact? Use any tool at disposal if one is available.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())