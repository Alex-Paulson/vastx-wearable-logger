"""Resolve read-only application resources and persistent user data paths."""

from pathlib import Path
import sys


def get_resource_base() -> Path:
  """Return the folder containing bundled, read-only application files."""
  if getattr(sys, "frozen", False):
    return Path(sys._MEIPASS).resolve()

  return Path(__file__).resolve().parent


def get_runtime_base() -> Path:
  """Return the persistent folder beside the executable (or source files)."""
  if getattr(sys, "frozen", False):
    return Path(sys.executable).resolve().parent

  return Path(__file__).resolve().parent


RESOURCE_FOLDER = get_resource_base()
RUNTIME_FOLDER = get_runtime_base()
DATA_FOLDER = RUNTIME_FOLDER / "data"
LOGS_FOLDER = RUNTIME_FOLDER / "logs"


def create_user_folders() -> None:
  """Create folders used for files that must survive application shutdown."""
  DATA_FOLDER.mkdir(parents=True, exist_ok=True)
  LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
