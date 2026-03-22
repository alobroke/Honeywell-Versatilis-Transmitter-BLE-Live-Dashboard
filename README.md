# Honeywell Versatilis Transmitter — BLE Live Dashboard

A Python-based real-time monitoring dashboard that communicates directly with the
Honeywell Versatilis Transmitter (HVT100) over Bluetooth Low Energy (BLE),
implementing all five commands defined in the official BLE Communication Protocol
specification (v1.0, 28-Jan-2026).

---

## Project Overview

The Honeywell Versatilis Transmitter is an industrial IoT sensor used to monitor
rotating equipment such as motors, pumps, fans, blowers, compressors, and gearboxes.
It measures vibration, surface temperature, ambient temperature, humidity, pressure,
and acoustics, and transmits this data over BLE 5.0.

This project connects to the sensor directly from a Windows PC via a TP-Link BT 5.4
USB adapter, decodes the proprietary binary BLE payload per the official protocol
specification, and displays all sensor values on a live web dashboard.

---

## Hardware Requirements

| Item | Details |
|---|---|
| Sensor | Honeywell Versatilis HVT100A03 (MAC: 00:40:84:65:20:2B) |
| BLE Adapter | TP-Link Bluetooth 5.4 USB Adapter (UB500 or UB5A) |
| OS | Windows 10/11 |
| Python | 3.9 or higher |

---

## Files in This Project

### `dashboard.py` — Main file (910 lines)

This is the single complete file that does everything. It contains the BLE
communication layer, all five protocol command implementations, binary payload
decoders, and the Plotly Dash web dashboard. Run this file to start the system.

**Structure inside `dashboard.py`:**

