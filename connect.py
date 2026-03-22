import asyncio
from bleak import BleakClient

ADDRESS = "00:40:84:65:20:2B"
CHAR_UUID = "e093f3b5-00a3-a9e5-9eca-40026e0edc24"

def notification_handler(sender, data):
    print("Received:", data)

async def run():
    async with BleakClient(ADDRESS) as client:
        print("Connected:", client.is_connected)

        # Enable notifications
        await client.start_notify(CHAR_UUID, notification_handler)

        print("Sending command: 01 00")

        # Send command (LIVE DATA)
        await client.write_gatt_char(CHAR_UUID, bytearray([0x01, 0x00]))

        # Wait for response
        await asyncio.sleep(12)

        await client.stop_notify(CHAR_UUID)

asyncio.run(run())