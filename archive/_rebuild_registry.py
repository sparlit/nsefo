#!/usr/bin/env python3
"""Rebuild registry.py with all broker entries."""
import re, sys

with open('python_app/brokers/registry.py', encoding='utf-8') as f:
    lines = f.read().splitlines()

# ── Find PROVIDER_INFO boundaries ─────────────────────────────────────────────
pinfo_start = next(i for i, l in enumerate(lines) if 'PROVIDER_INFO = {' in l)
print(f'PROVIDER_INFO starts at line {pinfo_start+1}')

# Forward scan: find the closing brace of PROVIDER_INFO
# brace goes positive on { and negative on }
# When we see the } that brings brace to -1, we've passed the closing }
seen_open = False
brace = 0
dict_close_line = None
for i, l in enumerate(lines[pinfo_start:], pinfo_start):
    prev_brace = brace
    for c in l:
        if c == '{':
            brace += 1
            seen_open = True
        elif c == '}':
            brace -= 1
    # When brace goes from 1→0, we've closed PROVIDER_INFO
    if seen_open and prev_brace >= 1 and brace == 0:
        dict_close_line = i
        break

print(f'PROVIDER_INFO closes at line {dict_close_line+1}')
# dict_close_line = line with "}" (the closing of PROVIDER_INFO)

# Last entry is dict_close_line - 1 (the "    }," line)
last_entry_line = dict_close_line - 1
print(f'Last entry at line {last_entry_line+1}: {lines[last_entry_line].strip()[:60]}')
# blank line after last entry: dict_close_line + 1
# functions start at dict_close_line + 2

# ── Build new entries ─────────────────────────────────────────────────────────
with open('INDIAN STOCK MARKET REGISTERED BROKERS.txt', encoding='utf-8') as f:
    broker_names = [l.strip() for l in f.read().splitlines()[1:] if l.strip()]

# Collect existing provider keys
existing_keys = set()
for i in range(pinfo_start + 1, dict_close_line):
    m = re.match(r'\s+"(\w+)":\s*\{', lines[i])
    if m:
        existing_keys.add(m.group(1))
print(f'Existing keys: {len(existing_keys)}')

def to_key(name):
    s = re.sub(r'\s+(PVT\.?|LTD\.?|LIMITED|PRIVATE|LLP|India|Ireland|Singapore|USA|UK)\s*$', '', name.strip(), flags=re.IGNORECASE)
    s = re.sub(r'^THE\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s.strip())
    words = [w for w in s.split() if len(w) > 2]
    key = '_'.join(words[:4]).lower()
    key = re.sub(r'[^a-z0-_]', '', key)
    key = re.sub(r'_+', '_', key).strip('_')
    return key or None

new_entries = []
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
    entry = (
        f'    "{safe_key}": {{\n'
        f'        "name": "{name.upper()}",\n'
        f'        "nse_code": "",\n'
        f'        "segments": [],\n'
        f'        "api_status": "stub",\n'
        f'        "base_url": "",\n'
        f'        "auth_type": "unknown",\n'
        f'        "required_credentials": [],\n'
        f'        "deprecated": False,\n'
        f'        "_implementation": "providers/{safe_key}.py",\n'
        f'    }},'
    )
    new_entries.append(entry)

print(f'new_entries count: {len(new_entries)}')
if new_entries:
    print(f'First entry chars: {len(new_entries[0])}, last: {len(new_entries[-1])}')
    print(f'First entry: {new_entries[0][:100]!r}')
    print(f'Last entry: {new_entries[-1][:100]!r}')
# Join entries
joined = ''.join(new_entries)
print(f'joined chars: {len(joined):,}')

# Join entries with no separator (entries already have their own newlines and trailing commas)
# All entries have trailing comma (}},). Join into one big string.
joined = ''.join(new_entries)  # each entry is a self-contained multi-line string with trailing comma

# Strip the trailing comma from the very last entry (it needs "}}" not "}},")
last_close = joined.rfind('    }}')
# Remove the trailing comma after the last entry's "}}"
joined = joined[:last_close + 5]  # up to and including "    }}"  (5 chars: 4-space + }})

# Build new file content
# Lines: header + blank + new entries + blank + closing brace + blank + functions
header = '\n'.join(lines[:pinfo_start + 1])  # up to and including "PROVIDER_INFO = {"
middle = '\n' + joined + '\n'  # blank + entries + blank
tail = lines[dict_close_line] + '\n' + '\n'.join(lines[dict_close_line + 1:])
new_content = header + middle + tail

print(f'  header chars: {len(header):,}')
print(f'  joined chars: {len(joined):,}')
print(f'  tail chars: {len(tail):,}')
print(f'  new_content chars: {len(new_content):,}')
print(f'  dict_close_line={dict_close_line}, pinfo_start={pinfo_start}')
print(f'  lines[dict_close_line]={lines[dict_close_line]!r}')
print(f'  new_content[:200]: {new_content[:200]!r}')

print(f'New file size: {len(new_content):,} chars')

import ast
try:
    ast.parse(new_content)
    print('AST: OK')
except SyntaxError as e:
    print(f'AST ERROR: {e}')
    if e.lineno:
        el = new_content.splitlines()
        for i in range(max(0, e.lineno-3), min(len(el), e.lineno+3)):
            print(f'{i+1}: {el[i]!r}')
    sys.exit(1)

# Verify entry count
t = ast.parse(new_content)
pi = next(n for n in ast.walk(t) if isinstance(n, ast.Assign) and
           any(isinstance(x, ast.Name) and x.id == 'PROVIDER_INFO' for x in n.targets))
print(f'PROVIDER_INFO entries: {len(pi.value.keys)}')

with open('python_app/brokers/registry.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done')