```
Configuration
  ADDRESS        — BLE MAC address of the sensor
  CHAR_UUID      — Honeywell custom GATT characteristic UUID
  MAX_PTS        — Number of data points to keep in trend charts (60)

Live data store (live{})
  Shared dictionary holding all current sensor values.
  Written by BLE thread, read by Dash callback.
  Protected by threading.Lock() for thread safety.

BLE control flags (_ble_control{})
  connect_requested     — set True to initiate BLE connection
  disconnect_requested  — set True to trigger 0x16 abort + disconnect
  running               — True while BLE session is active

Notification handler (_on_notify)
  Collects all incoming BLE notification packets into _packets list.
  Also detects abort responses (0x16 accepted, 0xDEADFEED rejected).

Command 2.3.4 — cmd_heartbeat()
  Sends 0x15 to keep BLE connection alive.
  Must be sent at least every 60 seconds or sensor auto-disconnects.
  Sent after every command and midway through long waits.

Command 2.3.5 — cmd_abort() / cmd_abort_and_disconnect()
  Sends 0x16 abort to stop any ongoing sensor command.
  Waits up to 2 seconds for sensor acknowledgement.
  Sensor replies 0x16 (accepted) or 0xDEADFEED (rejected).
  Called on command timeout, on disconnect button press,
  and automatically before reconnecting after any BLE error.

Packet collector (_collect)
  Waits for all notification packets from sensor.
  Checks disconnect_requested every second for responsive disconnect.
  Sends heartbeat midway through waits longer than 12 seconds.
  Returns assembled buffer (skipping ACK first packet and DONE last packet).

Shared field decoder (_read_fields)
  Single decoder used by BOTH live and history decoders.
  Reads all sensor fields from a given byte offset.
  Guaranteed identical byte interpretation for both commands.

  Verified byte offsets (from real sensor capture):
    +0   Ambient temp    signed byte °C
    +1   Humidity        unsigned byte %RH
    +2   Pressure raw    hPa = (raw × 3) + 335  [confirmed vs Honeywell app]
    +3   Surface temp    signed byte °C
    +4   RPM             uint16 little-endian
    +6   Vibration X     23 bytes
         vel(4f) acc(4f) freq(4f) disp(4f) kurt(1) crest(1) skew(1) spare(4)
    +29  Vibration Y     23 bytes (same structure)
    +52  Vibration Z     23 bytes (same structure)
    +75  Audio dBSPL     1 byte
    +76  Audio frequency float Hz
    +80  Audio spare     2 bytes
    +82  Battery %       1 byte

  Note: kurtosis, crest factor, and skewness are stored as integers
  scaled ×10 in the byte. Divide by 10.0 to get real value.
  Confirmed: raw byte 28 = 2.8 kurtosis (verified vs Honeywell app).

Command 2.3.1 — _decode_live() / run_live()
  Sends 0x01 0x00 to request live sensor reading.
  Sensor takes ~12 seconds to measure and respond.
  Waits 13 seconds to collect all 54 packets (~25,796 bytes).
  Header before _read_fields: version(1) + spares(8) + timestamp(4) = 13 bytes.
  Updates all live{} values and refreshes dashboard.

Command 2.3.2 — _decode_history() / run_history()
  Sends 0x02 0x01 + record_count(4 bytes) to fetch stored history.
  Sensor stores readings internally even when nothing is connected.
  Fetches latest 5 records, runs every 5 live data cycles (~75 seconds).
  Each history record is exactly 186 bytes:
    13 header + 6 env fields + 69 vibration + 7 audio + 1 battery + 90 alarm = 186
  Decoder forces exact 186-byte alignment after every record.
  Validates temperature range (-40 to +80°C) and skips invalid records.

Command 2.3.3 — _decode_raw() / run_raw()
  Sends 0x1B to request raw accelerometer waveform per axis.
  Command: CMD(1) + data_length(4, default 0x04) + axis(4 Int32) + spare(3)
  Axis 0 = X (every 10 cycles), 1 = Y (every 15), 2 = Z (every 20).
  Response is multiple frames, each frame:
    CMD(1) + CRC16(2) + frame_no(1) + frame_len(2) + sensitivity(4) + spare(4) + samples
  Sample formula: result_g = (raw_int16 × sensitivity) / 1000
  Max 16,500 samples per axis at 7.6 kHz ODR (~2.24 seconds of data).
  Downsampled to 2,000 points for dashboard display performance.

BLE loop (ble_loop)
  Main async loop running in a background thread.
  Waits for connect_requested flag before connecting.
  Checks disconnect_requested at every step for responsive disconnect.
  Auto-reconnects on any BLE error after 5 second delay.
  Cycle schedule:
    Every cycle      → 2.3.1 Live data + 2.3.4 Heartbeat
    Every 5 cycles   → 2.3.2 History (last 5 records)
    Every 10 cycles  → 2.3.3 Raw vibration X axis
    Every 15 cycles  → 2.3.3 Raw vibration Y axis
    Every 20 cycles  → 2.3.3 Raw vibration Z axis

Dash web dashboard
  Runs on http://localhost:8050
  Refreshes every 3 seconds.
  Components:
    Status bar        — BLE connection status, last update time, last command
    Connect button    — initiates BLE connection
    Disconnect button — sends 0x16 abort then cleanly disconnects
    7 sensor cards    — ambient temp, surface temp, humidity, pressure,
                        battery, RPM, acoustics (latest values)
    Vib velocity chart — 60-point rolling trend X/Y/Z in mm/s
    Vib accel chart    — 60-point rolling trend X/Y/Z in g
    Temperature chart  — ambient vs surface trend
    Acoustics chart    — dBSPL trend
    Health table       — kurtosis, crest factor, skewness, dominant frequency
                         per axis (from latest 2.3.1 reading)
    History table      — last 5 stored sensor records with all fields
    Raw waveform chart — X/Y/Z combined accelerometer waveform in g
```

---

### `scan.py` — BLE scanner (development tool)

Scans for nearby BLE devices and prints their MAC address and name.
Used to discover and confirm the sensor MAC address during initial setup.

```python
# Usage
python scan.py
# Output example:
# 00:40:84:65:20:2B  |  HVT100A03202B
```

### `explore.py` — GATT service explorer (development tool)

Connects to the sensor and lists all GATT services and characteristics
with their UUIDs and properties. Used to discover the custom service UUID
and characteristic UUID required for communication.

```python
# Usage
python explore.py
# Output example:
# SERVICE: e093f3b5-00a3-a9e5-9eca-40016e0edc24
#    CHAR: e093f3b5-00a3-a9e5-9eca-40026e0edc24  |  ['write', 'notify', 'write-without-response']
```

### `listen.py` — Raw packet listener (development tool)

Connects to the sensor, enables notifications, sends the live data command,
and prints raw hex bytes of every incoming packet. Used to capture real sensor
data for byte-level analysis and decoder development.

### `final.py` — First working decoder (development tool)

