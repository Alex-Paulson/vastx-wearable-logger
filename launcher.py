from pathlib import Path
import logging
import sys
import threading
import time
import webbrowser

from streamlit.web import cli as streamlit_cli
from runtime_paths import (
  LOGS_FOLDER,
  RESOURCE_FOLDER,
  create_user_folders
)

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 8501
STARTUP_DELAY_SECONDS = 4

def open_browser() -> None:
  time.sleep(STARTUP_DELAY_SECONDS)

  webbrowser.open(
    f"http://{SERVER_ADDRESS}:{SERVER_PORT}"
  )

def find_app_file() -> Path:
  return RESOURCE_FOLDER / "app.py"

def configure_logging() -> None:
  create_user_folders()

  logging.basicConfig(
    filename=LOGS_FOLDER / "vastx.log",
    level=logging.INFO,
    format=(
      "%(asctime)s %(levelname)s %(name)s: "
      "%(message)s"
    ),
    encoding="utf-8"
  )

def main() -> int:
  configure_logging()
  logging.info("VASTX Wearable Logger starting")

  app_file = find_app_file()

  if not app_file.exists():
    print("VASTX Wearable Logger could not start.")
    print("The application file was not found.")
    print(app_file)
    input("Press Enter to close...")
    return 1

  browser_thread = threading.Thread(
    target = open_browser,
    daemon = True
  )

  browser_thread.start()

  sys.argv = [
    "streamlit",
    "run",
    str(app_file),
    "--global.developmentMode=false",
    "--server.address=127.0.0.1",
    "--server.port=8501",
    "--server.headless=true",
    "--browser.gatherUsageStats=false"
  ]

  try:
    streamlit_cli.main()
  except Exception as error:
    logging.exception("VASTX Wearable Logger stopped with an error")
    print()
    print("VASTX Wearable Logger stopped with an error: ")
    print(error)
    input("Please Enter to close...")
    return 1

  return 0

if __name__ == "__main__":
  raise SystemExit(main())
