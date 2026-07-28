import asyncio
import csv
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Queue

import pandas as pd
import streamlit as st
from bleak import BleakClient, BleakScanner

HEART_RATE_MEASUREMENT_UUID = (
  "00002a37-0000-1000-8000-00805f9b34fb"
)

BASELINE_DURATION_SECONDS = 300
DATA_FOLDER = Path(__file__).resolve().parent / "data"

def initialise_session_state():
  defaults = {
    "devices": [],
    "status": "Ready.",
    "connected": False,
    "recording": False,
    "heart_rate": "--",
    "data": [],
    "queue": Queue(),
    "device_name": "",
    "device_address": "",
    "connection_thread_started": False,
    "recording_start_time": None,
    "baseline_readings": [],
    "calculated_baseline_hr": None,
    "baseline_complete": False
  }

  for key, value in defaults.items():
    if key not in st.session_state:
      st.session_state[key] = value

def scan_devices():
  async def scan():
    return await BleakScanner.discover(
      timeout=10.0
    )

  devices = asyncio.run(scan())
  results = []

  for device in devices:
    name = device.name or "Unknown"

    results.append({
      "name": name,
      "address": device.address,
      "label": f"{name} - {device.address}",
      "device": device
    })

  results.sort(
    key=lambda item: (
      "polar h10" not in item["name"].lower(),
      item["name"].lower()
    )
  )

  return results

def parse_heart_rate(data):
  if len(data) < 2:
    raise ValueError(
      "Heart-rate packet was too short."
    )

  flags = data[0]

  if flags & 0x01:
    if len(data) < 3:
      raise ValueError(
        "The packet did not contain a 16-bit "
        "heart-rate value."
      )

    return int.from_bytes(
      data[1:3],
      byteorder="little"
    )

  return int(data[1])

def calculate_percentage_threshold(
  baseline_heart_rate,
  percentage_threshold
):
  return baseline_heart_rate * (
    1 + percentage_threshold / 100
  )

def calculate_percentage_above_baseline(
  heart_rate,
  baseline_heart_rate
):
  if baseline_heart_rate <= 0:
    return 0.0

  return (
    (heart_rate - baseline_heart_rate)
    / baseline_heart_rate
  ) * 100

def get_active_baseline(manual_baseline):
  calculated_baseline = (
    st.session_state.calculated_baseline_hr
  )

  if calculated_baseline is not None:
    return float(calculated_baseline)

  return float(manual_baseline)

def update_session_baseline(heart_rate):
  if not st.session_state.recording:
    return

  if st.session_state.recording_start_time is None:
    return

  if st.session_state.baseline_complete:
    return

  elapsed_seconds = (
    datetime.now()
    - st.session_state.recording_start_time
  ).total_seconds()

  if elapsed_seconds < BASELINE_DURATION_SECONDS:
    st.session_state.baseline_readings.append(
      int(heart_rate)
    )
    return

  if len(st.session_state.baseline_readings) == 0:
    st.session_state.status = (
      "The baseline period ended, but no "
      "heart-rate readings were collected."
    )
    return

  st.session_state.calculated_baseline_hr = round(
    sum(st.session_state.baseline_readings)
    / len(st.session_state.baseline_readings),
    1
  )

  st.session_state.baseline_complete = True

  st.session_state.status = (
    "Five-minute baseline complete. "
    "New readings are now compared with "
    "the calculated session baseline."
  )

def get_flag_details(
  heart_rate,
  manual_threshold,
  baseline_heart_rate,
  percentage_threshold
):
  if heart_rate == "--":
    return (
      "Waiting for reading",
      "Waiting for live heart-rate data"
    )

  try:
    heart_rate_value = int(heart_rate)
    manual_threshold_value = float(
      manual_threshold
    )
    baseline_value = float(
      baseline_heart_rate
    )
    percentage_value = float(
      percentage_threshold
    )
  except (ValueError, TypeError):
    return (
      "Invalid threshold",
      "Please enter valid threshold values"
    )

  calculated_threshold = (
    calculate_percentage_threshold(
      baseline_value,
      percentage_value
    )
  )

  manual_triggered = (
    heart_rate_value > manual_threshold_value
  )

  percentage_triggered = (
    heart_rate_value > calculated_threshold
  )

  percentage_text = (
    f"{percentage_value:.1f}"
    .rstrip("0")
    .rstrip(".")
  )

  if manual_triggered and percentage_triggered:
    return (
      "Elevated HR",
      "HR is above the manual threshold and "
      f"more than {percentage_text}% above baseline"
    )

  if manual_triggered:
    return (
      "Elevated HR",
      "HR is above the manual threshold"
    )

  if percentage_triggered:
    return (
      "Elevated HR",
      f"HR is more than {percentage_text}% "
      "above baseline"
    )

  return "Normal", "Within threshold"

