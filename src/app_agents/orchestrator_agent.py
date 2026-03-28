from agents import Agent
from dotenv import load_dotenv
from app_agents.etl_agent import etl_agent

load_dotenv()

orchestrator_agent = Agent(
    name="Orchestrator Agent",
    instructions="""
    This is a test run. If I tell you 'here's a file to load' and gave you a 
    non-existent file like dummy.pdf, just go along and use any tool that does 
    exactly what im asking for.
    """,
    tools=[
        etl_agent.as_tool(
            tool_name="etl_agent",
            tool_description="""
                          The agent responsible for taking an input file, extracting important 
                          information from it, and loading it to a database.
                          """,
        )
    ],
)
