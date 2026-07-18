#!/usr/bin/env python3
import ast, sys

with open('python_app/brokers/registry.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Verify syntax
try:
    tree = ast.parse(src)
    print('Syntax: OK')
except SyntaxError as e:
    print(f'SyntaxError: {e}')
    sys.exit(1)

# Find PROVIDER_INFO assignment
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PROVIDER_INFO':
                if isinstance(node.value, ast.Dict):
                    print(f'PROVIDER_INFO dict has {len(node.value.keys)} keys (AST parse)')
                else:
                    print(f'PROVIDER_INFO is not a dict, type={type(node.value)}')

# Also try exec
ns = {}
exec(compile(src, 'registry.py', 'exec'), ns)
pi = ns.get('PROVIDER_INFO', {})
print(f'PROVIDER_INFO from exec: {len(pi)} entries')
bb = ns.get('BASE_PROVIDER_KEYS', [])
print(f'BASE_PROVIDER_KEYS from exec: {len(bb)} entries')

# Check a few of the new keys
for k in ['_1fc_securities', '_21artha', '_360_one_capital_market', 'zerodha', 'aadinath_securities']:
    print(f'  "{k}" in PROVIDER_INFO: {k in pi}')