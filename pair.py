import asyncio
from bleak import BleakClient

ADDRESS = "00:40:84:65:20:2B"

async def pair():
    async with BleakClient(ADDRESS, timeout=15.0) as client:
        print(f"Connected: {client.is_connected}")
        
        # Read device name
        name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
        print(f"Device name: {name.decode('utf-8')}")
        
        # Request pairing/bonding
        print("\nAttempting to pair...")
        await client.pair()
        print("Pairing result: success")

asyncio.run(pair())