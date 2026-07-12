#!/bin/bash
# ==============================================================================
# NSEFO Master Pro — Linux Installer (legacy alias)
# Prefer: ./install   (identical functionality)
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/install" "$@"