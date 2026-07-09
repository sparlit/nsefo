@echo off
setlocal
echo [1/3] Installing Dependencies...
python -m pip install -r requirements.txt --quiet
python -m pip install maturin --quiet

echo [2/3] Compiling Performance Core...
cd nsefo_core
set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
python -m maturin build --release
for %%i in (target\wheels\*.whl) do python -m pip install "%%i" --force-reinstall --quiet
cd ..

echo [3/3] Launching Configuration Wizard...
set PYTHONPATH=%PYTHONPATH%;.
python start_master_pro.py --setup
endlocal
