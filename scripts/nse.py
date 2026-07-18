#!/usr/bin/env python3
"""
NSEFO — Single-word entry: python nse.py  (or ./nse.py on Linux with +x)
Works on Windows, Linux, and macOS without any extension in the command.
"""
import sys, os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.environ["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

from run import main
sys.exit(main())