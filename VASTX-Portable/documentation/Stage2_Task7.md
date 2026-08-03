# Stage 2 - Task 7

## Portable Application Testing

### Objective

The aim of this task was to verify that the portable VASTX Wearable Logger could be launched successfully using the embedded Python runtime and tested as an end user would use it.

---

## Test Environment

Operating System:
- Windows 11

Embedded Python:
- Python 3.12.9 (64-bit)

Application:
- VASTX Wearable Logger

---

## Test Results

| Test | Result |
|------|--------|
| Portable launcher starts | PASS |
| Embedded Python launches | PASS |
| Streamlit starts correctly | PASS |
| Application opens in browser | PASS |
| GUI loads successfully | PASS |
| Polar H10 scanning works | PASS |
| Device connection works | PASS |
| Live heart rate displayed | PASS |
| Recording starts and stops | PASS |
| CSV file saved successfully | PASS |

---

## Startup Performance

Approximate startup time:
- 5-10 seconds

Approximate portable folder size:
- (Record after Task 8)

---

## Issues Encountered

During testing the browser initially displayed a "Not Found" page.

This was resolved by correcting the launcher configuration so that it opened the correct Streamlit application.

No further issues were encountered.

---

## Outcome

The portable deployment successfully launched using the embedded Python runtime.

The application functioned correctly without requiring the user to manually enter Python or Streamlit commands.

The application was successfully tested using the portable launcher.

## Result

.Sum / 1MB
350.767563819885