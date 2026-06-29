# Bluetooth Testing Notes

## Date
26 June 2026

## Project
vastx-wearable-logger

## Objective
The objective of this test was to verify that Python could successfully scan for nearby Bluetooth Low Energy (BLE) devices using the Bleak library.

## Test Environment

Laptop:
Microsoft Surface Pro 11

Operating System:
Windows 11

Python Library:
- bleak
- pandas

## Test Performed

A Python script (`ble_scan.py`) was created using the Bleak library. The script scanned for nearby BLE devices and displayed any detected device names and addresses.

## Results

Bluetooth enabled:
Yes

BLE scan enabled:
Yes

Devices detected:
Name:  S3b53a58d3a7a34c0C
Address:  94:50:44:30:12:38

Name:  None
Address:  BC:7E:8B:1F:5D:07

Name:  None
Address:  78:BD:BC:67:BC:7B

Name:  None
Address:  41:E5:53:42:F4:16

Name:  None
Address:  0E:D3:27:B0:DB:72

Name:  LARQ_0epxfNNs4od
Address:  62:8B:34:FE:54:9E

Name:  None
Address:  51:D2:91:48:BF:5A

Name:  None
Address:  65:4E:BB:B7:26:E9

Errors encountered:
Initially the script could not be found because the terminal was in the wrong directory (`C:\Users\alexp`). After changing to the project folder (`C:\Users\alexp\vastx-wearable-logger`), the script executed successfully.

## Next Steps

The next stage will be to:
- Identify the Polar H10 when it becomes available.
- Connect to the device.
- Access to the Heart Rate Service.
- Receive live heart rate and RR interval data.
- Save the received data to a CSV file for later use by the VASTX model.