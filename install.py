#!/usr/bin/env python3
"""
NSEFO Master Pro - Installation Script
Cross-platform: runs on Windows and Linux.
Usage: python install.py
        python install.py --non-interactive   (skip credential prompts, use config.json)
"""
import sys
import os
import subprocess
import json
import shutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [INSTALL] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("install")


def check_python_version():
    """Require Python 3.10 or higher."""
    if sys.version_info < (3, 10):
        logger.error("Python 3.10+ required. You have %s", sys.version.split()[0])
        sys.exit(1)
    logger.info("Python %s verified", sys.version.split()[0])


def check_rust():
    """Verify Rust/Cargo is installed."""
    try:
        result = subprocess.run(
            ["cargo", "--version"], capture_output=True, text=True
        )
        logger.info("Rust %s found", result.stdout.strip())
        return True
    except FileNotFoundError:
        logger.error("Rust not found. Install from: https://rustup.rs")
        return False


def check_pip():
    """Verify pip is available."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        logger.error("pip not available")
        return False


def _prompt(prompt_text, fallback):
    """Read input with fallback for non-interactive use."""
    try:
        val = input(prompt_text)
        return val.strip() or fallback
    except (EOFError, OSError):
        return fallback


def get_credentials(existing_cfg):
    """Collect broker API credentials interactively."""
    print("\n" + "=" * 48)
    print("  CONFIGURATION WIZARD")
    print("=" * 48)

    # Provider selection
    providers = [
        ("dhan", "Dhan (dhanhq SDK)"),
        ("fenix", "Dhan (Fenix Gateway)"),
        ("zerodha", "Zerodha Kite Connect"),
        ("angelone", "AngelOne SmartAPI"),
        ("upstox", "Upstox"),
        ("fyers", "Fyers API v2"),
        ("kotak", "Kotak Securities"),
        ("kotak_neo", "Kotak Neo"),
        ("5paisa", "5paisa"),
        ("iifl", "IIFL Markets"),
        ("motilal", "Motilal Oswal"),
        ("finvasia", "Finvasia (Shoonya)"),
        ("choice", "Choice Broking"),
        ("vpc", "VPC"),
        ("aliceblue", "AliceBlue"),
        ("moneysukh", "Moneysukh (ONUS Capital)"),
        ("hdfc", "HDFC Securities"),
        ("icici", "ICICI Direct"),
        ("sbi", "SBI Securities"),
        ("bajaj", "Bajaj Financial"),
        ("geojit", "Geojit"),
        ("sharekhan", "Mirae Asset Sharekhan"),
        ("anand_rathi", "Anand Rathi"),
        ("edelweiss", "Edelweiss"),
        ("nirmal_bang", "Nirmal Bang"),
        ("axis_direct", "Axis Direct"),
        ("groww", "Groww"),
        ("paytm_money", "Paytm Money"),
        ("kunjee", "Kunjee"),
        ("master_trust", "Master Trust"),
    ]

    print("\nSupported Brokers:")
    for i, (key, label) in enumerate(providers, 1):
        print(f"  {i:2d}. {label}")
    print()

    # Provider prompt with default
    default_provider = existing_cfg.get("provider", "")
    if default_provider and default_provider not in dict(providers):
        default_provider = ""

    provider_idx = _prompt(
        f"Broker number [press Enter to list]: ",
        ""
    )
    if provider_idx.strip():
        try:
            idx = int(provider_idx) - 1
            if 0 <= idx < len(providers):
                selected_provider = providers[idx][0]
            else:
                selected_provider = _prompt(f"Broker key (e.g. fenix): ", existing_cfg.get("provider", "fenix"))
        except ValueError:
            selected_provider = _prompt(f"Broker key (e.g. fenix): ", existing_cfg.get("provider", "fenix"))
    else:
        selected_provider = _prompt(f"Broker key (e.g. fenix) [{existing_cfg.get('provider', 'fenix')}]: ", existing_cfg.get("provider", "fenix"))

    client_id = _prompt(
        f"Client ID / User ID [{existing_cfg.get('client_id', '')}]: ",
        existing_cfg.get("client_id", "")
    )
    access_token = _prompt(
        f"API Access Token [enter or paste token]: ",
        existing_cfg.get("access_token", "")
    )
    mode = _prompt(
        f"Trading Mode (live/paper) [{existing_cfg.get('mode', 'paper')}]: ",
        existing_cfg.get("mode", "paper")
    )

    risk = existing_cfg.get("risk", {})
    capital = _prompt(
        f"Operational Capital [\u20b9{risk.get('capital', 1000000):,.0f}]: ",
        risk.get("capital", 1000000)
    )
    fixed_lots = _prompt(
        f"Fixed Lot Count [{risk.get('fixed_lots', 1)}]: ",
        risk.get("fixed_lots", 1)
    )

    totp_secret = _prompt(
        f"TOTP Secret [{existing_cfg.get('totp_secret', '')}]: ",
        existing_cfg.get("totp_secret", "")
    )
    api_key = _prompt(
        f"API Key (if required by broker) [{existing_cfg.get('api_key', '')}]: ",
        existing_cfg.get("api_key", "")
    )

    # target_frequency: trading cadence
    print("\nTrading Frequency Modes:")
    print("  1. scalping  — 2s REST polling, rapid order placement")
    print("  2. swing    — 60s polling, overnight holds")
    print("  3. hft      — WebSocket, <50ms target latency")
    tf_default = existing_cfg.get("target_frequency", "scalping")
    tf_choice = _prompt(f"Target frequency (scalping/swing/hft) [{tf_default}]: ", tf_default)
    target_frequency = tf_choice if tf_choice in ("scalping", "swing", "hft") else "scalping"

    # data_provider: live broker key for paper mode price feed
    dp_default = existing_cfg.get("data_provider", "")
    data_provider = _prompt(f"Live data provider for paper mode (broker key, empty=none) [{dp_default}]: ", dp_default)

    try:
        capital = float(capital)
    except (ValueError, TypeError):
        capital = 1000000.0

    try:
        fixed_lots = int(fixed_lots)
    except (ValueError, TypeError):
        fixed_lots = 1

    return {
        "mode": mode.lower() in ("live", "paper") and mode.lower() or "paper",
        "client_id": client_id,
        "access_token": access_token,
        "totp_secret": totp_secret,
        "provider": selected_provider,
        "api_key": api_key,
        "target_frequency": target_frequency,
        "data_provider": data_provider,
        "risk": {
            "capital": capital,
            "fixed_lots": fixed_lots,
            "max_risk_per_trade_percent": risk.get("max_risk_per_trade_percent", 1.0),
            "daily_max_loss": risk.get("daily_max_loss", 5000.0),
        }
    }


def verify_broker_connectivity(cfg):
    """Test broker API login. Return True on success."""
    provider = cfg.get("provider", "")
    client_id = cfg.get("client_id", "")
    access_token = cfg.get("access_token", "")
    api_key = cfg.get("api_key", "")

    try:
        from python_app.broker.session_manager import SessionManager
        sm = SessionManager()
        broker = sm.get_broker()
        if broker and broker.login():
            logger.info("[OK] Broker API connectivity verified.")
            return True
    except Exception as e:
        logger.error("Connectivity check failed: %s", e)
    return False


def install_dependencies():
    """Install Python packages from requirements.txt."""
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_file):
        logger.error("requirements.txt not found")
        sys.exit(1)
    logger.info("Installing Python dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_file, "-q"],
        check=True
    )
    logger.info("Dependencies installed.")


def install_maturin():
    """Install maturin for Rust build."""
    logger.info("Installing maturin...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "maturin", "-q"],
        check=True
    )
    logger.info("maturin installed.")


def build_rust_core():
    """Compile the Rust extension (nsefo_core) using maturin."""
    core_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nsefo_core")
    logger.info("Compiling Rust performance core...")
    env = os.environ.copy()
    env["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "maturin", "build", "--release"],
        cwd=core_dir,
        env=env,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logger.error("Rust build failed:\n%s", result.stderr)
        sys.exit(1)
    logger.info("Rust core compiled successfully.")

    # Find and install the wheel
    wheels_dir = os.path.join(core_dir, "target", "wheels")
    whl_files = [f for f in os.listdir(wheels_dir) if f.endswith(".whl")]
    if not whl_files:
        logger.error("No wheel file found after build")
        sys.exit(1)
    whl_path = os.path.join(wheels_dir, whl_files[0])
    logger.info("Installing wheel: %s", whl_files[0])
    subprocess.run(
        [sys.executable, "-m", "pip", "install", whl_path, "--force-reinstall", "-q"],
        check=True
    )
    logger.info("nsefo_core installed in site-packages.")


def save_config(cfg):
    """Persist configuration to config.json."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=4)
    logger.info("Configuration saved to config.json")


