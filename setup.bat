@echo off
setlocal
echo [1/3] Installing Dependencies...
pip install -r requirements.txt --quiet
pip install maturin --quiet

echo [2/3] Compiling Performance Core...
cd nsefo_core
maturin build --release
for %%i in (target\wheels\*.whl) do pip install "%%i" --force-reinstall --quiet
cd ..

echo [3/3] Launching Configuration Wizard...
set PYTHONPATH=%PYTHONPATH%;.
python start_master_pro.py --setup
endlocal