def ble_worker(device, output_queue):
  async def connect():
    try:
      output_queue.put({
        "type": "status",
        "message": "Connecting to Polar H10."
      })

      async with BleakClient(
        device,
        winrt={
          "use_cached_services": False
        }
      ) as client:
        if not client.is_connected:
          output_queue.put({
            "type": "status",
            "message": "Connection failed."
          })
          return

        characteristic = (
          client.services.get_characteristic(
            HEART_RATE_MEASUREMENT_UUID
          )
        )

        if characteristic is None:
          output_queue.put({
            "type": "status",
            "message": (
              "Heart Rate Measurement characteristic "
              "was not found. Make sure the selected "
              "device is the Polar H10."
            )
          })
          return

        def handle_heart_rate(sender, data):
          del sender

          try:
            heart_rate = parse_heart_rate(
              data
            )

            output_queue.put({
              "type": "heart_rate",
              "heart_rate": heart_rate
            })
          except Exception as error:
            output_queue.put({
              "type": "status",
              "message": (
                "Error reading heart-rate data: "
                + str(error)
              )
            })

        await client.start_notify(
          characteristic,
          handle_heart_rate
        )

        output_queue.put({
          "type": "status",
          "message": "Connected."
        })

        while client.is_connected:
          await asyncio.sleep(1)

        output_queue.put({
          "type": "status",
          "message": (
            "Device disconnected. "
            "Please reconnect."
          )
        })

    except Exception as error:
      output_queue.put({
        "type": "status",
        "message": (
          "Connection failed: " + str(error)
        )
      })

  asyncio.run(connect())

def start_connection(device):
  thread = threading.Thread(
    target=ble_worker,
    args=(
      device,
      st.session_state.queue
    ),
    daemon=True
  )

  thread.start()

def safe_filename_part(value):
  cleaned = re.sub(
    r"[^A-Za-z0-9_-]+",
    "_",
    value.strip()
  )

  return cleaned or "unknown"

