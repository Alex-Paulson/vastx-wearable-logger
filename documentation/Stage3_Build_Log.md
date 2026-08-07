# Stage 3 – PyInstaller Build Log

## Build Attempt 1

### Build Command

```powershell
.\build_env\Scripts\python.exe -m PyInstaller --noconfirm --clean --name "VASTX Wearable Logger" --onedir --add-data "app.py;." --collect-all streamlit launcher.py
```

### Result

- Build completed: Yes
- Executable created: Yes
- Executable launched: Yes
- Browser opened: Yes
- Streamlit application loaded: Yes

### Errors Encountered

Warnings were reported during packaging for optional system DLLs such as dbghelp.dll, bcrypt.dll, and IPHLPAPI.DLL, but the build completed successfully.

### Notes

The packaged app was rebuilt from the current source files, including the latest application entry point and launcher. The executable was verified to start successfully from the generated folder at dist/VASTX Wearable Logger/VASTX Wearable Logger.exe.