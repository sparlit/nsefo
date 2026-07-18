#!/usr/bin/env python3
with open('python_app/brokers/registry.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('PROVIDER_INFO = {')
end = content.rfind('}')
print(f'PROVIDER_INFO starts at char {start}')
print(f'Last }} at char {end}')
print(f'Total file length: {len(content):,}')

dict_content = content[start:end]
entry_count = dict_content.count('    "')
print(f'Entries (by quotes): {entry_count}')

closes = content.count('}')
print(f'Total }} in file: {closes}')

# Check if there's a second PROVIDER_INFO = {
second = content.find('PROVIDER_INFO = {', start + 1)
print(f'Second PROVIDER_INFO at: {second}')

# Look for any SyntaxError triggers - unbalanced brackets
opens_brace = content.count('{')
closes_brace = content.count('}')
opens_paren = content.count('(')
closes_paren = content.count(')')
print(f'Braces: {{ {opens_brace} / }} {closes_brace}')
print(f'Parens: ( {opens_paren} / ) {closes_paren}')