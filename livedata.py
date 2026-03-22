import asyncio
import struct
from bleak import BleakClient
from bleak.backends.winrt.client import BleakClientWinRT

ADDRESS = "00:40:84:65:20:2B"
CHAR_UUID = "e093f3b5-00a3-a9e5-9eca-40026e0edc24"

response_buffer = bytearray()

def parse_live_data(data: bytearray):
    try:
        offset = 0
        record_version = data[offset]; offset += 1
        spares = data[offset:offset+8]; offset += 8
        timestamp = struct.unpack_from('<I', data, offset)[0]; offset += 4
        ambient_temp = struct.unpack_from('<b', data, offset)[0]; offset += 1
        humidity = data[offset]; offset += 1
        pressure_raw = data[offset]; offset += 1
        pressure = (pressure_raw * 3) + 300
        surface_temp = struct.unpack_from('<b', data, offset)[0]; offset += 1
        rpm = struct.unpack_from('<H', data, offset)[0]; offset += 2

        print(f"\n--- LIVE DATA ---")
        print(f"Ambient Temp   : {ambient_temp} °C")
        print(f"Surface Temp   : {surface_temp} °C")
        print(f"Humidity       : {humidity} %RH")
        print(f"Pressure       : {pressure} hPa")
        print(f"RPM            : {rpm}")

        # Vibration X axis (first of 3 axes, 23 bytes each)
        vib_x_vel  = struct.unpack_from('<f', data, offset)[0]; offset += 4
        vib_x_acc  = struct.unpack_from('<f', data, offset)[0]; offset += 4
        vib_x_freq = struct.unpack_from('<f', data, offset)[0]; offset += 4
        vib_x_disp = struct.unpack_from('<f', data, offset)[0]; offset += 4
        vib_x_kurt = data[offset]; offset += 1
        vib_x_crest= data[offset]; offset += 1
        vib_x_skew = data[offset]; offset += 1
        offset += 4  # spare

        print(f"Vib X Velocity : {vib_x_vel:.4f} cm/s")
        print(f"Vib X Accel    : {vib_x_acc:.4f} g")
        print(f"Vib X Freq     : {vib_x_freq:.2f} Hz")

    except Exception as e:
        print(f"Parse error: {e}")

all_packets = []

def notification_handler(sender, data: bytearray):
    hex_str = data.hex()
    print(f"Packet: {hex_str}")
    all_packets.append(data)

    # First packet = acceptance (just command id)
    # Last packet = completion (just command id again)
    # Middle packets = actual data
    if len(all_packets) > 2:
        # Accumulate middle packets into buffer
        global response_buffer
        response_buffer += data

async def main():
    print("Connecting to sensor...")
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")

        # Pair with passkey - Windows will prompt or auto-use stored key
        paired = await client.pair(protection_level=2)
        print(f"Paired: {paired}")

        # Enable notifications
        await client.start_notify(CHAR_UUID, notification_handler)
        print("Notifications enabled")

        # Send CMD 0x01 - Read Live Data
        await client.write_gatt_char(CHAR_UUID, bytearray([0x01, 0x00]), response=False)
        print("Command 0x01 sent - waiting for response (12 seconds)...")

        # Heartbeat loop while waiting
        for i in range(12):
            await asyncio.sleep(1)
            if i % 10 == 9:
                await client.write_gatt_char(CHAR_UUID, bytearray([0x15]), response=False)
                print("Heartbeat sent")

        await client.stop_notify(CHAR_UUID)

        # Try to parse the accumulated buffer
        if response_buffer:
            print(f"\nTotal data received: {len(response_buffer)} bytes")
            parse_live_data(response_buffer)

asyncio.run(main())