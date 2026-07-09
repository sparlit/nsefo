#!/bin/bash
# MASTER PRO - LINUX INSTALLER
set -e
echo "[1/3] Installing Dependencies..."
python3 -m pip install -r requirements.txt --quiet
python3 -m pip install maturin --quiet

echo "[2/3] Compiling Performance Core..."
cd nsefo_core
python3 -m maturin build --release
python3 -m pip install target/wheels/*.whl --force-reinstall --quiet
cd ..

echo "[3/3] Launching Configuration Wizard..."
export PYTHONPATH=$PYTHONPATH:.
python3 start_master_pro.py --setup
