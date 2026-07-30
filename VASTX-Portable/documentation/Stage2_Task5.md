# Stage 2 - Task 5

## Embedded Python Configuration

### Objective

Configure the embedded Python runtime so that all required packages are loaded from the portable application folder.

### Configuration

The embedded Python runtime was configured by modifying the `python312._pth` file.

Additional search paths were added:

```
..\packages
..\app
```

The `import site` option was enabled.

### Verification

The following packages were successfully imported:
- streamlit
- bleak
- pandas
- openpyxl

The embedded Python runtime correctly located all of the packages from the portable `packages` directory.

### Outcome

The embedded Python environment is now fully configured and ready to execute the VASTX Wearable Logger independently of any system-wide Python installation.