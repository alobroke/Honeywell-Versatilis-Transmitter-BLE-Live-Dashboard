import asyncio
import struct
from bleak import BleakClient

ADDRESS = "00:40:84:65:20:2B"
CHAR_UUID = "e093f3b5-00a3-a9e5-9eca-40026e0edc24"

packets = []

def notification_handler(sender, data: bytearray):
    packets.append(bytes(data))
    print(f"Packet {len(packets)}: {len(data)} bytes")

def decode(buf: bytearray):
    o = 0
    try:
        record_ver        = buf[o]; o += 1
        o += 8  # spares
        timestamp         = struct.unpack_from('<I', buf, o)[0]; o += 4
        amb_temp          = struct.unpack_from('<b', buf, o)[0]; o += 1
        humidity          = buf[o]; o += 1
        pressure          = (buf[o] * 3) + 300; o += 1
        surf_temp         = struct.unpack_from('<b', buf, o)[0]; o += 1
        rpm               = struct.unpack_from('<H', buf, o)[0]; o += 2

        print(f"\n{'='*40}")
        print(f"Timestamp    : {timestamp}")
        print(f"Ambient temp : {amb_temp} °C")
        print(f"Surface temp : {surf_temp} °C")
        print(f"Humidity     : {humidity} %RH")
        print(f"Pressure     : {pressure} hPa")
        print(f"RPM          : {rpm}")

        for axis in ['X', 'Y', 'Z']:
            vel   = struct.unpack_from('<f', buf, o)[0]; o += 4
            acc   = struct.unpack_from('<f', buf, o)[0]; o += 4
            freq  = struct.unpack_from('<f', buf, o)[0]; o += 4
            o += 4  # displacement (N/A)
            kurt  = buf[o]; o += 1
            crest = buf[o]; o += 1
            skew  = buf[o]; o += 1
            o += 4  # spare
            print(f"Vib {axis}       : vel={vel:.4f} cm/s  acc={acc:.5f} g  freq={freq:.1f} Hz  kurt={kurt}  crest={crest}  skew={skew}")

        audio_db   = buf[o]; o += 1
        audio_freq = struct.unpack_from('<f', buf, o)[0]; o += 4
        o += 2
        print(f"Acoustics    : {audio_db} dBSPL @ {audio_freq:.1f} Hz")

        battery = buf[o]; o += 1
        print(f"Battery      : {battery} %")
        print(f"{'='*40}\n")

    except Exception as e:
        print(f"Decode error at offset {o}: {e}")

async def main():
    print("Connecting...")
    async with BleakClient(ADDRESS) as client:
        print("Connected. Enabling notifications...")
        await client.start_notify(CHAR_UUID, notification_handler)

        print("Sending live data command 0x01...")
        await client.write_gatt_char(CHAR_UUID, bytearray([0x01, 0x00]), response=False)

        # Wait 15 seconds + send heartbeat at 10s
        for i in range(15):
            await asyncio.sleep(1)
            if i == 10:
                await client.write_gatt_char(CHAR_UUID, bytearray([0x15]), response=False)
                print("Heartbeat sent")

        await client.stop_notify(CHAR_UUID)

    # Decode: skip first and last packet, combine middle ones
    if len(packets) > 2:
        buf = bytearray()
        for p in packets[1:-1]:
            buf += p
        print(f"\nTotal data buffer: {len(buf)} bytes")
        decode(buf)
    else:
        print("Not enough packets received")

asyncio.run(main())