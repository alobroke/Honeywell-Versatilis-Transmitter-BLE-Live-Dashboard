import asyncio
import struct

from bleak import BleakClient

ADDRESS = "00:40:84:65:20:2B"
CHAR_UUID = "e093f3b5-00a3-a9e5-9eca-40026e0edc24"

response_buffer = bytearray()
packet_count = 0

def notification_handler(sender, data: bytearray):
    global packet_count, response_buffer
    packet_count += 1
    print(f"Packet {packet_count}: {data.hex()}")
    if packet_count > 1:
        response_buffer += data

async def main():
    print("Connecting...")
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        await client.start_notify(CHAR_UUID, notification_handler)
        print("Notifications enabled. Sending live data command...")

        await client.write_gatt_char(CHAR_UUID, bytearray([0x01, 0x00]), response=False)
        print("Waiting 15 seconds for response...")

        await asyncio.sleep(15)
        await client.stop_notify(CHAR_UUID)

asyncio.run(main())