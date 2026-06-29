# Polar Connect Plan

## Aim
Plan the future Python script that will connect to the Polar H10 heart rate sensor.

## Planned Steps
1. Scan for nearby Bluetooth Low Energy (BLE) devices.
2. Print detected device names and addresses.
3. Find the Polar H10.
4. Connect to the Polar H10.
5. Find the Heart Rate Service.
6. Subscribe to heart-rate data.
7. Print live values.
8. Later save values to CSV.

## Current Status
BLE scanning works using `blue_scan.py`.

## Questions
- What name will the Polar H10 appear as?
- Does it need to be paired first?
- Which characteristic gives heart-rate notifications?
- How should RR intervals be saved?