def save_to_csv(
  participant_id,
  session_id
):
  if len(st.session_state.data) == 0:
    st.session_state.status = (
      "No data available to save."
    )
    return None

  DATA_FOLDER.mkdir(
    parents=True,
    exist_ok=True
  )

  file_time = datetime.now().strftime(
    "%Y-%m-%d_%H-%M-%S"
  )

  participant_part = safe_filename_part(
    participant_id
  )

  session_part = safe_filename_part(
    session_id
  )

  filename = (
    f"VASTX_{participant_part}_"
    f"{session_part}_{file_time}.csv"
  )

  file_path = DATA_FOLDER / filename

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

  with file_path.open(
    "w",
    newline="",
    encoding="utf-8"
  ) as file:
    writer = csv.DictWriter(
      file,
      fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(
      st.session_state.data
    )

  st.session_state.status = (
    "Data saved successfully: "
    + str(file_path)
  )

  return file_path

def process_queue(
  participant_id,
  session_id,
  notes,
  manual_baseline,
  manual_threshold,
  percentage_threshold
):
  while not st.session_state.queue.empty():
    message = (
      st.session_state.queue.get()
    )

    if message["type"] == "status":
      status_message = message["message"]
      st.session_state.status = status_message

      if status_message == "Connected.":
        st.session_state.connected = True
        st.session_state.connection_thread_started = (
          True
        )

      lower_status = status_message.lower()

      if (
        "disconnected" in lower_status
        or "failed" in lower_status
        or "not found" in lower_status
      ):
        st.session_state.connected = False
        st.session_state.recording = False
        st.session_state.connection_thread_started = (
          False
        )

    if message["type"] == "heart_rate":
      heart_rate = message["heart_rate"]
      st.session_state.heart_rate = (
        heart_rate
      )

      update_session_baseline(
        heart_rate
      )

      active_baseline = get_active_baseline(
        manual_baseline
      )

      flag_status, flag_reason = (
        get_flag_details(
          heart_rate,
          manual_threshold,
          active_baseline,
          percentage_threshold
        )
      )

      percent_above_baseline = (
        calculate_percentage_above_baseline(
          heart_rate,
          active_baseline
        )
      )

      calculated_threshold = (
        calculate_percentage_threshold(
          active_baseline,
          percentage_threshold
        )
      )

      if st.session_state.recording:
        st.session_state.data.append({
          "timestamp": (
            datetime.now().strftime(
              "%Y-%m-%d %H:%M:%S"
            )
          ),
          "participant_id": participant_id,
          "session_id": session_id,
          "device_name": (
            st.session_state.device_name
          ),
          "device_address": (
            st.session_state.device_address
          ),
          "heart_rate_bpm": heart_rate,
          "threshold_bpm": (
            manual_threshold
          ),
          "baseline_hr_bpm": round(
            active_baseline,
            1
          ),
          "percent_above_baseline": round(
            percent_above_baseline,
            1
          ),
          "calculated_percentage_threshold_bpm": (
            round(
              calculated_threshold,
              1
            )
          ),
          "flag_status": flag_status,
          "flag_reason": flag_reason,
          "rr_intervals_ms": "",
          "event_marker": "",
          "notes": notes
        })

initialise_session_state()

st.set_page_config(
  page_title="VASTX Wearable Logger",
  layout="wide"
)

st.title("VASTX Wearable Logger")

st.write(
  "Polar H10 live physiological data logger"
)

st.info(
  "Status: " + st.session_state.status
)

st.header("Participant details")

participant_id = st.text_input(
  "Participant ID",
  value="P001"
)

session_id = st.text_input(
  "Session ID",
  value="S001"
)

notes = st.text_area(
  "Notes",
  value=""
)

st.header("Threshold settings")

baseline_heart_rate = st.number_input(
  "Manual baseline HR, bpm",
  min_value=30,
  max_value=220,
  value=75,
  step=1,
  key="baseline_hr_input"
)

manual_threshold = st.number_input(
  "Alert threshold, bpm",
  min_value=30,
  max_value=220,
  value=100,
  step=1,
  key="manual_threshold_input"
)

percentage_threshold = st.number_input(
  "Percentage increase threshold, %",
  min_value=0,
  max_value=200,
  value=20,
  step=1,
  key="percentage_threshold_input"
)

process_queue(
  participant_id,
  session_id,
  notes,
  baseline_heart_rate,
  manual_threshold,
  percentage_threshold
)

active_baseline = get_active_baseline(
  baseline_heart_rate
)

calculated_percentage_threshold = (
  calculate_percentage_threshold(
    active_baseline,
    percentage_threshold
  )
)

st.write(
  "Active baseline used for comparison: "
  f"{active_baseline:.1f} bpm"
)

st.write(
  "Calculated percentage threshold: "
  f"{calculated_percentage_threshold:.1f} bpm"
)

st.subheader("Session baseline")

if st.session_state.recording_start_time is None:
  st.info(
    "Baseline collection has not started. "
    "Start recording to begin the "
    "five-minute baseline period."
  )

elif st.session_state.baseline_complete:
  st.success(
    "Five-minute baseline complete."
  )

  st.metric(
    "Calculated baseline HR",
    (
      str(
        st.session_state.calculated_baseline_hr
      )
      + " bpm"
    )
  )

  st.write(
    "Baseline readings used:",
    len(
      st.session_state.baseline_readings
    )
  )

else:
  elapsed_seconds = (
    datetime.now()
    - st.session_state.recording_start_time
  ).total_seconds()

  remaining_seconds = max(
    0,
    BASELINE_DURATION_SECONDS
    - elapsed_seconds
  )

  st.info(
    "Collecting the five-minute baseline. "
    f"Time remaining: {int(remaining_seconds)} "
    "seconds"
  )

  st.write(
    "Baseline readings collected:",
    len(
      st.session_state.baseline_readings
    )
  )

  if len(
    st.session_state.baseline_readings
  ) > 0:
    provisional_baseline = round(
      sum(
        st.session_state.baseline_readings
      )
      / len(
        st.session_state.baseline_readings
      ),
      1
    )

    st.write(
      "Current provisional baseline average: "
      f"{provisional_baseline} bpm"
    )

st.header("Device connection")

if st.button("Scan for devices"):
  st.session_state.status = (
    "Scanning for devices."
  )

  try:
    st.session_state.devices = (
      scan_devices()
    )

    if len(
      st.session_state.devices
    ) == 0:
      st.session_state.status = (
        "No devices found."
      )
    else:
      st.session_state.status = (
        "Devices found."
      )

  except Exception as error:
    st.session_state.status = (
      "Scanning failed: " + str(error)
    )

device_labels = [
  device["label"]
  for device in st.session_state.devices
]

selected_device = st.selectbox(
  "Detected devices",
  options=device_labels,
  index=None,
  placeholder="Select a device"
)

if st.button("Connect"):
  if not selected_device:
    st.session_state.status = (
      "Please select a device first."
    )
  else:
    selected = next(
      (
        device
        for device
        in st.session_state.devices
        if device["label"] == selected_device
      ),
      None
    )

    if selected is None:
      st.session_state.status = (
        "Please select a device first."
      )

    elif (
      "polar h10"
      not in selected["name"].lower()
    ):
      st.session_state.status = (
        "Please select the Polar H10 device."
      )

    elif (
      st.session_state.connection_thread_started
    ):
      st.session_state.status = (
        "A connection attempt is already running."
      )

    else:
      st.session_state.device_name = (
        selected["name"]
      )

      st.session_state.device_address = (
        selected["address"]
      )

      st.session_state.status = (
        "Connecting to Polar H10."
      )

      st.session_state.connection_thread_started = (
        True
      )

      start_connection(
        selected["device"]
      )

st.header("Live data")

process_queue(
  participant_id,
  session_id,
  notes,
  baseline_heart_rate,
  manual_threshold,
  percentage_threshold
)

active_baseline = get_active_baseline(
  baseline_heart_rate
)

flag_status, flag_reason = (
  get_flag_details(
    st.session_state.heart_rate,
    manual_threshold,
    active_baseline,
    percentage_threshold
  )
)

st.metric(
  label="Heart rate",
  value=(
    str(
      st.session_state.heart_rate
    )
    + " bpm"
  )
)

if flag_status == "Normal":
  st.success(
    "Status: Normal"
  )

elif flag_status == "Elevated HR":
  st.error(
    "Status: Elevated HR detected"
  )

elif flag_status == "Waiting for reading":
  st.info(
    "Status: Waiting for live heart rate"
  )

else:
  st.warning(
    "Status: " + flag_status
  )

st.write(
  "Flag reason: " + flag_reason
)

if flag_status == "Elevated HR":
  st.error(
    "Mock VASTX update: cardiac output "
    "may be increased. Flag for review."
  )

  st.caption(
    "This is not a medical recommendation. "
    "It only demonstrates the prototype workflow."
  )

elif flag_status == "Normal":
  st.success(
    "Mock VASTX update: no elevated "
    "heart-rate flag detected."
  )

else:
  st.info(
    "Mock VASTX update: waiting for "
    "live physiological data."
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
        "Please connect to a device "
        "before recording."
      )

    elif st.session_state.recording:
      st.session_state.status = (
        "Recording is already active."
      )

    else:
      st.session_state.recording = True

      st.session_state.recording_start_time = (
        datetime.now()
      )

      st.session_state.baseline_readings = []

      st.session_state.calculated_baseline_hr = (
        None
      )

      st.session_state.baseline_complete = False
      st.session_state.data = []

      st.session_state.status = (
        "Recording started. Collecting the "
        "five-minute session baseline."
      )

with col2:
  if st.button("Stop recording"):
    if st.session_state.recording:
      st.session_state.recording = False

      st.session_state.status = (
        "Recording stopped."
      )
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
  "Recording active:",
  st.session_state.recording
)