The first version that successfully decoded a full live data response.
Used to confirm byte offsets by comparing output against the Honeywell
Versatilis Connect mobile app readings side by side.

### `pair.py` — BLE pairing tool (development tool)

Attempts to pair with the sensor using the default passkey 110420.
Windows pairing is handled via Settings → Bluetooth → Add device.
This file was used during initial pairing troubleshooting.

---

## Reference Documents

| Document | Purpose |
|---|---|
| `HVT_Bluetooth_LE_Communication_Protocol.pdf` | Official BLE protocol spec — all command formats, byte layouts, response structures |
| `hon-ia-honeywell-versatilis-transmitter-technical-specifications-r110-2.pdf` | Hardware spec — sensor ranges, accuracy, certifications, mounting options |

---

## Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install bleak dash plotly
```

---

## Running the Dashboard

```bash
python dashboard.py
```

Open browser at `http://localhost:8050`

The dashboard auto-connects to the sensor on startup. The first live reading
appears after ~15 seconds. History data appears after ~75 seconds (5 cycles).
Raw vibration waveform appears after ~150 seconds (10 cycles).

Press `Ctrl+C` to stop.

---

## BLE Protocol Summary

| Command | Code | Sent | Purpose |
|---|---|---|---|
| Read Live Data | 0x01 | Every cycle | All sensor values, FFT data |
| Read History | 0x02 | Every 5 cycles | Last 5 stored records |
| Read Raw Vibration | 0x1B | Every 10/15/20 cycles | Raw waveform per axis |
| Heartbeat | 0x15 | After every command | Keep BLE alive (60s timeout) |
| Abort | 0x16 | On timeout / disconnect | Stop current command cleanly |

---

## Sensor GATT Profile

| Item | Value |
|---|---|
| Service UUID | `e093f3b5-00a3-a9e5-9eca-40016e0edc24` |
| Characteristic UUID | `e093f3b5-00a3-a9e5-9eca-40026e0edc24` |
| Properties | write, notify, write-without-response |
| Pairing passkey | 110420 |
| BLE version | 5.0 |
| BLE range | 25 metres line of sight |

---

## Confirmed Calibration Values

These were verified by running the dashboard and the official Honeywell Versatilis
Connect mobile app simultaneously on the same sensor:

| Parameter | Formula | Example |
|---|---|---|
| Pressure | `(raw_byte × 3) + 335` | raw=204 → 947 hPa |
| Kurtosis | `raw_byte / 10.0` | raw=28 → 2.8 |
| Crest factor | `raw_byte / 10.0` | raw=36 → 3.6 |
| Skewness | `raw_byte / 10.0` | raw=0 → 0.0 |
| Raw vibration | `(int16 × sensitivity) / 1000` | per spec 2.3.3 |

---

## Health Indicator Reference

| Kurtosis Value | Meaning |
|---|---|
| < 4 | Normal bearing — healthy |
| 4 – 6 | Monitor — early signs |
| 6 – 10 | Warning — bearing wear |
| > 10 | Critical — inspect immediately |

| Crest Factor | Meaning |
|---|---|
| < 4 | Normal |
| 4 – 6 | Monitor |
| > 6 | Impacts or shocks present |

---

## Architecture

```
Sensor (HVT100)
    ↓  BLE 5.0 notifications
TP-Link USB Adapter
    ↓
Python bleak library
    ↓
_on_notify() — packet collector
    ↓
_collect()   — assembles packets into buffer
    ↓
_read_fields() — shared binary decoder
    ↓
_decode_live() / _decode_history() / _decode_raw()
    ↓
live{} dictionary  ←→  threading.Lock()
    ↓
Dash callback (every 3s)
    ↓
http://localhost:8050
```

---

## Author Notes

- The Intel built-in Bluetooth was left in Error state throughout development.
  The TP-Link USB adapter was used exclusively and worked without issues.
- The sensor auto-disconnects after 60 seconds without any command.
  The heartbeat (0x15) is sent after every command cycle to prevent this.
- The pressure formula offset of +335 (instead of spec's +300) was determined
  empirically by comparing against the Honeywell app reading of 947 hPa.
- History values showing wrong temperatures in earlier versions were caused by
  record misalignment. Fixed by using a single shared _read_fields() decoder
  and forcing exact 186-byte alignment after every history record.