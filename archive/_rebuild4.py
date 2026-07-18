#!/usr/bin/env python3
"""Rebuild registry.py via ast parse + unparse."""
import ast, re, sys

print("=== Rebuilding registry.py via AST ===")

# Read and parse original
with open('python_app/brokers/registry.py', encoding='utf-8') as f:
    src = f.read()

tree = ast.parse(src)

# Find PROVIDER_INFO node
pi_node = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
               any(isinstance(t, ast.Name) and t.id == 'PROVIDER_INFO' for t in n.targets))
print(f"Original PROVIDER_INFO: {len(pi_node.value.keys)} entries")

# Build mapping: provider_key -> AST dict value node for each NEW entry
with open('INDIAN STOCK MARKET REGISTERED BROKERS.txt', encoding='utf-8') as f:
    brokers = [l.strip() for l in f.read().splitlines()[1:] if l.strip()]
print(f"Brokers: {len(brokers)}")

# Get existing keys
existing_keys = set(k.value for k in pi_node.value.keys)
print(f"Existing keys: {len(existing_keys)}")

def to_key(name):
    s = re.sub(r'\s+(PVT.?|LTD.?|LIMITED|PRIVATE|LLP|India|Ireland|Singapore|USA|UK)\s*$', '', name.strip(), flags=re.IGNORECASE)
    s = re.sub(r'^THE\s+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s.strip())
    words = [w for w in s.split() if len(w) > 2]
    k = '_'.join(words[:4]).lower()
    k = re.sub(r'[^a-z0-_\s]', '', k)
    return k or None

# Build new key-value pairs
new_pairs = []
for name in brokers:
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
    sk = '_' + key if key[0].isdigit() else key

    # Build the AST for the entry value dict
    entry_dict = ast.Dict(
        keys=[ast.Constant(value=k) for k in
              ['name', 'nse_code', 'segments', 'api_status',
               'base_url', 'auth_type', 'required_credentials', 'deprecated', '_implementation']],
        values=[
            ast.Constant(value=name.upper()),
            ast.Constant(value=''),
            ast.List(elts=[]),
            ast.Constant(value='stub'),
            ast.Constant(value=''),
            ast.Constant(value='unknown'),
            ast.List(elts=[]),
            ast.Constant(value=False),
            ast.Constant(value=f'providers/{sk}.py'),
        ]
    )
    new_pairs.append((sk, entry_dict))

print(f"New pairs: {len(new_pairs)}")
if not new_pairs:
    print("Nothing to add!")
    sys.exit(0)

# Create new PROVIDER_INFO dict: original + new pairs
all_keys = list(pi_node.value.keys) + [ast.Constant(value=k) for k, v in new_pairs]
all_values = list(pi_node.value.values) + [v for k, v in new_pairs]
new_pi_dict = ast.Dict(keys=all_keys, values=all_values)

# Replace the node in the AST
pi_node.value = new_pi_dict

# Unparse the modified tree
new_src = ast.unparse(tree)
print(f"New source: {len(new_src):,} chars")

# Verify with ast.parse
try:
    ast.parse(new_src)
    print("AST verify: OK")
except SyntaxError as e:
    print(f"AST ERROR: {e}")
    sys.exit(1)

# Count entries
new_tree = ast.parse(new_src)
pi_new = next(n for n in ast.walk(new_tree) if isinstance(n, ast.Assign) and
              any(isinstance(t, ast.Name) and t.id == 'PROVIDER_INFO' for t in n.targets))
print(f"PROVIDER_INFO entries: {len(pi_new.value.keys)}")

with open('python_app/brokers/registry.py', 'w', encoding='utf-8') as f:
    f.write(new_src)
print("Done!")