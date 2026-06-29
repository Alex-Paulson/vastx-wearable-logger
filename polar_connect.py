import asyncio
from bleak import BleakScanner

async def main():
  print("Searching for Polar H10...")

  devices = await BleakScanner.discover(timeout=10)

  polar_found = False

  for device in devices:
    print("Name:", device.name)
    print("Address:", device.address)
    print()

    if device.name is not None and "Polar" in device.name:
      polar_found = True
      print("Polar H10 found.")
      print("Connection code will be added once the device is available.")

  if polar_found == False:
    print("Polar H10 not detected.")

asyncio.run(main())