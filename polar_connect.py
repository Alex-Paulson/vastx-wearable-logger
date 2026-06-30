import asyncio
import csv
from datetime import datetime
from bleak import BleakScanner, BleakClient

HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
CSV_FILE = "heart_rate_data.csv"

def create_csv():
  with open(CSV_FILE, "w", newline = "") as file:
    writer = csv.writer(file)
    writer.writerow(["timestamp", "heart_rate_bpm"])

def save_heart_rate(heart_rate):
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  with open(CSV_FILE, "a", newline = "") as file:
    writer = csv.writer(file)
    writer.writerow([timestamp, heart_rate])

def handle_heart_rate(sender, data):
  flags = data[0]

  if flags & 0x01:
    heart_rate = int.from_bytes(data[1:3], byteorder = "little")
  else:
    heart_rate = data[1]

  print("Heart rate: ", heart_rate, "bpm")
  save_heart_rate(heart_rate)

async def main():
  create_csv()

  print("Scanning for BLE devices...")

  devices = await BleakScanner.discover(timeout = 10)

  polar_device = None

  for device in devices:
    print("Found: ", device.name, device.address)

    if device.name is not None and "Polar" in device.name:
      polar_device = device

  if polar_device is None:
    print("Polar H10 is not found.")
    return
  
  print("Connecting to: ", polar_device.name, polar_device.address)

  async with BleakClient(polar_device.address) as client:
    print("Connected: ", client.is_connected)

    print("Subscribing to heart rate data...")
    await client.start_notify(HEART_RATE_MEASUREMENT_UUID, handle_heart_rate)

    print("Recording heart rate data to: ", CSV_FILE)
    print("Press Ctrl + C to stop.")

    while True:
      await asyncio.sleep(1)

asyncio.run(main())