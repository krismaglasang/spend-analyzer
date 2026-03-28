from agents import Agent
from dotenv import load_dotenv
from tools.load_to_db import load_to_db

load_dotenv()

etl_agent: Agent = Agent(
    name="ETL agent",
    instructions="""
                  You are an ETL agent whose task is to take a file, 
                  extract the important fields and values from it, 
                  then load them to a database.
                  
                  You have access to a tool to load records to an external database.
                  """,
    tools=[load_to_db]
)
