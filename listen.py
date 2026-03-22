import asyncio
from bleak import BleakClient

ADDRESS = "00:40:84:65:20:2B"
CHAR_UUID = "e093f3b5-00a3-a9e5-9eca-40026e0edc24"

def handler(sender, data: bytearray):
    print(f"Raw bytes ({len(data)}): {data.hex()}")
    print(f"As integers: {list(data)}")
    print()

async def listen():
    async with BleakClient(ADDRESS) as client:
        print("Connected. Listening for data...\n")
        await client.start_notify(CHAR_UUID, handler)
        await asyncio.sleep(30)  # listen for 30 seconds
        await client.stop_notify(CHAR_UUID)

asyncio.run(listen())