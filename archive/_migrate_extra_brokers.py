#!/usr/bin/env python3
"""
Migrate new broker names into python_app/brokers/registry.py and create stub files.
Run: python _migrate_extra_brokers.py
"""
import re, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "python_app/brokers/registry.py")
PROVIDERS_DIR = os.path.join(SCRIPT_DIR, "python_app/brokers/providers")

# ── Helpers ────────────────────────────────────────────────────────────────

def to_key(name: str) -> str:
    """Best-effort provider key from full company name."""
    # Remove common suffixes and prefixes
    s = re.sub(r'\s+(PVT\.?|LTD\.?|LIMITED|PRIVATE|LLP|India|Ireland|Singapore|USA|UK)\s*$', '', name.strip(), flags=re.IGNORECASE)
    s = re.sub(r'^THE\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s.strip())
    # Keep first 4-5 significant words
    words = [w for w in s.split() if len(w) > 2]
    key = '_'.join(words[:4]).lower()
    key = re.sub(r'[^a-z0-9_]', '', key)
    key = re.sub(r'_+', '_', key).strip('_')
    return key if key else "unknown_broker"


def read_registry() -> tuple[str, str, str]:
    with open(REGISTRY_PATH, encoding='utf-8') as f:
        content = f.read()
    start = content.index("PROVIDER_INFO = {")
    end = content.rindex("}") + 1
    return content[:start], content[start:end], content[end:]


def read_providers_init() -> str:
    path = os.path.join(PROVIDERS_DIR, "__init__.py")
    with open(path, encoding='utf-8') as f:
        return f.read()


# ── STUB TEMPLATE ───────────────────────────────────────────────────────────

STUB_TEMPLATE = '''"""%(provider_key)s broker stub — auto-generated."""
import logging
from typing import List, Dict, Any
from ..base import Broker

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class %(class_name)s(Broker):
    """%(name)s — STUB implementation (no verified API endpoints)."""

    _provider_key = "%(provider_key)s"

    def __init__(self, **kwargs):
        self.logger = logging.getLogger("%(class_name)s")
        self.base_url = kwargs.get("base_url", "")
        # Accept any credentials passed in via kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _get_client(self):
        if not _HAS_HTTPX:
            raise ImportError("httpx is required: pip install httpx")
        import certifi
        return httpx.Client(verify=certifi.where(), timeout=15.0)

    def login(self, **kwargs) -> bool:
        self.logger.warning(
            "%(name)s — login() is a stub. "
            "No verified API endpoints available. "
            "Please verify the correct API URL from your browser DevTools Network tab."
        )
        return False

    def get_market_data(self, symbols: List[Dict[str, str]]) -> Dict[str, Any]:
        self.logger.warning("%(name)s — get_market_data() not implemented (stub)", )
        return {}

    def get_historical_data(self, symbol: Dict[str, str], interval: str,
                           from_date: str, to_date: str) -> Any:
        self.logger.warning("%(name)s — get_historical_data() not implemented (stub)", )
        return []

    def place_order(self, order: Dict[str, Any]) -> str:
        self.logger.warning("%(name)s — place_order() not implemented (stub)", )
        return ""

    def get_orderbook(self) -> List[Dict[str, Any]]:
        self.logger.warning("%(name)s — get_orderbook() not implemented (stub)", )
        return []

    def get_positions(self) -> List[Dict[str, Any]]:
        self.logger.warning("%(name)s — get_positions() not implemented (stub)", )
        return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        self.logger.warning("%(name)s — get_holdings() not implemented (stub)", )
        return []

    def logout(self) -> bool:
        self.logger.warning("%(name)s — logout() not implemented (stub)", )
        return False

    def get_profile(self) -> Dict[str, Any]:
        self.logger.warning("%(name)s — get_profile() not implemented (stub)", )
        return {}

    def cancel_order(self, order_id: str) -> bool:
        self.logger.warning("%(name)s — cancel_order() not implemented (stub)", )
        return False

    def modify_order(self, order_id: str, **kwargs) -> bool:
        self.logger.warning("%(name)s — modify_order() not implemented (stub)", )
        return False

'''

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Read current registry
    prefix, provider_block, suffix = read_registry()
    providers_init = read_providers_init()

    # Extract existing keys
    existing_keys = set(re.findall(r'^\s+"(\w+)":\s*\{', provider_block, re.MULTILINE))

    # Parse the new broker list from stdin (passed via heredoc or redirect)
    # We'll read all lines from the script's stdin
    new_brokers_raw = sys.stdin.read().strip().split('\n')

    # Parse broker names (skip empty lines)
    new_brokers = []
    for line in new_brokers_raw:
        name = line.strip()
        if not name:
            continue
        # Remove leading index numbers like "21ARTHA" -> "21ARTHA" (keep them as part of name)
        # Actually some entries start with numbers, keep them
        new_brokers.append(name)

    print(f"[MIGRATE] {len(new_brokers)} broker names received")
    print(f"[MIGRATE] {len(existing_keys)} existing keys in registry")

    # Generate new entries
    new_entries = {}  # key -> registry dict
    new_stub_files = []  # list of (key, class_name, name)

    # Deduplicate against existing keys
    for name in new_brokers:
        key = to_key(name)
        if key in existing_keys or key in new_entries:
            # Try to make it unique by appending a number
            counter = 2
            while f"{key}_{counter}" in existing_keys or f"{key}_{counter}" in new_entries:
                counter += 1
            if counter > 2:
                key = f"{key}_{counter}"
        # Final safety
        if key in existing_keys or key in new_entries:
            continue

        class_name = ''.join(word.capitalize() for word in key.split('_')) + 'Provider'

        entry = {
            "name": name.upper(),
            "nse_code": "",
            "segments": [],
            "api_status": "stub",
            "base_url": "",
            "auth_type": "unknown",
            "required_credentials": [],
            "deprecated": False,
            "_implementation": f"providers/{key}.py",
        }

        new_entries[key] = entry
        new_stub_files.append((key, class_name, name))

    print(f"[MIGRATE] {len(new_entries)} new entries to add")

    # ── Update registry.py ──────────────────────────────────────────────────

    # Build new entries block
    new_block_lines = []
    for key in sorted(new_entries.keys()):
        entry = new_entries[key]
        lines = [f'    "{key}": {{']
        for field in ["name", "nse_code", "segments", "api_status", "base_url",
                       "auth_type", "required_credentials", "deprecated", "_implementation"]:
            val = entry[field]
            if isinstance(val, list):
                lines.append(f'        "{field}": {val},')
            elif isinstance(val, bool):
                lines.append(f'        "{field}": {val},')
            elif val == "":
                lines.append(f'        "{field}": "",')
            else:
                lines.append(f'        "{field}": "{val}",')
        lines.append('    },')
        new_block_lines.append('\n'.join(lines))

    new_entries_str = ',\n\n'.join(new_block_lines)

    # Find insertion point — after the last existing entry (find "# ──" divider or end of dict)
    # We'll insert right before the closing "}" of PROVIDER_INFO
    # Find the last "    }," in the block (the final entry before the closing brace)
    last_entry_match = list(re.finditer(r'(    },\n)(?=\nPROVIDER_INFO_END|\n__all__|\ndef\s)', provider_block))
    if not last_entry_match:
        # Fallback: find line just before closing brace of PROVIDER_INFO
        last_entry_match = list(re.finditer(r'    },\n', provider_block))

    # Insert new entries before the closing "}" of PROVIDER_INFO
    # The block ends with "}" on its own line
    insert_marker = '\n\nPROVIDER_INFO_END = True  # auto-generated marker'
    new_provider_block = provider_block.rstrip().rstrip('}').rstrip()
    if 'PROVIDER_INFO_END' not in new_provider_block:
        new_provider_block += '\n\n' + new_entries_str + '\n}'
    else:
        # Replace between last entry and PROVIDER_INFO_END / closing brace
        new_provider_block = provider_block + ',\n\n' + new_entries_str + '\n}'

    new_registry_content = prefix + new_provider_block + suffix

    # Fix: remove duplicate closing brace if any
    # Count closing braces at end
    new_registry_content = re.sub(r'\n}\n}\s*$', '\n}', new_registry_content)

    with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
        f.write(new_registry_content)
    print(f"[MIGRATE] registry.py updated with {len(new_entries)} entries")

    # ── Create stub files ───────────────────────────────────────────────────

    created = 0
    for key, class_name, name in new_stub_files:
        filepath = os.path.join(PROVIDERS_DIR, f"{key}.py")
        if os.path.exists(filepath):
            print(f"  [SKIP] {key}.py already exists")
            continue

        content = STUB_TEMPLATE % {
            "provider_key": key,
            "class_name": class_name,
            "name": name,
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        created += 1

    print(f"[MIGRATE] {created} new stub files created")

    # ── Update providers/__init__.py ────────────────────────────────────────

    # Read current __init__.py
    init_path = os.path.join(PROVIDERS_DIR, "__init__.py")
    with open(init_path, encoding='utf-8') as f:
        init_content = f.read()

    # Add new imports at the end before the _PROVIDER_MAP section
    # Find the last import line and add new ones after it
    import_lines = [f"from .{key} import {class_name}" for key, class_name, _ in new_stub_files]

    if import_lines:
        # Insert before "_PROVIDER_MAP"
        if "_PROVIDER_MAP" in init_content:
            init_content = init_content.replace(
                "_PROVIDER_MAP = {",
                '\n'.join(import_lines) + '\n' + "_PROVIDER_MAP = {"
            )
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(init_content)
        print(f"[MIGRATE] providers/__init__.py updated with {len(import_lines)} imports")

    # ── Add to _PROVIDER_MAP ────────────────────────────────────────────────

    # Read updated __init__.py
    with open(init_path, encoding='utf-8') as f:
        init_content = f.read()

    # Add new entries to _PROVIDER_MAP
    new_map_entries = '\n'.join(f'    "{key}": {class_name},' for key, class_name, _ in new_stub_files)
    if new_map_entries:
        init_content = re.sub(
            r'(    "[^"]+": [^,]+,\n)*\n(_PROVIDER_MAP_END|"[^"]+"\s*:\s*[^,]+)\s*\}',
            lambda m: m.group(0).rstrip().rstrip('}') + ',\n' + new_map_entries + '\n}',
            init_content
        )
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(init_content)
        print(f"[MIGRATE] _PROVIDER_MAP updated with {len(new_stub_files)} entries")

    print(f"[MIGRATE] DONE — {len(new_entries)} brokers added, {created} stubs created")
    print(f"[MIGRATE] Run: python -m py_compile python_app/brokers/providers/__init__.py to verify")


if __name__ == "__main__":
    main()