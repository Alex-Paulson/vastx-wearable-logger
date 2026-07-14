import asyncio
import csv
import threading
import time
from datetime import datetime
from queue import Queue

import pandas as pd
import streamlit as st
from bleak import BleakClient, BleakScanner

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
      "label": name + " - " + device.address,
      "device": device
    })

  return results

def parse_heart_rate(data):
  flags = data[0]

  if flags & 0x01:
    heart_rate = int.from_bytes(
      data[1:3],
      byteorder = "little"
    )
  else:
    heart_rate = data[1]

  return heart_rate

def calculate_percentage_threshold(
  baseline_heart_rate,
  percentage_threshold
):
  return baseline_heart_rate * (
    1 + percentage_threshold / 100
  )

def calculate_percent_above_baseline(
  heart_rate,
  baseline_heart_rate
):
  if baseline_heart_rate <= 0:
    return 0.0

  return (
    (heart_rate - baseline_heart_rate)
    / baseline_heart_rate
  ) * 100

def get_flag_details(
  heart_rate,
  manual_threshold,
  baseline_heart_rate,
  percentage_threshold
):
  if heart_rate == "--":
    return "Waiting for reading", "Waiting for live heart rate data"

  try:
    heart_rate_value = int(heart_rate)
    manual_threshold_value = int(manual_threshold)
    baseline_value = int(baseline_heart_rate)
    percentage_value = float(percentage_threshold)
  except (ValueError, TypeError):
    return "Invalid threshold", "Please enter a valid threshold value"

  calculated_threshold = calculate_percentage_threshold(
    baseline_value,
    percentage_value
  )

  manual_triggered = heart_rate_value > manual_threshold_value
  percentage_triggered = heart_rate_value > calculated_threshold
  percentage_text = str(percentage_value).rstrip("0").rstrip(".")

  if manual_triggered and percentage_triggered:
    return (
      "Elevated HR",
      "HR above manual threshold and more than "
      + percentage_text
      + "% above baseline"
    )

  if manual_triggered:
    return "Elevated HR", "HR above manual threshold"

  if percentage_triggered:
    return (
      "Elevated HR",
      "HR more than "
      + percentage_text
      + "% above baseline"
    )

  return "Normal", "Within threshold"

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
        "message": "Device disconnected. Please reconnect. " + str(error)
      })

  asyncio.run(connect())

def start_connection(device_address):
  thread = threading.Thread(
    target = ble_worker,
    args = (
      device_address,
      st.session_state.queue
    ),
    daemon = True
  )

  thread.start()

def save_to_csv(participant_id, session_id):
  if len(st.session_state.data) == 0:
    st.session_state.status = "No data available to save."
    return None

  file_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

  filename = (
    "VASTX_"
    + participant_id
    + "_"
    + session_id
    + "_"
    + file_time
    + ".csv"
  )

  fieldnames = [
    "timestamp",
    "participant_id",
    "session_id",
    "device_name",
    "device_address",
    "heart_rate_bpm",
    "threshold_bpm",
    "baseline_hr_bpm",
    "percent_above_baseline",
    "calculated_percentage_threshold_bpm",
    "flag_status",
    "flag_reason",
    "rr_intervals_ms",
    "event_marker",
    "notes"
  ]

  with open(
    filename,
    "w",
    newline = "",
    encoding = "utf-8"
  ) as file:
    writer = csv.DictWriter(
      file,
      fieldnames = fieldnames
    )

    writer.writeheader()
    writer.writerows(st.session_state.data)

  st.session_state.status = "Data saved successfully: " + filename
  return filename

