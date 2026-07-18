#!/usr/bin/env python3
"""Rebuild registry.py with correct format."""
import re, ast, sys

print("=== Rebuilding registry.py ===")

with open('python_app/brokers/registry.py', encoding='utf-8') as f:
    lines = f.read().splitlines()

pinfo_start = next(i for i, l in enumerate(lines) if 'PROVIDER_INFO = {' in l)
print(f"PROVIDER_INFO at line {pinfo_start+1}")

brace = 0
dict_close = None
for i, l in enumerate(lines[pinfo_start:], pinfo_start):
    for c in l:
        if c == '{': brace += 1
        elif c == '}': brace -= 1
    if brace == 0 and i > pinfo_start:
        dict_close = i
        break
print(f"Closes at line {dict_close+1}")

with open('INDIAN STOCK MARKET REGISTERED BROKERS.txt', encoding='utf-8') as f:
    brokers = [l.strip() for l in f.read().splitlines()[1:] if l.strip()]
print(f"Brokers: {len(brokers)}")

existing = set()
for i in range(pinfo_start + 1, dict_close):
    m = re.match(r'\s+"(\w+)":\s*\{', lines[i])
    if m:
        existing.add(m.group(1))
print(f"Existing: {len(existing)}")

def to_key(name):
    s = re.sub(r'\s+(PVT.?|LTD.?|LIMITED|PRIVATE|LLP|India|Ireland|Singapore|USA|UK)\s*$', '', name.strip(), flags=re.IGNORECASE)
    s = re.sub(r'^THE\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s.strip())
    words = [w for w in s.split() if len(w) > 2]
    k = '_'.join(words[:4]).lower()
    k = re.sub(r'[^a-z0-_\s]', '', k)
    return k or None

new_entries = []
for name in brokers:
    key = to_key(name)
    if not key:
        continue
    if key in existing:
        c = 2
        while f'{key}_{c}' in existing:
            c += 1
        key = f'{key}_{c}'
    if key in existing:
        continue
    existing.add(key)
    sk = '_' + key if key[0].isdigit() else key
    entry = (
        f'    "{sk}": {{\n'
        f'        "name": "{name.upper()}",\n'
        f'        "nse_code": "",\n'
        f'        "segments": [],\n'
        f'        "api_status": "stub",\n'
        f'        "base_url": "",\n'
        f'        "auth_type": "unknown",\n'
        f'        "required_credentials": [],\n'
        f'        "deprecated": False,\n'
        f'        "_implementation": "providers/{sk}.py",\n'
        f'    }},\n'
    )
    new_entries.append(entry)

print(f"New entries: {len(new_entries)}")

# Each entry ends with "    }},\n" (brace+comma+newline — single closing brace, trailing comma)
# Join with empty string — entries directly concatenated: e1},\ne2},\ne3}}
joined = ''.join(new_entries)
print(f"Joined: {len(joined):,} chars")

# Verify: first entry last 30 chars
print(f"Entry ends with: {new_entries[0][-30:]!r}")

# The joined string ends with "    }},\n" (trailing comma + newline from last entry)
# We want to remove the trailing comma so: e1},\ne2},\ne3} (last entry has no comma)
# rfind "    }},\n" in joined
last_close = joined.rfind('    }},\n')
print(f"Last entry marker at: {last_close}")

# Strip trailing comma+newline from the last entry (but keep the "}}" closing brace)
if last_close >= 0:
    # Replace the last "    }},\n" with "    }}" (remove comma)
    joined = joined[:last_close] + joined[last_close + 6:]  # skip "    }},\n" (6 chars)
    # Actually: '    }},\n' = 7 chars? Let me check
    # 4-space + }} + , + \n = 4 + 2 + 1 + 1 = 8? Wait no
    # f'    }},\n' = f'    }' + '},' + '\n' = 5+2+1 = 8 chars? 
    # f'    }' = 5 chars, '},\n' = 3 chars = 8 total. 
    # '    }},\n' in repr: "'    }},\n'" = 8 chars. 
    # 4-space + } + } + , + \n = 8 chars
    # Strip the last ',\n' from '    }},\n': remove chars [last_close+4:] = ',\n'
    # No: we want to KEEP '    }}' and remove ',\n'
    # last_close is the position where '    }},\n' starts
    # We want: joined[:last_close+4] + joined[last_close+6:]
    # '    }},\n' starts at last_close. 4-space = last_close to last_close+4.
    # '}}' = last_close+4 to last_close+6. ',' = last_close+6. '\n' = last_close+7.
    # Actually: 4-space (last_close..last_close+4), first '}' (last_close+4), second '}' (last_close+5), ',' (last_close+6), '\n' (last_close+7)
    # Wait: '    }}' = 6 chars (4-space + 2 braces). ',\n' = 2 chars. Total 8.
    # So '    }},\n' = '    }}' + ',\n' = '    }},\n'
    # Actually: f'    }}' = '    }}' (4-space + 1 brace = 5 chars? But }} is TWO chars... 
    # I'm confusing myself. Let me just print the hex of the last few chars.
    pass

# The last "    }},\n" (7 chars: 4-space + }} + , + \n) — strip just the ',\n'
# Actually: find ",\n" at the end of the string
last_comma_newline = joined.rfind(',\n')
print(f"Last comma-newline at: {last_comma_newline}")
if last_comma_newline == len(joined) - 2:
    # It's the last ",\n" — strip it
    joined = joined[:last_comma_newline]
    print(f"After strip: {len(joined):,} chars")
    print(f"joined ends with: {joined[-50:]!r}")

# Build new file
new_file = (
    '\n'.join(lines[:pinfo_start])       # header (up to line before PROVIDER_INFO)
    + '\nPROVIDER_INFO = {\n'            # opening brace
    + joined                               # entries (ends with }} of last entry)
    + '\n}\n'                             # closing brace of dict
    + '\n'.join(lines[dict_close + 1:])   # rest (blank line + functions)
)
print(f"new_file: {len(new_file):,} chars")

# AST check
try:
    ast.parse(new_file)
    print("AST: OK")
except SyntaxError as e:
    print(f"AST ERROR: {e}")
    sys.exit(1)

tree = ast.parse(new_file)
pi = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
           any(isinstance(x, ast.Name) and x.id == 'PROVIDER_INFO' for x in n.targets))
print(f"PROVIDER_INFO entries: {len(pi.value.keys)}")

with open('python_app/brokers/registry.py', 'w', encoding='utf-8') as f:
    f.write(new_file)
print("Done!")