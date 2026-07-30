# Stage 2 - Task 6

## Portable Launcher

### Objective

Create a launcher that starts the VASTX Wearable Logger by using the embedded Python runtime.

### Implementation

A Windows batch file (`Start VASTX Portable.bat`) was created.

The launcher:

- Changes to the application directory.
- Starts the embedded Python directory.
- Launches the Streamlit application.
- Records console output in `logs/launcher.log`.

### Testing

The launcher was executed successfully.

The application started without requiring a system-wide Python installation.

### Outcome

The application can be started by double-clicking the launcher, improving portability and ease of use.