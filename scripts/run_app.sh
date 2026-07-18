#!/bin/bash
# NSEFO Master Pro — Alternative Linux launcher (calls start_master_pro.py directly)
# For normal startup use: ./nsefo (which calls run.py with full connectivity check)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
exec python3 "$SCRIPT_DIR/start_master_pro.py" "$@"