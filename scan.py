import asyncio
from bleak import BleakScanner

async def test():
    devices = await BleakScanner.discover(timeout=8.0)
    for d in devices:
        print(f"{d.address}  |  {d.name}")

asyncio.run(test())