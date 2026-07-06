import asyncio
import csv
import threading
import time
from datetime import datetime
from queue import Queue

import pandas as pd
import streamlit as st
from bleak import BleakScanner, BleakClient

HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

if "devices" not in st.session_state:
  st.session_state.devices = []

if "status" not in st.session_state:
  st.session_state.status = "Ready."

if "connected" not in st.session_state:
  st.session_state.connected = False

if "recording" not in st.session_state:
  st.session_state.recording = False

if "heart_rate" not in st.session_state:
  st.session_state.heart_rate = "--"

if "data" not in st.session_state:
  st.session_state.data = []

if "queue" not in st.session_state:
  st.session_state.queue = Queue()

if "device_name" not in st.session_state:
  st.session_state.device_name = ""

if "device_address" not in st.session_state:
  st.session_state.device_address = ""

if "connection_thread_started" not in st.session_state:
  st.session_state.connection_thread_started = False

def scan_devices():
  async def scan():
    return await BleakScanner.discover(timeout = 10)

  devices = asyncio.run(scan())
  results = []

  for device in devices:
    name = device.name if device.name else "Unknown"
    results.append({
      "name": name,
      "address": device.address,
      "label": name + " - " + device.address
    })

  return results

def parse_heart_rate(data):
  flags = data[0]

  if flags & 0x01:
    heart_rate = int.from_bytes(data[1:3], byteorder = "little")
  else:
    heart_rate = data[1]

  return heart_rate

def ble_worker(device_address, output_queue):
  async def connect():
    try:
      async with BleakClient(device_address) as client:
        if client.is_connected:
          output_queue.put({
            "type": "status",
            "message": "Connected."
          })
        else:
          output_queue.put({
            "type": "status",
            "message": "Connection failed."
          })
          return

        def handle_heart_rate(sender, data):
          heart_rate = parse_heart_rate(data)

          output_queue.put({
            "type": "heart_rate",
            "heart_rate": heart_rate
          })

        await client.start_notify(
          HEART_RATE_MEASUREMENT_UUID,
          handle_heart_rate
        )

        while True:
          await asyncio.sleep(1)

    except Exception as error:
      output_queue.put({
        "type": "status",
        "message": "Error: device disconnected. Please reconnect. " + str(error)
      })

  asyncio.run(connect())

def start_connection(device_address):
  thread = threading.Thread(
    target = ble_worker,
    args = (device_address, st.session_state.queue),
    daemon = True
  )

  thread.start()

def save_to_csv(participant_id, session_id, notes):
  if len(st.session_state.data) == 0:
    st.session_state.status = "No data to save."
    return None

  file_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  filename = "VASTX_" + participant_id + "_" + session_id + "_" + file_time + ".csv"

  with open(filename, "w", newline = "") as file:
    fieldnames = [
      "timestamp",
      "participant_id",
      "session_id",
      "device_name",
      "device_address",
      "heart_rate_bpm",
      "rr_intervals_ms",
      "event_marker",
      "notes"
    ]

    writer = csv.DictWriter(file, fieldnames = fieldnames)
    writer.writeheader()

    for row in st.session_state.data:
      writer.writerow(row)

  st.session_state.status = "Data saved successfully."
  return filename

def process_queue(participant_id, session_id, notes):
  while not st.session_state.queue.empty():
    message = st.session_state.queue.get()

    if message["type"] == "status":
      st.session_state.status = message["message"]

      if message["message"] == "Connected.":
        st.session_state.connected = True

      if "disconnected" in message["message"]:
        st.session_state.connected = False
        st.session_state.recording = False
        st.session_state.connection_thread_started = False

    if message["type"] == "heart_rate":
      heart_rate = message["heart_rate"]
      st.session_state.heart_rate = heart_rate

      if st.session_state.recording:
        st.session_state.data.append({
          "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          "participant_id": participant_id,
          "session_id": session_id,
          "device_name": st.session_state.device_name,
          "device_address": st.session_state.device_address,
          "heart_rate_bpm": heart_rate,
          "rr_intervals_ms": "",
          "event_marker": "",
          "notes": notes
        })

st.set_page_config(
  page_title = "VASTX Wearable Logger",
  layout = "wide"
)

st.title("VASTX Wearable Logger")
st.write("Polar H10 live physiological data logger")

st.info("Status: " + st.session_state.status)

st.header("Participant details")

participant_id = st.text_input("Participant ID", value = "P001")
session_id = st.text_input("Session ID", value = "S001")
notes = st.text_area("Notes", value = "")

process_queue(participant_id, session_id, notes)

st.header("Device connection")

if st.button("Scan for devices"):
  st.session_state.status = "Scanning for devices."

  try:
    st.session_state.devices = scan_devices()

    if len(st.session_state.devices) == 0:
      st.session_state.status = "No devices found."
    else:
      st.session_state.status = "Devices found."

  except Exception as error:
    st.session_state.status = "Connection failed. " + str(error)

device_labels = []

for device in st.session_state.devices:
  device_labels.append(device["label"])

selected_device = st.selectbox(
  "Detected devices",
  options = device_labels
)

if st.button("Connect"):
  if selected_device == "":
    st.session_state.status = "Please select a device first."
  else:
    selected = None

    for device in st.session_state.devices:
      if device["label"] == selected_device:
        selected = device

    if selected is not None:
      st.session_state.device_name = selected["name"]
      st.session_state.device_address = selected["address"]
      st.session_state.status = "Connecting to Polar H10."
      st.session_state.connection_thread_started = True
      start_connection(selected["address"])
    else:
      st.session_state.status = "Please select a device first."

st.header("Live data")

process_queue(participant_id, session_id, notes)

st.metric(
  label = "Heart rate: ",
  value = str(st.session_state.heart_rate) + " bpm"
)

if st.session_state.connected:
  st.success("Connection status: " + st.session_state.status)
else:
  st.warning("Connection status: " + st.session_state.status)

st.header("Recording")

col1, col2, col3 = st.columns(3)

with col1:
  if st.button("Start recording"):
    if not st.session_state.connected:
      st.session_state.status = "Please connect to a device before recording."
    else:
      st.session_state.recording = True
      st.session_state.status = "Recording started."

with col2:
  if st.button("Stop recording"):
    if st.session_state.recording:
      st.session_state.recording = False
      st.session_state.status = "Recording stopped."
    else:
      st.session_state.status = "Recording is not currently active."

with col3:
  if st.button("Save CSV"):
    save_to_csv(participant_id, session_id, notes)

st.write("Recording active: ", st.session_state.recording)

st.header("Data preview")

if len(st.session_state.data) > 0:
  df = pd.DataFrame(st.session_state.data)
  st.dataframe(df.tail(10))
else:
  st.write("No data recorded yet.")

time.sleep(1)
st.rerun()