st.header("Data preview")

if len(st.session_state.data) > 0:
  preview_df = pd.DataFrame(
    st.session_state.data
  )

  st.dataframe(
    preview_df.tail(10),
    use_container_width=True
  )
else:
  st.write(
    "No data recorded yet."
  )

st.header("Session summary")

if len(st.session_state.data) == 0:
  st.write(
    "No session summary available yet."
  )
else:
  summary_df = pd.DataFrame(
    st.session_state.data
  )

  readings_collected = len(
    summary_df
  )

  minimum_heart_rate = int(
    summary_df["heart_rate_bpm"].min()
  )

  maximum_heart_rate = int(
    summary_df["heart_rate_bpm"].max()
  )

  mean_heart_rate = round(
    summary_df["heart_rate_bpm"].mean(),
    1
  )

  elevated_readings = int(
    (
      summary_df["flag_status"]
      == "Elevated HR"
    ).sum()
  )

  percentage_flagged = round(
    elevated_readings
    / readings_collected
    * 100,
    1
  )

  summary_col1, summary_col2, summary_col3 = (
    st.columns(3)
  )

  with summary_col1:
    st.metric(
      "Readings collected",
      readings_collected
    )

    st.metric(
      "Minimum HR",
      f"{minimum_heart_rate} bpm"
    )

  with summary_col2:
    st.metric(
      "Maximum HR",
      f"{maximum_heart_rate} bpm"
    )

    st.metric(
      "Mean HR",
      f"{mean_heart_rate} bpm"
    )

  with summary_col3:
    st.metric(
      "Elevated readings",
      elevated_readings
    )

    st.metric(
      "Percentage flagged",
      f"{percentage_flagged}%"
    )

  if elevated_readings > 0:
    st.warning(
      "Mock VASTX session note: Elevated HR "
      "was detected during this session. "
      "Cardiac output may be increased. "
      "Flag for review."
    )
  else:
    st.success(
      "Mock VASTX session note: No elevated "
      "HR flag was detected during this session."
    )

time.sleep(1)
st.rerun()