def process_queue(
  participant_id,
  session_id,
  notes,
  baseline_heart_rate,
  manual_threshold,
  percentage_threshold
):
  while not st.session_state.queue.empty():
    message = st.session_state.queue.get()

    if message["type"] == "status":
      st.session_state.status = message["message"]

      if message["message"] == "Connected.":
        st.session_state.connected = True

      if "disconnected" in message["message"].lower():
        st.session_state.connected = False
        st.session_state.recording = False
        st.session_state.connection_thread_started = False

    if message["type"] == "heart_rate":
      heart_rate = message["heart_rate"]
      st.session_state.heart_rate = heart_rate

      flag_status, flag_reason = get_flag_details(
        heart_rate,
        manual_threshold,
        baseline_heart_rate,
        percentage_threshold
      )

      percent_above_baseline = calculate_percent_above_baseline(
        heart_rate,
        baseline_heart_rate
      )

      calculated_threshold = calculate_percentage_threshold(
        baseline_heart_rate,
        percentage_threshold
      )

      if st.session_state.recording:
        st.session_state.data.append({
          "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          "participant_id": participant_id,
          "session_id": session_id,
          "device_name": st.session_state.device_name,
          "device_address": st.session_state.device_address,
          "heart_rate_bpm": heart_rate,
          "threshold_bpm": manual_threshold,
          "baseline_hr_bpm": baseline_heart_rate,
          "percent_above_baseline": round(percent_above_baseline, 1),
          "calculated_percentage_threshold_bpm": round(calculated_threshold, 1),
          "flag_status": flag_status,
          "flag_reason": flag_reason,
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

participant_id = st.text_input(
  "Participant ID",
  value = "P001"
)

session_id = st.text_input(
  "Session ID",
  value = "S001"
)

notes = st.text_area(
  "Notes",
  value = ""
)

st.header("Threshold settings")

baseline_heart_rate = st.number_input(
  "Baseline HR, bpm",
  min_value = 30,
  max_value = 220,
  value = 75,
  step = 1
)

manual_threshold = st.number_input(
  "Alert threshold, bpm",
  min_value = 30,
  max_value = 220,
  value = 100,
  step = 1
)

percentage_threshold = st.number_input(
  "Percentage increase threshold",
  min_value = 0,
  max_value = 200,
  value = 20,
  step = 1
)

calculated_percentage_threshold = calculate_percentage_threshold(
  baseline_heart_rate,
  percentage_threshold
)

st.write(
  "Calculated percentage threshold: "
  + str(round(calculated_percentage_threshold, 1))
  + " bpm"
)

process_queue(
  participant_id,
  session_id,
  notes,
  baseline_heart_rate,
  manual_threshold,
  percentage_threshold
)

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

device_labels = [
  device["label"]
  for device in st.session_state.devices
]

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
        break

    if selected is not None:
      st.session_state.device_name = selected["name"]
      st.session_state.device_address = selected["address"]
      st.session_state.status = "Connecting to Polar H10."
      st.session_state.connection_thread_started = True

      start_connection(selected["address"])
    else:
      st.session_state.status = "Please select a device first."

st.header("Live data")

process_queue(
  participant_id,
  session_id,
  notes,
  baseline_heart_rate,
  manual_threshold,
  percentage_threshold
)

flag_status, flag_reason = get_flag_details(
  st.session_state.heart_rate,
  manual_threshold,
  baseline_heart_rate,
  percentage_threshold
)

st.metric(
  label = "Heart rate",
  value = str(st.session_state.heart_rate) + " bpm"
)

if flag_status == "Normal":
  st.success("Status: Normal")
elif flag_status == "Elevated HR":
  st.error("Status: Elevated HR detected")
elif flag_status == "Waiting for reading":
  st.info("Status: Waiting for live heart rate")
else:
  st.warning("Status: " + flag_status)

st.write(
  "Flag reason: "
  + flag_reason
)

if flag_status == "Elevated HR":
  st.error(
    "Mock VASTX update: cardiac output may be increased. "
    "Flag for review."
  )
  st.caption(
    "This is not a medical recommendation. "
    "It only demonstrates the prototype workflow."
  )
elif flag_status == "Normal":
  st.success(
    "Mock VASTX update: no elevated heart-rate flag detected."
  )
else:
  st.info(
    "Mock VASTX update: waiting for live physiological data."
  )

if st.session_state.connected:
  st.success(
    "Connection status: "
    + st.session_state.status
  )
else:
  st.warning(
    "Connection status: "
    + st.session_state.status
  )

st.header("Recording")

col1, col2, col3 = st.columns(3)

with col1:
  if st.button("Start recording"):
    if not st.session_state.connected:
      st.session_state.status = (
        "Please connect to a device before recording."
      )
    else:
      st.session_state.recording = True
      st.session_state.status = "Recording started."

with col2:
  if st.button("Stop recording"):
    if st.session_state.recording:
      st.session_state.recording = False
      st.session_state.status = "Recording stopped."
    else:
      st.session_state.status = (
        "Recording is not currently active."
      )

with col3:
  if st.button("Save CSV"):
    save_to_csv(
      participant_id,
      session_id
    )

st.write(
  "Recording active: ",
  st.session_state.recording
)

st.header("Data preview")

if len(st.session_state.data) > 0:
  df = pd.DataFrame(st.session_state.data)

  st.dataframe(
    df.tail(10),
    use_container_width = True
  )
else:
  st.write("No data recorded yet.")

st.header("Session summary")

if len(st.session_state.data) == 0:
  st.write("No session summary available yet.")
else:
  summary_df = pd.DataFrame(st.session_state.data)

  readings_collected = len(summary_df)
  minimum_heart_rate = int(summary_df["heart_rate_bpm"].min())
  maximum_heart_rate = int(summary_df["heart_rate_bpm"].max())
  mean_heart_rate = round(summary_df["heart_rate_bpm"].mean(), 1)

  elevated_readings = int(
    (
      summary_df["flag_status"]
      == "Elevated HR"
    ).sum()
  )

  percentage_flagged = round(
    elevated_readings / readings_collected * 100,
    1
  )

  summary_col1, summary_col2, summary_col3 = st.columns(3)

  with summary_col1:
    st.metric(
      "Readings collected",
      readings_collected
    )

    st.metric(
      "Minimum HR",
      str(minimum_heart_rate) + " bpm"
    )

  with summary_col2:
    st.metric(
      "Maximum HR",
      str(maximum_heart_rate) + " bpm"
    )

    st.metric(
      "Mean HR",
      str(mean_heart_rate) + " bpm"
    )

  with summary_col3:
    st.metric(
      "Elevated readings",
      elevated_readings
    )

    st.metric(
      "Percentage flagged",
      str(percentage_flagged) + "%"
    )

  if elevated_readings > 0:
    st.warning(
      "Mock VASTX session note: Elevated HR was detected "
      "during this session. Cardiac output may be increased. "
      "Flag for review."
    )
  else:
    st.success(
      "Mock VASTX session note: No elevated HR flag "
      "detected during this session."
    )

time.sleep(1)
st.rerun()