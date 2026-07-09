#!/bin/bash
# NSEFO MASTER PRO - UNIFIED SETUP & LAUNCHER

echo "╔================================================╗"
echo "║  NSEFO MASTER PRO - EXPERT SYSTEM SETUP        ║"
echo "╚================================================╝"

# Dependency Installation
echo "[1/4] Installing Core Dependencies..."
pip install -r requirements.txt --quiet
pip install maturin --quiet

# Rust Calculation Core Build
echo "[2/4] Compiling High-Performance Rust Brains..."
cd nsefo_core
maturin build --release
pip install target/wheels/*.whl --force-reinstall --quiet
cd ..

# Wrapper Setup
echo "[3/4] Creating Entry Point..."
cat <<INNEREOF > nsefo
#!/bin/bash
export PYTHONPATH=\$PYTHONPATH:.
python3 start_master_pro.py "\$@"
INNEREOF
chmod +x nsefo

# Final Launch
echo "[4/4] Setup Complete. Launching Master Pro Wizard..."
./nsefo
