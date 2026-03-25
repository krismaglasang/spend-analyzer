import asyncio


async def toast_bread():
    print("toasting bread 🍞")
    await asyncio.sleep(5)
    print("crispy toast ready 🔔")
    
async def pour_coffee():
     print("Hot coffee ☕️")

async def main():
    await asyncio.gather(toast_bread(), pour_coffee())

if __name__ == "__main__":
    asyncio.run(main())