def main():
    print("\n" + "=" * 50)
    print("  NSEFO MASTER PRO - INSTALLATION")
    print("=" * 50 + "\n")

    check_python_version()
    if not check_pip():
        sys.exit(1)

    # Load existing config if available
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    existing_cfg = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            existing_cfg = json.load(f)
        logger.info("Existing config found.")

    # Non-interactive mode: skip credential prompts
    non_interactive = "--non-interactive" in sys.argv or "-y" in sys.argv

    # Step 1: Dependencies
    print("\n[1/4] Installing Dependencies...")
    install_dependencies()
    install_maturin()

    # Step 2: Build Rust core
    print("\n[2/4] Compiling Performance Core...")
    if not check_rust():
        logger.warning("Rust not found. Install from https://rustup.rs")
        logger.warning("Skipping Rust compilation - install Rust then re-run.")
    else:
        build_rust_core()

    # Step 3: Credentials
    print("\n[3/4] Configuration Wizard...")
    cfg = get_credentials(existing_cfg) if not non_interactive else existing_cfg

    # Step 4: Connectivity check
    print("\n[4/4] Validating Connectivity...")
    connectivity_ok = verify_broker_connectivity(cfg)

    save_config(cfg)

    print("\n" + "=" * 50)
    if connectivity_ok:
        print("  INSTALLATION COMPLETE")
    else:
        print("  INSTALLATION COMPLETE (check credentials)")
    print("=" * 50)
    print("\n  To start the application:")
    print("  Windows: nsefo")
    print("  Linux:   ./nsefo")
    print("  Or:      python run.py")
    print()


if __name__ == "__main__":
    main()