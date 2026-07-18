#!/usr/bin/env python3
"""Rebuild registry.py using ast.parse to extract and rebuild the PROVIDER_INFO dict."""
import ast, re, sys

REGISTRY = 'python_app/brokers/registry.py'
BROKERS = 'INDIAN STOCK MARKET REGISTERED BROKERS.txt'

# ── Step 1: Read original and extract via AST ────────────────────────────────
with open(REGISTRY, encoding='utf-8') as f:
    src = f.read()

tree = ast.parse(src)
# Find PROVIDER_INFO assignment
pi_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
               any(isinstance(t, ast.Name) and t.id == 'PROVIDER_INFO' for t in n.targets))
print(f'Original PROVIDER_INFO: {len(pi_node.value.keys)} entries')

# Get source lines
src_lines = src.splitlines()

# Find the line range of PROVIDER_INFO in the source
# The dict literal starts at pi_node.lineno, ends at the line of the last entry
# We need to find the line with the closing "}" of PROVIDER_INFO

# Map AST line numbers to source lines (AST is 1-indexed)
# We'll find PROVIDER_INFO dict boundaries by scanning forward from pi_node.lineno
pinfo_lineno = pi_node.lineno  # e.g., 24

# Find the line that closes the PROVIDER_INFO dict by scanning with a brace counter
brace = 0
dict_close_lineno = None
for i, line in enumerate(src_lines[pinfo_lineno - 1:], pinfo_lineno - 1):
    for c in line:
        if c == '{':
            brace += 1
        elif c == '}':
            brace -= 1
    if brace == 0 and i >= pinfo_lineno - 1:
        dict_close_lineno = i + 1  # 1-indexed
        break

print(f'PROVIDER_INFO dict: lines {pinfo_lineno}..{dict_close_lineno}')
# dict_close_lineno is the line with "}" of PROVIDER_INFO

# Last entry is dict_close_lineno - 1
last_entry_lineno = dict_close_lineno - 1
print(f'Last original entry at line: {last_entry_lineno}')

# ── Step 2: Load broker names ────────────────────────────────────────────────
with open(BROKERS, encoding='utf-8') as f:
    broker_names = [l.strip() for l in f.read().splitlines()[1:] if l.strip()]
print(f'Brokers in file: {len(broker_names)}')

# Collect existing provider keys
existing_keys = set(pi_node.value.keys)
print(f'Existing keys: {len(existing_keys)}')

def to_key(name):
    s = re.sub(r'\s+(PVT.?|LTD.?|LIMITED|PRIVATE|LLP|India|Ireland|Singapore|USA|UK)\s*$', '', name.strip(), flags=re.IGNORECASE)
    s = re.sub(r'^THE\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s.strip())
    words = [w for w in s.split() if len(w) > 2]
    key = '_'.join(words[:4]).lower()
    key = re.sub(r'[^a-z0-_\s]', '', key)
    return key or None

# Build new AST dict entries
new_key_nodes = {}
for name in broker_names:
    key = to_key(name)
    if not key:
        continue
    if key in existing_keys:
        c = 2
        while f'{key}_{c}' in existing_keys:
            c += 1
        key = f'{key}_{c}'
    if key in existing_keys:
        continue
    existing_keys.add(key)
    safe_key = '_' + key if key[0].isdigit() else key
    new_key_nodes[safe_key] = name

print(f'New entries to add: {len(new_key_nodes)}')
if not new_key_nodes:
    print('No new entries — exiting')
    sys.exit(0)

# ── Step 3: Build the new PROVIDER_INFO dict ─────────────────────────────────
# Build new dict: copy of original + new entries
new_dict_pairs = list(pi_node.value.keys) + list(new_key_nodes.keys)

# Build AST Dict with all entries
new_dict_ast = ast.Dict(
    keys=[ast.Constant(value=k) for k in new_dict_pairs],
    values=[
        ast.Dict(
            keys=[ast.Constant(value=field) for field in [
                'name', 'nse_code', 'segments', 'api_status',
                'base_url', 'auth_type', 'required_credentials',
                'deprecated', '_implementation'
            ]],
            values=[
                ast.Constant(value=new_key_nodes[k]['name'] if k in new_key_nodes else ''),
                ast.Constant(value=''),
                ast.List(elts=[]),
                ast.Constant(value='stub'),
                ast.Constant(value=''),
                ast.Constant(value='unknown'),
                ast.List(elts=[]),
                ast.Constant(value=False),
                ast.Constant(value=f'providers/{k}.py'),
            ]
        ) if k in new_key_nodes else pi_node.value.keys[i]  # This won't work — need to look up original value
        for i, k in enumerate(new_dict_pairs)
    ]
)

# This approach is getting complex. Instead, let's use a simpler method:
# Build the new source by extracting the dict content as Python literal strings

# Extract existing entries as source text
# Get the source text for the existing PROVIDER_INFO dict
entry_source_lines = src_lines[pinfo_lineno:dict_close_lineno]  # includes opening and entries, not closing }

# Build new entries as Python source lines
new_entry_source_lines = []
for k, name in new_key_nodes.items():
    impl_path = f'providers/{k}.py'
    entry_src = '\n'.join([
        f'    "{k}": {{',
        f'        "name": "{name.upper()}",',
        f'        "nse_code": "",',
        f'        "segments": [],',
        f'        "api_status": "stub",',
        f'        "base_url": "",',
        f'        "auth_type": "unknown",',
        f'        "required_credentials": [],',
        f'        "deprecated": False,',
        f'        "_implementation": "{impl_path}",',
        f'    }},',
    ])
    new_entry_source_lines.append(entry_src)

# Join new entries (no separator — entries already have internal newlines and trailing commas)
joined_new = ''.join(new_entry_source_lines)
# Remove trailing comma from the very last entry
last_close_idx = joined_new.rfind('    }}')
if last_close_idx >= 0:
    joined_new = joined_new[:last_close_idx + 5]  # keep up to "    }}" (4-space + }})

# Rebuild the dict section
# Lines: "PROVIDER_INFO = {" + newline + existing entries + blank line + new entries + newline + closing "}"
new_dict_src = (
    f'PROVIDER_INFO = {{\n'                                     # opening
    + '\n'.join(entry_source_lines[1:]) + '\n'                   # existing entries (skip "PROVIDER_INFO = {")
    + '\n'                                                     # blank line
    + joined_new + '\n'                                         # new entries
    + '}\n'                                                     # closing brace
)

# Full new source
new_src = (
    '\n'.join(src_lines[:pinfo_lineno - 1]) + '\n'  # everything before PROVIDER_INFO (up to line before)
    + new_dict_src
    + '\n'.join(src_lines[dict_close_lineno:])       # everything after the dict closing "}"
)

print(f'New source size: {len(new_src):,} chars')

# AST check
try:
    new_tree = ast.parse(new_src)
    pi_new = next(n for n in ast.walk(new_tree) if isinstance(n, ast.Assign) and
                  any(isinstance(t, ast.Name) and t.id == 'PROVIDER_INFO' for t in n.targets))
    print(f'New PROVIDER_INFO: {len(pi_new.value.keys)} entries')
    print(f'AST: OK')
except SyntaxError as e:
    print(f'AST ERROR: {e}')
    sys.exit(1)

with open(REGISTRY, 'w', encoding='utf-8') as f:
    f.write(new_src)
print('Done')