# 🛠️ Installation & Setup Guide

The **NSEFO Master Pro** system features a unified installation process for both Windows and Linux.

## 📋 Pre-requisites
### 1. Software
- **Python 3.10 or higher**: Must be added to your System PATH.
- **Rust Toolchain**: Required to compile the high-performance core. [Install here](https://rustup.rs/).
- **Git**: For repository cloning.

### 2. Trading Access
- **Dhan API ID & Token**: Generate these from the Dhan Developer portal.
- **TOTP Secret**: Found in your security settings (Required for "No-Login" operation).

---

## 🚀 Step-by-Step Installation

### **Linux / macOS**
Execute the unified installer:
```bash
chmod +x setup.sh
./setup.sh
```
*Alternatively, you can use the single-word wrapper:* `./install`

### **Windows**
Run the batch installer from Command Prompt or PowerShell:
```cmd
setup.bat
```
*Alternatively, you can use the single-word command:* `install`

---

## ⚙️ Configuration Wizard
After compilation, the system will prompt you for:
1. **Trading Mode**: `paper` (simulation) or `live`.
2. **Dhan ID & Token**: Your API credentials.
3. **Operational Capital**: Total INR to be used for risk % calculations.
4. **Fixed Lot Count**: Your manual lot size override (default 1).

---

## ✅ Post-Installation Checks
1. Ensure `config.json` is generated in the root directory.
2. Verify `nsefo_core` is installed in your site-packages (`pip list | grep nsefo`).
3. Check connectivity via the launcher health report.
