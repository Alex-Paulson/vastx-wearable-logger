import sys
import traceback

PACKAGES = [
  "streamlit",
  "bleak",
  "pandas",
  "openpyxl",
]

def main() -> int:
  print("VASTX portable dependency test")
  print(f"Python executable: {sys.executable}")
  print(f"Python version: {sys.version}")
  print()

  failed = []

  for package in PACKAGES:
    try:
      module = __import__(package)
      version = getattr(module, "__version__", "version not exposed")
      print(f"[PASS] {package}: {version}")
    except Exception:
      failed.append(package)
      print(f"[FAIL] {package}")
      traceback.print_exc()

  print()

  if failed:
    print("Import test failed for:", ", ".join(failed))
    return 1

  print("All portable package imports passed.")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())