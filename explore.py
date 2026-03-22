import asyncio
from bleak import BleakClient

ADDRESS = "00:40:84:65:20:2B"

async def explore():
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}\n")
        for service in client.services:
            print(f"SERVICE: {service.uuid}")
            for char in service.characteristics:
                print(f"   CHAR: {char.uuid}  |  {char.properties}")
            print()

asyncio.run(explore())