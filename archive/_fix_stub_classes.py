#!/usr/bin/env python3
"""Fix stub files and __init__.py for numeric-prefixed broker keys."""
import re, os

# Mapping of old_key -> (new_key, class_name)
fixes = {
    '1fc_securities':   ('_1fc_securities',   '_1fc_securitiesProvider'),
    '21artha':          ('_21artha',          '_21arthaProvider'),
    '360_one_capital_market':     ('_360_one_capital_market',     '_360_one_capital_marketProvider'),
    '360_one_distribution_services': ('_360_one_distribution_services', '_360_one_distribution_servicesProvider'),
    '5paisa_capital':  ('_5paisa_capital',  '_5paisa_capitalProvider'),
}

providers_dir = 'python_app/brokers/providers'
errors = []

for old_key, (new_key, class_name) in fixes.items():
    stub_path = os.path.join(providers_dir, f'{new_key}.py')
    if not os.path.exists(stub_path):
        errors.append(f'Missing stub: {stub_path}')
        continue

    with open(stub_path, encoding='utf-8') as f:
        content = f.read()

    # Fix the class name line:  class 21arthaProvider(...) -> class _21arthaProvider(...)
    content = re.sub(rf'class\s+{old_key[1:] if old_key[0].isdigit() else old_key}Provider', f'class {class_name}', content)

    # Fix _provider_key value
    content = re.sub(r'_provider_key\s*=\s*"' + old_key + r'"', f'_provider_key = "{new_key}"', content)

    # Fix logger name
    old_logger = old_key[0].isdigit() and old_key or old_key  # just for safety; not really needed

    with open(stub_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed stub: {new_key}.py')

# Fix __init__.py — update class names in imports and _PROVIDER_MAP
init_path = os.path.join(providers_dir, '__init__.py')
with open(init_path, encoding='utf-8') as f:
    content = f.read()

for old_key, (new_key, class_name) in fixes.items():
    # Import line: from ._1fc_securities import _1fc_securitiesProvider
    old_import = f'from .{old_key} import {old_key[1:] if old_key[0].isdigit() else old_key}Provider'
    new_import = f'from .{new_key} import {class_name}'
    content = content.replace(old_import, new_import)
    # Map entry
    content = content.replace(f'"{old_key}": {old_key[1:] if old_key[0].isdigit() else old_key}Provider',
                              f'"{new_key}": {class_name}')

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('providers/__init__.py imports fixed')

if errors:
    for e in errors:
        print(f'ERROR: {e}')
else:
    print('All fixes applied successfully')