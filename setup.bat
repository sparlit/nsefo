@echo off
echo ╔================================================╗
echo ║  NSEFO MASTER PRO - EXPERT SYSTEM SETUP        ║
echo ╚================================================╝

echo [1/4] Installing Core Dependencies...
pip install -r requirements.txt --quiet
pip install maturin --quiet

echo [2/4] Compiling High-Performance Rust Brains...
cd nsefo_core
maturin build --release
for %%i in (target\wheels\*.whl) do pip install "%%i" --force-reinstall --quiet
cd ..

echo [3/4] Creating Entry Point...
echo @echo off > nsefo.bat
echo set PYTHONPATH=%%PYTHONPATH%%;. >> nsefo.bat
echo python start_master_pro.py %%* >> nsefo.bat

echo [4/4] Setup Complete. Launching Master Pro Wizard...
call nsefo.bat
