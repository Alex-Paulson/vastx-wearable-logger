import asyncio
from bleak import BleakScanner

async def main():
  print("Scanning for Bluetooth Low Energy devices...")

  devices = await BleakScanner.discover(timeout = 10)

  if len(devices) == 0:
    print("No BLE devices found.")
  else:
    print("Devices found: ")
    for device in devices:
      print("Name: ", device.name)
      print("Address: ", device.address)
      print()

asyncio.run(main())