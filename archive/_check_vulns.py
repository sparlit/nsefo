import pkg_resources

# Get installed packages
installed = {p.project_name.lower(): p.version for p in pkg_resources.working_set}

# Packages with vulnerabilities (from pip-audit)
vuln = {
    'autobahn': ('19.11.2', '20.12.3'),
    'click': ('8.1.7', '8.3.3'),
    'ecdsa': ('0.19.2', None),
    'mcp': ('1.28.0', '1.28.1'),
    'pillow': ('12.2.0', '12.3.0'),
    'python-dotenv': ('1.0.0', '1.2.2'),
    'setuptools': ('81.0.0', '83.0.0'),
}

# Packages in requirements.txt
reqs = [
    'dhanhq', 'pydantic', 'fastapi', 'uvicorn', 'python-multipart', 'pyotp',
    'httpx', 'websockets', 'pyside6', 'pandas', 'numpy', 'spacy', 'opengreeks',
    'fenix', 'pycryptodome', 'requests-oauthlib', 'selenium', 'trio',
    'trio-websocket', 'websocket-client', 'playwright', 'curl_cffi',
    'python-dotenv', 'pytest', 'pytest-asyncio'
]

reqs_lower = set(r.lower() for r in reqs)

print("=== Vulnerable packages that ARE in requirements.txt ===")
for name, (ver, fix) in vuln.items():
    if name in reqs_lower:
        print(f"  {name} {ver} -> fix: {fix}")

print()
print("=== All vulnerable packages ===")
for name, (ver, fix) in vuln.items():
    in_reqs = "IN REQS" if name in reqs_lower else "NOT in reqs"
    print(f"  {name} {ver} ({in_reqs})")

print()
print("=== Installed websocket-client ===")
print(f"  websocket-client: {installed.get('websocket-client', 'NOT FOUND')}")
print(f"  websockets: {installed.get('websockets', 'NOT FOUND')}")
print(f"  selenium: {installed.get('selenium', 'NOT FOUND')}")
print(f"  trio-websocket: {installed.get('trio-websocket', 'NOT FOUND')}")

# Check if ecdsa is a dep of anything we care about
print()
print("=== ECDSA deps ===")
import subprocess
result = subprocess.run(['pip', 'show', 'ecdsa'], capture_output=True, text=True)
print(result.stdout)

print("=== Python-dotenv deps ===")
result = subprocess.run(['pip', 'show', 'python-dotenv'], capture_output=True, text=True)
print(result.stdout)