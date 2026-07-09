#!/bin/bash
# MASTER PRO - LINUX INSTALLER
set -e
echo "[1/3] Installing Dependencies..."
pip install -r requirements.txt --quiet
pip install maturin --quiet

echo "[2/3] Compiling Performance Core..."
cd nsefo_core
maturin build --release
pip install target/wheels/*.whl --force-reinstall --quiet
cd ..

echo "[3/3] Launching Configuration Wizard..."
export PYTHONPATH=$PYTHONPATH:.
python3 start_master_pro.py --setup
