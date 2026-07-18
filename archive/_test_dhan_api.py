"""Verify Dhan API connectivity with provided access token."""
import os, httpx, json

TOKEN = os.environ.get("NSEFO_DHAN_TOKEN") or "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzg0MjY1NTc1LCJpYXQiOjE3ODQxNzkxNzUsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwNjI1NTI5In0.iKPTzoC23_P3tTqG6hNtsu1nQVQ7sFSgGKD7IBfjYU9C0YulRe1-D06RV7-JE0GT00uoJX7z9Yxc3VOzh0hTpQ"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
BASE = "https://api.dhan.co/v2"

def get(path: str, params=None):
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, params=params or {}, timeout=15)
    return r.status_code, r.json()

def post(path: str, data: dict):
    r = httpx.post(f"{BASE}{path}", headers=HEADERS, json=data, timeout=15)
    return r.status_code, r.json()

print("=== Dhan API Connectivity Test ===")
print()

# 1. Test user profile
code, body = get("/profile")
print(f"GET /profile  → {code}")
if code == 200:
    print(f"  client_id : {body.get('clientId')}")
    print(f"  name      : {body.get('name')}")
    print(f"  email     : {body.get('emailId')}")
else:
    print(f"  ERROR: {body}")

print()

# 2. Test fund limits
code, body = get("/fundlimits")
print(f"GET /fundlimits  → {code}")
if code == 200:
    print(f"  available_cash : {body.get('availableCash')}")
    print(f"  collateral    : {body.get('collateral')}")
    print(f"  margin_used   : {body.get('marginUsed')}")
else:
    print(f"  ERROR: {body}")

print()

# 3. Test positions
code, body = get("/positions")
print(f"GET /positions  → {code}")
if code == 200:
    print(f"  positions: {len(body) if isinstance(body, list) else body}")
else:
    print(f"  ERROR: {body}")

print()

# 4. Test holdings
code, body = get("/holdings")
print(f"GET /holdings  → {code}")
if code == 200:
    print(f"  holdings: {len(body) if isinstance(body, list) else body}")
else:
    print(f"  ERROR: {body}")

print()

# 5. Test NSEFO instruments (search for Nifty)
code, body = post("/instruments", {"exchange": "NSE_FO", "symbol": "NIFTY", "instrument_type": "OPT"})
print(f"POST /instruments  → {code}")
if code == 200:
    data = body.get("data", []) if isinstance(body, dict) else body
    print(f"  NIFTY options found: {len(data)}")
    if data:
        print(f"  sample: {data[0]}")
else:
    print(f"  ERROR: {body}")

print()
print("=== Done ===")